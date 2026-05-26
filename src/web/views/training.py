import streamlit as st
from src.database.connection import get_db_session
from src.database.repository import (
    create_training_session,
    finish_training_session,
    create_answer_history,
    mark_question_as_bad,
)
from src.business.randomizer import get_random_questions

def render_training():
    """
    Renders the Sandbox Training Camp tab.
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

    # 1. State: Config / Start Page
    if not st.session_state.sandbox_session_active and not st.session_state.sandbox_finished:
        st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.02); padding: 25px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 25px;">
            <h4 style="color: #818cf8; margin-top: 0;">🥋 Режим «Песочница» (Sandbox Mode)</h4>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                В этом режиме вам будет предложено случайное количество вопросов из базы данных. 
                Вы можете отвечать на них устно, засекать время самостоятельно, после чего сравнивать 
                свой ответ с эталонным и выставлять себе честную оценку от 1 до 10.
            </p>
            <ul style="color: #94a3b8; font-size: 0.9rem; padding-left: 20px;">
                <li>Все вопросы выбираются случайным образом.</li>
                <li>Вопросы, помеченные как некачественные (Дефектные), автоматически исключаются.</li>
                <li>Каждая сессия сохраняется в историю базы данных со всеми выставленными оценками.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        with st.form("sandbox_config_form"):
            num_q = st.slider("Количество вопросов в сессии", min_value=1, max_value=20, value=5, step=1, help="Выберите, сколько вопросов вы хотите пройти за этот раунд.")
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
                            "code_snippet": q.code_snippet
                        }
                        for q in random_qs
                    ]
                    st.session_state.sandbox_current_index = 0
                    st.session_state.sandbox_session_id = db_sess.id
                    st.session_state.sandbox_session_active = True
                    st.session_state.sandbox_finished = False
                    st.session_state.sandbox_show_expected = False
                    st.session_state.sandbox_ratings = []
                    session_created = True
                    
            if session_created:
                st.toast("Сессия успешно создана! Начинаем...", icon="🚀")
                st.rerun()

    # 2. State: Active Training Session
    elif st.session_state.sandbox_session_active:
        questions = st.session_state.sandbox_questions
        idx = st.session_state.sandbox_current_index
        total_q = len(questions)
        q = questions[idx]

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

        st.markdown(f"<div class='question-card'>", unsafe_allow_html=True)
        st.markdown(
            f"<h4>Вопрос #{q['id']} <span class='qtype-badge {badge_class}'>{q['question_type']}</span></h4>", 
            unsafe_allow_html=True
        )
        st.markdown(f"<div style='font-size: 1.15rem; font-weight: 500; line-height: 1.6; color: #f0f2f6; margin-bottom: 20px;'>{q['question_text']}</div>", unsafe_allow_html=True)

        if q["code_snippet"]:
            st.markdown("**Код / Сниппет:**")
            st.code(q["code_snippet"], language="python")
        st.markdown("</div>", unsafe_allow_html=True)

        # Control Buttons Row
        col_show, col_bad, col_spacer = st.columns([0.3, 0.25, 0.45])
        
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
                    # If it was the last question, finish the session
                    with get_db_session() as session:
                        finish_training_session(session, st.session_state.sandbox_session_id)
                    st.session_state.sandbox_session_active = False
                    st.session_state.sandbox_finished = True
                
                st.rerun()

        # Render Expected Answer & Self-Rating if show_expected is True
        if st.session_state.sandbox_show_expected:
            st.markdown("---")
            st.markdown("### 🎯 Эталонный разбор")
            st.markdown(f"<div class='answer-box' style='background: rgba(99, 102, 241, 0.05); border-left: 4px solid #6366f1; padding: 18px; border-radius: 4px 8px 8px 4px; color: #e2e8f0; font-size: 1rem; line-height: 1.6;'>{q['expected_answer'].replace('\n', '<br>')}</div>", unsafe_allow_html=True)
            
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
                    "rating": rating
                })

                # 3. Advance or Finish
                if not is_last:
                    st.session_state.sandbox_current_index += 1
                    st.session_state.sandbox_show_expected = False
                else:
                    with get_db_session() as session:
                        finish_training_session(session, st.session_state.sandbox_session_id)
                    st.session_state.sandbox_session_active = False
                    st.session_state.sandbox_finished = True
                
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
                st.metric(label="Средняя самооценка", value=f"{avg_rating:.1f} / 10")
            
            st.write("")
            st.markdown("### 📋 Детализация оценок")
            
            # Show a premium summary table
            for r_idx, r in enumerate(ratings_list, 1):
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.01); border: 1px solid rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="color: #818cf8;">Вопрос #{r['id']} ({r['question_type']})</strong>
                        <span style="background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85rem; border: 1px solid rgba(16, 185, 129, 0.3);">
                            Оценка: {r['rating']} / 10
                        </span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.9rem;">{r['question_text']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Вы пометили все вопросы в этой сессии как дефектные/пропущенные.")

        st.write("")
        if st.button("🥋 Вернуться в меню тренировок", type="primary", use_container_width=True):
            st.session_state.sandbox_session_active = False
            st.session_state.sandbox_finished = False
            st.session_state.sandbox_questions = []
            st.rerun()
