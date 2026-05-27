import streamlit as st
from pathlib import Path
from src.database.connection import get_db_session
from src.database.repository import (
    create_training_session,
    finish_training_session,
    create_answer_history,
    mark_question_as_bad,
)
from src.business.randomizer import get_random_questions
from src.business.training_manager import TrainingManager

@st.cache_resource
def get_training_manager(language: str) -> TrainingManager:
    """
    Returns the cached instance of TrainingManager for the selected language.
    This guarantees that heavy ML models (e.g., whisper) are initialized
    strictly once and kept in memory across page interactions.
    """
    voice = "ru-RU-DmitryNeural" if language == "ru" else "en-US-AndrewNeural"
    return TrainingManager(tts_voice=voice, stt_model_size="small")

def render_training():
    """
    Renders the Sandbox Training Camp tab with TTS reading and voice STT+AI feedback.
    """
    st.markdown("### 🥋 Тренировочный лагерь (Training Hub)")
    st.markdown("Практикуйте устные ответы на технические вопросы с последующим разбором эталонных решений и самооценкой.")
    st.write("")

    # Initialize Session State variables for Sandbox
    if "sandbox_session_active" not in st.session_state:
        st.session_state.sandbox_session_active = False
    if "sandbox_finished" not in st.session_state:
        st.session_state.sandbox_finished = False
    if "sandbox_questions" not in st.session_state:
        st.session_state.sandbox_questions = []
    if "sandbox_current_index" not in st.session_state:
        st.session_state.sandbox_current_index = 0
    if "sandbox_show_expected" not in st.session_state:
        st.session_state.sandbox_show_expected = False
    if "sandbox_session_id" not in st.session_state:
        st.session_state.sandbox_session_id = None
    if "sandbox_ratings" not in st.session_state:
        st.session_state.sandbox_ratings = []
    if "sandbox_answers" not in st.session_state:
        st.session_state.sandbox_answers = {}

    # Get the TrainingManager instance based on active language in sidebar
    audio_lang = st.session_state.get("audio_language", "en")
    manager = get_training_manager(audio_lang)

    # 1. State: Config / Start Page
    if not st.session_state.sandbox_session_active and not st.session_state.sandbox_finished:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.02); padding: 25px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 25px;">
            <h4 style="color: #818cf8; margin-top: 0;">🥋 Режим «Песочница» (Sandbox Mode)</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                В этом режиме вам будет предложено случайное количество вопросов из базы данных. 
                Вы можете озвучивать вопросы через TTS, отвечать на них устно голосом, после чего система ИИ 
                с помощью распознавания речи (STT) запишет ваш ответ и предоставит глубокий технический разбор.
            </p>
            <ul style="color: #94a3b8; font-size: 0.9rem; padding-left: 20px;">
                <li>Все вопросы выбираются случайным образом.</li>
                <li>Вопросы озвучиваются автоматически при открытии карточки.</li>
                <li>Вы можете отключить озвучку или прослушать вопрос заново с помощью кнопок управления.</li>
                <li>Доступна устная запись ответа прямо в браузере с детальной оценкой ИИ по критериям.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        with st.form("sandbox_config_form"):
            num_q = st.slider("Количество вопросов в сессии", min_value=1, max_value=20, value=5, step=1, help="Выберите, сколько вопросов вы хотите пройти за этот раунд.")
            analysis_mode_opt = st.radio(
                "Режим оценки ответов в ИИ",
                options=["Анализ батчами (быстро и экономично)", "Анализ ответов по одному (детально, langchain batch)"],
                index=0,
                help="Анализ батчами группирует до 5 ответов в один запрос ИИ. Анализ по одному отправляет каждый ответ отдельно в параллельном режиме."
            )
            start_session_btn = st.form_submit_button("🚀 Начать тренировочную сессию", type="primary", use_container_width=True)

        if start_session_btn:
            session_created = False
            with get_db_session() as session:
                random_qs = get_random_questions(session, num_q)
                if not random_qs:
                    st.warning("⚠️ В базе данных пока нет активных вопросов! Сначала сгенерируйте вопросы во вкладке 'Генерация вопросов'.")
                else:
                    # Create Session in DB
                    db_sess = create_training_session(session, session_mode="Sandbox", total_questions=len(random_qs))
                    
                    # Save to Streamlit state
                    st.session_state.sandbox_questions = [
                        {
                            "id": q.id,
                            "question_text": q.question_text,
                            "expected_answer": q.expected_answer,
                            "question_type": q.question_type.value,
                            "keywords": q.keywords,
                            "code_snippet": q.code_snippet,
                            "grade": q.grade.value if hasattr(q.grade, "value") else str(q.grade),
                            "global_topic_name": q.local_topic.global_topic.name,
                            "local_topic_name": q.local_topic.name
                        }
                        for q in random_qs
                    ]
                    st.session_state.sandbox_current_index = 0
                    st.session_state.sandbox_session_id = db_sess.id
                    st.session_state.sandbox_session_active = True
                    st.session_state.sandbox_finished = False
                    st.session_state.sandbox_show_expected = False
                    st.session_state.sandbox_ratings = []
                    st.session_state.sandbox_answers = {}
                    st.session_state.sandbox_analysis_mode = "batch" if "Анализ батчами" in analysis_mode_opt else "single"
                    session_created = True
                    
            if session_created:
                # Force reset of audio flags
                if "audio_loaded_question_id" in st.session_state:
                    del st.session_state.audio_loaded_question_id
                st.toast("Сессия успешно создана! Начинаем...", icon="🚀")
                st.rerun()

    # 2. State: Active Training Session
    elif st.session_state.sandbox_session_active:
        user_audio = None
        questions = st.session_state.sandbox_questions
        idx = st.session_state.sandbox_current_index
        total_q = len(questions)
        q = questions[idx]

        # Initialize audio states for this active question
        if "audio_loaded_question_id" not in st.session_state or st.session_state.audio_loaded_question_id != q["id"]:
            st.session_state.audio_loaded_question_id = q["id"]
            st.session_state.audio_playing = True
            st.session_state.audio_replay_index = 0
            # Reset voice submit states
            st.session_state.sandbox_voice_submitted = False
            st.session_state.sandbox_ai_eval_result = None

        # Header/Progress
        st.markdown(f"##### Вопрос {idx + 1} из {total_q}")
        st.progress((idx) / total_q)
        
        # Display Question Card
        badge_class = "badge-theory"
        if q["question_type"] == "Algorithms":
            badge_class = "badge-coding"
        elif q["question_type"] == "BugHunting":
            badge_class = "badge-bughunting"
        elif q["question_type"] in ["TestArch", "TestDesign"]:
            badge_class = "badge-theory"
            
        grade_str = q.get("grade", "middle")
        grade_class = f"badge-{grade_str.lower()}"

        st.markdown(f"<div class='question-card'>", unsafe_allow_html=True)
        st.markdown(
            f"<h4>Вопрос #{q['id']} <span class='qtype-badge {badge_class}'>{q['question_type']}</span> <span class='qtype-badge {grade_class}'>{grade_str.upper()}</span></h4>", 
            unsafe_allow_html=True
        )
        
        # Display Topic & Subtopic breadcrumbs for context in Sandbox Training Mode
        if q.get("global_topic_name") and q.get("local_topic_name"):
            st.markdown(
                f"<div style='font-size: 0.85rem; color: #818cf8; margin-top: -12px; margin-bottom: 15px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;'>"
                f"📂 {q['global_topic_name']} &nbsp;/&nbsp; 📄 {q['local_topic_name']}"
                f"</div>", 
                unsafe_allow_html=True
            )
            
        st.markdown(f"<div style='font-size: 1.15rem; font-weight: 500; line-height: 1.6; color: #f0f2f6; margin-bottom: 20px;'>{q['question_text']}</div>", unsafe_allow_html=True)

        if q["code_snippet"]:
            st.markdown("**Код / Сниппет:**")
            st.code(q["code_snippet"], language="python")
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔊 TTS Audio Autoplay Block & Buttons (inside card section)
        audio_file_path = None
        try:
            cached_path = manager.get_question_audio(q["id"], q["question_text"])
            if cached_path and cached_path.exists():
                # Clean up old replay-specific files for this question to save space
                for old_file in cached_path.parent.glob(f"q_{q['id']}_play_*.mp3"):
                    try:
                        old_file.unlink()
                    except Exception:
                        pass
                
                # Generate a unique path for the current replay index to bust the element/media cache
                audio_file_path = cached_path.parent / f"q_{q['id']}_play_{st.session_state.audio_replay_index}.mp3"
                import shutil
                shutil.copy(cached_path, audio_file_path)
        except Exception as e:
            st.warning(f"⚠️ Не удалось синтезировать голос для вопроса: {e}")

        # Controls columns
        col_play_ctrl1, col_play_ctrl2, col_play_ctrl_spacer = st.columns([0.25, 0.25, 0.5])
        with col_play_ctrl1:
            if st.session_state.audio_playing:
                if st.button("⏹️ Остановить озвучку", key=f"btn_stop_{q['id']}", use_container_width=True, help="Выключить плеер"):
                    st.session_state.audio_playing = False
                    st.rerun()
            else:
                if st.button("▶️ Воспроизвести", key=f"btn_play_{q['id']}", use_container_width=True, help="Включить озвучку вопроса"):
                    st.session_state.audio_playing = True
                    st.rerun()
                    
        with col_play_ctrl2:
            if st.button("🔄 Повторить озвучку", key=f"btn_replay_{q['id']}", use_container_width=True, help="Проиграть вопрос заново с начала"):
                st.session_state.audio_playing = True
                st.session_state.audio_replay_index += 1
                st.rerun()

        # Render hidden autoplay audio element if playing is active
        if audio_file_path and st.session_state.audio_playing:
            st.audio(
                str(audio_file_path),
                format="audio/mp3",
                autoplay=True
            )

        # Define local helper for final evaluations of all recorded voice answers
        def trigger_final_evaluation(current_user_audio=None):
            # If the current question has audio and is not transcribed yet, trigger transcription background task
            if current_user_audio is not None and idx not in st.session_state.sandbox_answers:
                try:
                    audio_bytes = current_user_audio.read()
                    temp_dir = Path("data/audio")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    temp_audio_path = temp_dir / f"session_{st.session_state.sandbox_session_id}_q_{q['id']}_temp.wav"
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_bytes)
                    
                    st.session_state.sandbox_answers[idx] = {
                        "id": q["id"],
                        "question_text": q["question_text"],
                        "expected_answer": q["expected_answer"],
                        "question_type": q["question_type"],
                        "transcribed_text": "(Распознавание речи...)",
                        "is_voice": True,
                        "ai_evaluated": False,
                        "transcribing": True,
                        "temp_audio_path": temp_audio_path
                    }
                    
                    import threading
                    def run_bg_transcription(sess_id, q_id, q_idx, file_path):
                        try:
                            transcribed = manager.audio_manager.process_user_audio(file_path)
                            if not transcribed:
                                transcribed = "(Тишина или неразборчивая речь)"
                            
                            if "sandbox_answers" in st.session_state and q_idx in st.session_state.sandbox_answers:
                                st.session_state.sandbox_answers[q_idx]["transcribed_text"] = transcribed
                                st.session_state.sandbox_answers[q_idx]["transcribing"] = False
                                
                            with get_db_session() as session:
                                from sqlalchemy import select
                                from src.database.models import AnswerHistory
                                stmt = select(AnswerHistory).where(
                                    AnswerHistory.session_id == sess_id,
                                    AnswerHistory.question_id == q_id
                                )
                                db_history = session.scalar(stmt)
                                if db_history:
                                    db_history.transcribed_text = transcribed
                                else:
                                    create_answer_history(
                                        db=session,
                                        session_id=sess_id,
                                        question_id=q_id,
                                        confidence_score=0,
                                        transcribed_text=transcribed,
                                        evaluation_status="Pending"
                                    )
                        except Exception as th_err:
                            print(f"Error in bg transcription: {th_err}")
                            if "sandbox_answers" in st.session_state and q_idx in st.session_state.sandbox_answers:
                                st.session_state.sandbox_answers[q_idx]["transcribing"] = False
                    
                    threading.Thread(
                        target=run_bg_transcription,
                        args=(st.session_state.sandbox_session_id, q["id"], idx, temp_audio_path)
                    ).start()
                except Exception as e:
                    st.error(f"Ошибка при сохранении последнего ответа: {e}")

            # Transcribe any pending answers synchronously now to prevent deadlocks and show proper UI progress state!
            pending_items = [
                (q_idx, ans) for q_idx, ans in st.session_state.sandbox_answers.items()
                if ans.get("is_voice") and ans.get("transcribing", False)
            ]
            
            if pending_items:
                with st.spinner("🎤 Завершаем распознавание речи... Пожалуйста, подождите."):
                    for q_idx, ans in pending_items:
                        try:
                            file_path = ans.get("temp_audio_path")
                            if file_path and file_path.exists():
                                transcribed = manager.audio_manager.process_user_audio(file_path)
                                if not transcribed:
                                    transcribed = "(Тишина или неразборчивая речь)"
                                
                                ans["transcribed_text"] = transcribed
                                ans["transcribing"] = False
                                
                                # Update database record
                                with get_db_session() as session:
                                    from sqlalchemy import select
                                    from src.database.models import AnswerHistory
                                    stmt = select(AnswerHistory).where(
                                        AnswerHistory.session_id == st.session_state.sandbox_session_id,
                                        AnswerHistory.question_id == ans["id"]
                                    )
                                    db_history = session.scalar(stmt)
                                    if db_history:
                                        db_history.transcribed_text = transcribed
                                    else:
                                        create_answer_history(
                                            db=session,
                                            session_id=st.session_state.sandbox_session_id,
                                            question_id=ans["id"],
                                            confidence_score=0,
                                            transcribed_text=transcribed,
                                            evaluation_status="Pending"
                                        )
                        except Exception as sync_err:
                            print(f"Error in sync transcription: {sync_err}")
                            ans["transcribing"] = False

            # Bounded final wait for any active thread, just in case (max 10 seconds)
            import time
            for _ in range(20):
                any_transcribing = any(ans.get("transcribing", False) for ans in st.session_state.sandbox_answers.values())
                if any_transcribing:
                    time.sleep(0.5)
                else:
                    break

            # Evaluate all pending voice answers in a single batch!
            voice_answers = [ans for ans in st.session_state.sandbox_answers.values() if ans.get("is_voice") and not ans.get("ai_evaluated")]
            if voice_answers:
                mode = st.session_state.get("sandbox_analysis_mode", "batch")
                spinner_msg = (
                    "🤖 ИИ параллельно анализирует ваши ответы по одному (langchain batch)... Пожалуйста, подождите."
                    if mode == "single"
                    else "🤖 ИИ анализирует ваши ответы в едином запросе... Пожалуйста, подождите."
                )
                with st.spinner(spinner_msg):
                    with get_db_session() as session:
                        try:
                            # Use our batch evaluator
                            eval_results = manager.evaluate_transcribed_answers_batch(
                                db_session=session,
                                session_id=st.session_state.sandbox_session_id,
                                answers_data=voice_answers,
                                analysis_mode=mode
                            )
                            
                            # Update our session state ratings with evaluated batch results
                            for res in eval_results:
                                # Find corresponding answer in state and update it
                                for q_idx, ans in st.session_state.sandbox_answers.items():
                                    if ans["id"] == res["id"]:
                                        ans["ai_evaluated"] = True
                                        ans["ai_result"] = {
                                            "score": res["score"],
                                            "criteria": res["criteria"],
                                            "what_was_good": res["what_was_good"],
                                            "what_was_bad_or_missing": res["what_was_bad_or_missing"],
                                            "verdict": res["verdict"],
                                            "summary": res["summary"],
                                            "transcribed_text": res["transcribed_text"]
                                        }
                                        ans["rating"] = res["score"]
                                        break
                                
                                # Add to sandbox_ratings
                                st.session_state.sandbox_ratings.append({
                                    "id": res["id"],
                                    "question_text": res["question_text"],
                                    "question_type": next(ans["question_type"] for ans in voice_answers if ans["id"] == res["id"]),
                                    "rating": res["score"],
                                    "ai_evaluated": True,
                                    "verdict": res["verdict"],
                                    "transcribed_text": res["transcribed_text"],
                                    "ai_result": {
                                        "score": res["score"],
                                        "criteria": res["criteria"],
                                        "what_was_good": res["what_was_good"],
                                        "what_was_bad_or_missing": res["what_was_bad_or_missing"],
                                        "verdict": res["verdict"],
                                        "summary": res["summary"],
                                        "transcribed_text": res["transcribed_text"]
                                    }
                                })
                        except Exception as eval_err:
                            st.error(f"Ошибка при батч-оценке ответов: {eval_err}")
            
            with get_db_session() as session:
                finish_training_session(session, st.session_state.sandbox_session_id)
            st.session_state.sandbox_session_active = False
            st.session_state.sandbox_finished = True
            st.rerun()

        # Control Buttons Row
        st.write("")
        col_show, col_bad, col_finish, col_spacer = st.columns([0.3, 0.25, 0.25, 0.2])
        
        with col_show:
            if st.button("👁️ Показать эталонный ответ", key="sandbox_toggle_expected", use_container_width=True):
                st.session_state.sandbox_show_expected = True
                st.rerun()

        with col_bad:
            if st.button("👎 Дефектный вопрос?", key="sandbox_mark_bad", help="Пометить вопрос как некорректный, убрать его из будущих тренировок и пропустить", use_container_width=True):
                with get_db_session() as session:
                    mark_question_as_bad(session, q["id"])
                st.toast(f"Вопрос #{q['id']} помечен как дефектный и скрыт!", icon="👎")
                
                # Skip logic
                if idx + 1 < total_q:
                    st.session_state.sandbox_current_index += 1
                    st.session_state.sandbox_show_expected = False
                else:
                    trigger_final_evaluation(None)
                
                st.rerun()

        with col_finish:
            if st.button("🏁 Завершить досрочно", key="sandbox_early_finish", help="Завершить тренировку сейчас и показать результаты пройденных вопросов", use_container_width=True):
                trigger_final_evaluation(user_audio)

        # 🎙️ Voice Input and AI Evaluation Block
        st.write("")
        st.markdown("##### 🎙️ Запишите ваш устный ответ:")
        user_audio = st.audio_input("Record your answer", key=f"audio_input_{q['id']}")

        if user_audio is not None:
            is_last = (idx + 1 == total_q)
            btn_label = "🏁 Завершить сессию" if is_last else "➡️ Следующий вопрос"
            
            if st.button(btn_label, key="sandbox_voice_next_btn", type="primary", use_container_width=True):
                if not is_last:
                    try:
                        audio_bytes = user_audio.read()
                        temp_dir = Path("data/audio")
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        temp_audio_path = temp_dir / f"session_{st.session_state.sandbox_session_id}_q_{q['id']}_temp.wav"
                        with open(temp_audio_path, "wb") as f:
                            f.write(audio_bytes)
                        
                        st.session_state.sandbox_answers[idx] = {
                            "id": q["id"],
                            "question_text": q["question_text"],
                            "expected_answer": q["expected_answer"],
                            "question_type": q["question_type"],
                            "transcribed_text": "(Распознавание речи...)",
                            "is_voice": True,
                            "ai_evaluated": False,
                            "transcribing": True,
                            "temp_audio_path": temp_audio_path
                        }
                        
                        import threading
                        def run_bg_transcription(sess_id, q_id, q_idx, file_path):
                            try:
                                transcribed = manager.audio_manager.process_user_audio(file_path)
                                if not transcribed:
                                    transcribed = "(Тишина или неразборчивая речь)"
                                
                                if "sandbox_answers" in st.session_state and q_idx in st.session_state.sandbox_answers:
                                    st.session_state.sandbox_answers[q_idx]["transcribed_text"] = transcribed
                                    st.session_state.sandbox_answers[q_idx]["transcribing"] = False
                                    
                                with get_db_session() as session:
                                    from sqlalchemy import select
                                    from src.database.models import AnswerHistory
                                    stmt = select(AnswerHistory).where(
                                        AnswerHistory.session_id == sess_id,
                                        AnswerHistory.question_id == q_id
                                    )
                                    db_history = session.scalar(stmt)
                                    if db_history:
                                        db_history.transcribed_text = transcribed
                                    else:
                                        create_answer_history(
                                            db=session,
                                            session_id=sess_id,
                                            question_id=q_id,
                                            confidence_score=0,
                                            transcribed_text=transcribed,
                                            evaluation_status="Pending"
                                        )
                            except Exception as th_err:
                                print(f"Error in bg transcription: {th_err}")
                                if "sandbox_answers" in st.session_state and q_idx in st.session_state.sandbox_answers:
                                    st.session_state.sandbox_answers[q_idx]["transcribing"] = False
                        
                        threading.Thread(
                            target=run_bg_transcription,
                            args=(st.session_state.sandbox_session_id, q["id"], idx, temp_audio_path)
                        ).start()
                        
                        st.session_state.sandbox_current_index += 1
                        st.session_state.sandbox_show_expected = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при фоновом запуске распознавания: {e}")
                else:
                    trigger_final_evaluation(user_audio)

        # Render Expected Answer & Self-Rating if show_expected is True and user hasn't submitted a voice answer
        elif st.session_state.sandbox_show_expected:
            st.markdown("---")
            st.markdown("### 🎯 Эталонный разбор")
            html_answer = q['expected_answer'].replace('\n', '<br>')
            st.markdown(f"<div class='answer-box' style='background: rgba(99, 102, 241, 0.05); border-left: 4px solid #6366f1; padding: 18px; border-radius: 4px 8px 8px 4px; color: #e2e8f0; font-size: 1rem; line-height: 1.6;'>{html_answer}</div>", unsafe_allow_html=True)
            
            if q["keywords"]:
                st.markdown("**Ключевые слова для самопроверки:**")
                kw_list = [k.strip() for k in q["keywords"].split(",") if k.strip()]
                kw_html = "".join([f"<span class='keyword-tag'>{k}</span>" for k in kw_list])
                st.markdown(kw_html, unsafe_allow_html=True)
                st.write("")

            st.write("")
            st.markdown("##### 📝 Оцените свой устный ответ:")
            rating = st.slider("Ваша оценка (от 1 — 'Полный провал' до 10 — 'Идеально')", min_value=1, max_value=10, value=5, step=1, key="sandbox_rating_slider")
            
            is_last = (idx + 1 == total_q)
            btn_label = "🏁 Завершить сессию" if is_last else "➡️ Следующий вопрос"
            
            if st.button(btn_label, key="sandbox_next_btn", type="primary"):
                # 1. Save AnswerHistory in DB
                with get_db_session() as session:
                    create_answer_history(
                        db=session,
                        session_id=st.session_state.sandbox_session_id,
                        question_id=q["id"],
                        confidence_score=rating
                    )
                
                # 2. Add to local ratings history for summary display
                st.session_state.sandbox_ratings.append({
                    "id": q["id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "rating": rating,
                    "ai_evaluated": False
                })

                # 3. Advance or Finish
                if not is_last:
                    st.session_state.sandbox_current_index += 1
                    st.session_state.sandbox_show_expected = False
                else:
                    trigger_final_evaluation(None)
                st.rerun()

    # 3. State: Session Finished / Summary Page
    elif st.session_state.sandbox_finished:
        st.markdown("""
        <div style="text-align: center; padding: 30px; background: rgba(16, 185, 129, 0.05); border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.2); margin-bottom: 25px;">
            <h2 style="color: #34d399; margin: 0;">🎉 Тренировка успешно завершена!</h2>
            <p style="color: #cbd5e1; font-size: 1.1rem; margin-top: 10px;">Вы отлично потрудились! Все результаты сохранены в базе данных.</p>
        </div>
        """, unsafe_allow_html=True)

        ratings_list = st.session_state.sandbox_ratings
        
        if ratings_list:
            total_answered = len(ratings_list)
            avg_rating = sum(r["rating"] for r in ratings_list) / total_answered
            
            # Show Metrics
            col_metric1, col_metric2 = st.columns(2)
            with col_metric1:
                st.metric(label="Отвечено вопросов", value=f"{total_answered} из {len(st.session_state.sandbox_questions)}")
            with col_metric2:
                st.metric(label="Средняя оценка", value=f"{avg_rating:.1f} / 10")
            
            st.write("")
            st.markdown("### 📋 Детализация оценок")
            
            # Show a premium summary collapsible detailed layout
            for r in ratings_list:
                ai_badge = "🤖 Оценка ИИ" if r.get("ai_evaluated") else "📝 Самооценка"
                badge_color = "#818cf8" if r.get("ai_evaluated") else "#94a3b8"
                
                with st.expander(f"📌 Вопрос #{r['id']} ({r['question_type']}) — Оценка: {r['rating']} / 10 ({ai_badge})"):
                    st.markdown(f"<div style='font-size: 1.05rem; font-weight: 500; color: #f0f2f6; margin-bottom: 15px;'>{r['question_text']}</div>", unsafe_allow_html=True)
                    
                    if r.get("ai_evaluated") and r.get("ai_result"):
                        result = r["ai_result"]
                        
                        st.markdown(f"**🗣️ Ваш распознанный ответ (STT):**")
                        st.info(result.get('transcribed_text', r.get('transcribed_text', '')))
                        
                        # Criteria Scores Columns
                        st.markdown("##### 📊 Оценки по критериям:")
                        crit_cols = st.columns(len(result['criteria']))
                        for c_idx, crit in enumerate(result['criteria']):
                            with crit_cols[c_idx]:
                                st.markdown(f"""
                                <div style="text-align: center; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 8px;">
                                    <small style="color: #94a3b8; font-weight: 600; font-size: 0.75rem;">{crit['criterion']}</small>
                                    <h3 style="color: #818cf8; margin: 5px 0; font-size: 1.3rem;">{crit['score']} / 10</h3>
                                    <p style="color: #cbd5e1; font-size: 0.75rem; margin: 0; line-height: 1.2;">{crit['explanation']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.write("")
                        # Strengths vs Weaknesses side-by-side
                        col_good, col_bad = st.columns(2)
                        with col_good:
                            st.markdown(f"""
                            <div style="background: rgba(16, 185, 129, 0.05); border-left: 4px solid #10b981; padding: 15px; border-radius: 4px; height: 100%;">
                                <strong style="color: #34d399; font-size: 0.9rem;">🟢 Что было хорошо:</strong>
                                <p style="color: #cbd5e1; font-size: 0.85rem; margin-top: 8px; line-height: 1.4;">{result['what_was_good']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_bad:
                            st.markdown(f"""
                            <div style="background: rgba(239, 68, 68, 0.05); border-left: 4px solid #ef4444; padding: 15px; border-radius: 4px; height: 100%;">
                                <strong style="color: #f87171; font-size: 0.9rem;">🔴 Чего не хватило / Ошибки:</strong>
                                <p style="color: #cbd5e1; font-size: 0.85rem; margin-top: 8px; line-height: 1.4;">{result['what_was_bad_or_missing']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.write("")
                        # Verdict & Recommendations
                        st.markdown(f"""
                        <div style="background: rgba(99, 102, 241, 0.05); border-left: 4px solid #6366f1; padding: 15px; border-radius: 4px;">
                            <strong style="color: #818cf8; font-size: 0.9rem;">💡 Резюме и Вердикт ИИ:</strong>
                            <p style="color: #cbd5e1; font-size: 0.85rem; margin-top: 8px; line-height: 1.4;">{result['verdict']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.02); border-left: 4px solid #94a3b8; padding: 15px; border-radius: 4px;">
                            <strong style="color: #94a3b8; font-size: 0.9rem;">📝 Самооценка:</strong>
                            <p style="color: #cbd5e1; font-size: 0.85rem; margin-top: 8px;">Вы оценили свой ответ на {r['rating']} из 10.</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Вы пометили все вопросы в этой сессии как дефектные/пропущенные.")

        st.write("")
        if st.button("🥋 Вернуться в меню тренировок", type="primary", use_container_width=True):
            st.session_state.sandbox_session_active = False
            st.session_state.sandbox_finished = False
            st.session_state.sandbox_questions = []
            st.session_state.sandbox_answers = {}
            st.rerun()
