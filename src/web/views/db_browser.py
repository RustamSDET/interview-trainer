import streamlit as st
from src.database.connection import get_db_session
from src.database.repository import (
    delete_question,
    set_question_bad_status,
    mark_question_as_bad,
)

def render_db_browser(hierarchy: list):
    """
    Renders the Database Questions Browser tab (Theme -> Subtheme -> Type -> Question).
    """
    st.markdown("### Просмотр доступных вопросов по темам")
    col_hdr, col_toggle = st.columns([0.65, 0.35])
    with col_hdr:
        st.markdown("<span style='color: #64748b;'>Нажимайте на раскрывающиеся toggle списки, чтобы изучить иерархию и вопросы.</span>", unsafe_allow_html=True)
    with col_toggle:
        show_bad_questions = st.checkbox(
            "🔍 Показать забракованные вопросы",
            value=False,
            help="Показывать вопросы, которые были помечены как некачественные (для анализа)."
        )
    st.write("")
    
    # Iterate over Global Topics (always display them as Level 1 Expanders)
    for gt in hierarchy:
        if not gt["local_topics"]:
            continue
            
        # Level 1 Expander: Global Topic
        with st.expander(f"📁 {gt['name'].upper()}", expanded=False):
            if gt["description"]:
                st.markdown(f"<p style='color: #818cf8; font-size: 0.95rem; font-style: italic; margin-bottom: 15px;'>{gt['description']}</p>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            
            # Iterate over Local Topics (Level 2 Expanders)
            for lt in gt["local_topics"]:
                with st.expander(f"📄 {lt['name']}", expanded=False):
                    if lt["description"]:
                        st.markdown(f"<p style='font-style: italic; color: #cbd5e1; font-size: 0.9rem; margin-bottom: 15px;'>{lt['description']}</p>", unsafe_allow_html=True)
                        st.write("---")
                        
                    # Parse dynamic allowed question types for this specific subtheme
                    allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
                    
                    # Level 3 Expanders (Question Types nested inside subtheme)
                    for qtype in allowed_types:
                        # Filter loaded questions of this specific type
                        if show_bad_questions:
                            type_questions = [q for q in lt["questions"] if q["question_type"].value == qtype]
                        else:
                            type_questions = [q for q in lt["questions"] if q["question_type"].value == qtype and not q["bad_question"]]
                        q_count = len(type_questions)
                        
                        # Assign visual emojis matching the type
                        emoji = "📖" if qtype == "Theory" else "💻" if qtype == "Algorithms" else "🐛" if qtype == "BugHunting" else "🏛️" if qtype == "TestArch" else "📐" if qtype == "TestDesign" else "👥"
                        sub_expander_label = f"{emoji} {qtype} ({q_count} вопросов)"
                        
                        # Level 3 Nesting (Expander for Question Type)
                        with st.expander(sub_expander_label):
                            if q_count == 0:
                                st.markdown(f"<small style='color: #64748b;'>📝 Вопросы типа <strong>{qtype}</strong> для этой подтемы еще не сгенерированы. Вы можете сгенерировать их во вкладке <strong>'Генерация вопросов'</strong>!</small>", unsafe_allow_html=True)
                            else:
                                # Level 4: Render actual Questions
                                for q_idx, q in enumerate(type_questions, 1):
                                    # Badge matching type
                                    badge_class = "badge-theory"
                                    if qtype == "Algorithms":
                                        badge_class = "badge-coding"
                                    elif qtype == "BugHunting":
                                        badge_class = "badge-bughunting"
                                    elif qtype in ["TestArch", "TestDesign"]:
                                        badge_class = "badge-theory" # Neutral indigo
                                        
                                    if q["bad_question"]:
                                        # Styled card with red/coral border for flagged questions
                                        st.markdown(f"<div class='question-card' style='border: 1px solid rgba(244, 63, 94, 0.4); background: rgba(244, 63, 94, 0.02);'>", unsafe_allow_html=True)
                                        st.markdown(
                                            f"<h5>Вопрос #{q['id']} <span class='qtype-badge {badge_class}'>{q['question_type'].value}</span> <span class='qtype-badge' style='background-color: rgba(244, 63, 94, 0.2) !important; color: #fb7185 !important; border-color: rgba(244, 63, 94, 0.4) !important;'>⚠️ ЗАБРАКОВАН</span></h5>", 
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        st.markdown(f"<div class='question-card'>", unsafe_allow_html=True)
                                        st.markdown(
                                            f"<h5>Вопрос #{q['id']} <span class='qtype-badge {badge_class}'>{q['question_type'].value}</span></h5>", 
                                            unsafe_allow_html=True
                                        )
                                    
                                    # Question text
                                    st.markdown(f"**Вопрос:** {q['question_text']}")
                                    
                                    # Code Snippet (if exists)
                                    if q["code_snippet"]:
                                        st.markdown("**Код / Сниппет:**")
                                        st.code(q["code_snippet"], language="python")
                                        
                                    # Keywords
                                    if q["keywords"]:
                                        st.markdown("**Ключевые слова:**")
                                        kw_list = [k.strip() for k in q["keywords"].split(",") if k.strip()]
                                        kw_html = "".join([f"<span class='keyword-tag'>{k}</span>" for k in kw_list])
                                        st.markdown(kw_html, unsafe_allow_html=True)
                                        st.write("")
                                        
                                    # Expected Answer (Collapsible spoiler)
                                    with st.expander("👁️ Показать ожидаемый ответ / разбор решения"):
                                        st.markdown(f"<div class='answer-box'><strong>Эталонный ответ:</strong><br><br>{q['expected_answer'].replace('\n', '<br>')}</div>", unsafe_allow_html=True)
                                        
                                    # Deletion button and confirmation logic
                                    confirm_key = f"confirm_del_{q['id']}"
                                    if st.session_state.get(confirm_key, False):
                                        st.markdown("<p style='color: #fb7185; font-size: 0.95rem; font-weight: bold; margin-top: 10px;'>⚠️ Вы уверены, что хотите окончательно удалить этот вопрос из базы?</p>", unsafe_allow_html=True)
                                        col_conf1, col_conf2 = st.columns([0.2, 0.8])
                                        with col_conf1:
                                            if st.button("Да, удалить", key=f"yes_del_{q['id']}", type="primary", use_container_width=True):
                                                with get_db_session() as session:
                                                    delete_question(session, q['id'])
                                                st.session_state[confirm_key] = False
                                                st.toast(f"Вопрос #{q['id']} успешно удален!", icon="🗑️")
                                                st.rerun()
                                        with col_conf2:
                                            if st.button("Отмена", key=f"no_del_{q['id']}", type="secondary", use_container_width=True):
                                                st.session_state[confirm_key] = False
                                                st.rerun()
                                    else:
                                        col_btn_sp, col_btn_action, col_btn_del = st.columns([0.5, 0.25, 0.25])
                                        with col_btn_action:
                                            if q["bad_question"]:
                                                if st.button("👍 Восстановить", key=f"restore_{q['id']}", use_container_width=True):
                                                    with get_db_session() as session:
                                                        set_question_bad_status(session, q['id'], is_bad=False)
                                                    st.toast(f"Вопрос #{q['id']} успешно восстановлен!", icon="👍")
                                                    st.rerun()
                                            else:
                                                if st.button("👎 Забраковать", key=f"flag_{q['id']}", use_container_width=True):
                                                    with get_db_session() as session:
                                                        mark_question_as_bad(session, q['id'])
                                                    st.toast(f"Вопрос #{q['id']} помечен как некачественный!", icon="👎")
                                                    st.rerun()
                                        with col_btn_del:
                                            if st.button("🗑️ Удалить вопрос", key=f"del_{q['id']}", use_container_width=True):
                                                st.session_state[confirm_key] = True
                                                st.rerun()
                                        
                                    st.markdown("</div>", unsafe_allow_html=True)
                                    if q_idx < q_count:
                                        st.write("---")
