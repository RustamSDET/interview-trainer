import streamlit as st
from src.database.connection import get_db_session
from src.database.models import QuestionType
from src.services.ai.generator import generate_questions_batch

def render_generator(hierarchy: list):
    """
    Renders the AI Question Generator control panel tab.
    """
    st.markdown("### Панель управления генератором вопросов")
    st.markdown("Выберите интересующие вас темы, подтемы и конкретные типы вопросов. У каждой подтемы отображаются **только разрешенные типы вопросов** согласно схеме базы данных.")
    
    # Selection state helpers
    # Pre-populate session_state checkbox values only for allowed types of each local topic
    for gt in hierarchy:
        for lt in gt["local_topics"]:
            allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
            for qtype_str in allowed_types:
                key = f"gen_lt_{lt['id']}_{qtype_str}"
                if key not in st.session_state:
                    st.session_state[key] = False

    # Define select/deselect callbacks targeting only active allowed checkboxes
    def select_all():
        for gt in hierarchy:
            for lt in gt["local_topics"]:
                allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
                for qtype_str in allowed_types:
                    st.session_state[f"gen_lt_{lt['id']}_{qtype_str}"] = True

    def deselect_all():
        for gt in hierarchy:
            for lt in gt["local_topics"]:
                allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
                for qtype_str in allowed_types:
                    st.session_state[f"gen_lt_{lt['id']}_{qtype_str}"] = False

    # Action buttons: Select All / Clear All
    col_btn1, col_btn2, col_spacer = st.columns([0.15, 0.15, 0.7])
    with col_btn1:
        st.button("✅ Выбрать все", on_click=select_all, use_container_width=True)
    with col_btn2:
        st.button("❌ Убрать все", on_click=deselect_all, use_container_width=True)
        
    st.write("")
    
    # Render Checkbox Tree Hierarchy
    with st.form("generation_config_form"):
        # Iterate over globals
        for gt in hierarchy:
            if not gt["local_topics"]:
                continue
                
            st.markdown(f"##### 📁 {gt['name']}")
            
            # Grid for local topics under this global
            for lt in gt["local_topics"]:
                # Parse specific allowed types for this subtopic
                allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
                
                # Two main columns: Left for Subtopic, Right for dynamic checkboxes row
                col_lt_name, col_checkboxes = st.columns([0.4, 0.6])
                
                with col_lt_name:
                    st.markdown(f"**{lt['name']}**")
                    if lt["description"]:
                        st.markdown(f"<small style='color: #64748b;'>{lt['description']}</small>", unsafe_allow_html=True)
                
                with col_checkboxes:
                    # Create dynamic sub-columns matching the number of allowed types
                    num_types = len(allowed_types)
                    cols = st.columns(num_types)
                    for idx, qtype_str in enumerate(allowed_types):
                        with cols[idx]:
                            key = f"gen_lt_{lt['id']}_{qtype_str}"
                            emoji = "📖" if qtype_str == "Theory" else "💻" if qtype_str == "Algorithms" else "🐛" if qtype_str == "BugHunting" else "🏛️" if qtype_str == "TestArch" else "📐" if qtype_str == "TestDesign" else "👥"
                            st.checkbox(f"{emoji} {qtype_str}", key=key)
            st.write("---")
            
        # Submit Button inside the Form
        st.markdown("<p style='color: #64748b; font-size: 0.85rem;'>* Генерация вопросов каждого типа занимает около 10-15 секунд, так как отправляет глубокие структурированные запросы к ИИ.</p>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("🚀 Начать генерацию выбранных вопросов ИИ", type="primary", use_container_width=True)

    # Handing Generation Execution on Form Submit
    if submit_btn:
        # Collect chosen targets matching dynamic options
        selected_targets = []
        for gt in hierarchy:
            for lt in gt["local_topics"]:
                allowed_types = [t.strip() for t in lt["allowed_question_types"].split(",") if t.strip()]
                for qtype_str in allowed_types:
                    key = f"gen_lt_{lt['id']}_{qtype_str}"
                    if st.session_state.get(key, False):
                        try:
                            # Map dynamic string to QuestionType enum
                            qtype_enum = QuestionType(qtype_str)
                            selected_targets.append((lt["id"], lt["name"], qtype_enum))
                        except ValueError:
                            st.error(f"❌ Ошибка: неизвестный тип вопроса в схеме: '{qtype_str}'")
                        
        if not selected_targets:
            st.warning("⚠️ Пожалуйста, выберите хотя бы одну подтему и тип вопроса для генерации.")
        else:
            st.write("---")
            status_text = st.empty()
            
            total_targets = len(selected_targets)
            
            # Create a clean spinner container for visual delight
            with st.spinner("Связываемся с Vertex AI (Gemini) для параллельной генерации вопросов... Пожалуйста, подождите..."):
                with get_db_session() as session:
                    try:
                        # Подготовка целей в виде кортежей (ID подтемы, тип вопроса)
                        batch_targets = [(lt_id, qtype) for lt_id, lt_name, qtype in selected_targets]
                        
                        status_text.markdown(f"🤖 **Батч-генерация запущена**: Отправлено {total_targets} запросов к Vertex AI...")
                        
                        success_count = generate_questions_batch(
                            db=session,
                            targets=batch_targets,
                            overwrite=True
                        )
                        
                        status_text.markdown("🎉 **Процесс генерации вопросов завершен!**")
                        st.success(f"✅ Успешно добавлено/обновлено {success_count} вопросов в базе данных!")
                        
                        # Force Cache Refresh
                        st.cache_data.clear()
                        st.toast("База вопросов успешно обновлена!", icon="📚")
                        
                        # Rerun to populate database view tab immediately
                        st.rerun()
                    except Exception as e:
                        status_text.empty()
                        st.error(f"❌ Произошла ошибка во время генерации: {e}")
