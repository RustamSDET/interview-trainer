import streamlit as st
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_session
from src.database.repository import get_all_global_topics, get_local_topics_by_global, get_questions_by_local_topic, delete_question
from src.database.models import QuestionType
from src.services.ai.generator import generate_questions_for_topic_and_type, generate_questions_batch

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Python SDET Interview Trainer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS Injection for Glassmorphism & High-Fidelity UI Styling
st.markdown("""
<style>
    /* Main container tweaks */
    .stApp {
        background-color: #0d0f1d;
        color: #f0f2f6;
    }
    
    /* Modern titles */
    h1 {
        font-family: 'Outfit', 'Inter', sans-serif !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4f46e5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px !important;
    }
    
    /* Glassmorphic custom styled Expanders */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(8px) !important;
        margin-bottom: 12px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="stExpander"]:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.15) !important;
        transform: translateY(-1px);
    }
    
    /* Badge classes for Question Types */
    .qtype-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 15px;
        border: 1px solid;
    }
    .badge-theory {
        background-color: rgba(99, 102, 241, 0.15) !important;
        color: #818cf8 !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    .badge-coding {
        background-color: rgba(16, 185, 129, 0.15) !important;
        color: #34d399 !important;
        border-color: rgba(16, 185, 129, 0.3) !important;
    }
    .badge-bughunting {
        background-color: rgba(244, 63, 94, 0.15) !important;
        color: #fb7185 !important;
        border-color: rgba(244, 63, 94, 0.3) !important;
    }
    
    /* Custom Capsule Tag for keywords */
    .keyword-tag {
        display: inline-block;
        background: rgba(255, 255, 255, 0.06);
        color: #cbd5e1;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        margin-right: 6px;
        margin-bottom: 6px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    /* Answer box styling */
    .answer-box {
        background: rgba(99, 102, 241, 0.03);
        border-left: 4px solid #6366f1;
        border-radius: 4px 8px 8px 4px;
        padding: 15px;
        margin-top: 10px;
        margin-bottom: 10px;
        color: #cbd5e1;
    }
    
    /* Global layout enhancements */
    div.stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px 8px 0px 0px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    div.stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: #818cf8;
    }
    div.stTabs [aria-selected="true"] {
        background-color: rgba(99, 102, 241, 0.1) !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
        color: #818cf8 !important;
    }
    
    /* Custom container for questions inside subtopics */
    .question-card {
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATABASE DATA LOADING (With Streamlit Caching)
# ---------------------------------------------------------

def load_hierarchy_data():
    """
    Fetches the entire Topics -> Subtopics -> Questions hierarchy from SQLite.
    Cached for fast rendering, cleared on demand after live question generation.
    """
    with get_db_session() as session:
        topics = get_all_global_topics(session)
        hierarchy = []
        for gt in topics:
            local_topics = get_local_topics_by_global(session, gt.id)
            gt_data = {
                "id": gt.id,
                "name": gt.name,
                "description": gt.description,
                "local_topics": []
            }
            for lt in local_topics:
                questions = get_questions_by_local_topic(session, lt.id)
                lt_data = {
                    "id": lt.id,
                    "name": lt.name,
                    "description": lt.description,
                    "allowed_question_types": lt.allowed_question_types,  # Load dynamic types!
                    "questions": []
                }
                for q in questions:
                    lt_data["questions"].append({
                        "id": q.id,
                        "question_text": q.question_text,
                        "expected_answer": q.expected_answer,
                        "question_type": q.question_type,
                        "keywords": q.keywords,
                        "code_snippet": q.code_snippet
                    })
                gt_data["local_topics"].append(lt_data)
            hierarchy.append(gt_data)
        return hierarchy

# Load the cached data
hierarchy = load_hierarchy_data()

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & STATS
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 20px 0;'><h2 style='color: #818cf8; margin: 0;'>🎓 SDET Trainer</h2><small style='color: #64748b;'>Python Interview Sandbox</small></div>", unsafe_allow_html=True)
    st.write("---")
    
    # Calculate global database metrics
    total_globals = len(hierarchy)
    total_locals = sum(len(gt["local_topics"]) for gt in hierarchy)
    total_questions = sum(sum(len(lt["questions"]) for lt in gt["local_topics"]) for gt in hierarchy)
    
    # Metrics display in sidebar
    st.markdown("### 📊 Статистика базы")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Темы", value=total_globals)
        st.metric(label="Подтемы", value=total_locals)
    with col2:
        st.metric(label="Вопросы", value=total_questions)
        
    st.write("---")
    st.markdown("### 🧠 О системе")
    st.info(
        "Данный интерактивный тренажер использует **Vertex AI (Gemini)** для динамической генерации "
        "глубоких технических вопросов с фокусом на Python SDET, "
        "включая разборы багов, написание качественного тестового кода и проверку теории."
    )

# ---------------------------------------------------------
# MAIN APP HEADER
# ---------------------------------------------------------

st.title("Python SDET Interview Trainer")
st.markdown("<p style='color: #94a3b8; font-size: 1.1rem; margin-top: -10px;'>Многоуровневый интерактивный тренажер технических интервью</p>", unsafe_allow_html=True)

# Define Tabs
tab_db, tab_gen = st.tabs(["📚 База вопросов", "🔮 Генерация вопросов"])

# ---------------------------------------------------------
# TAB 1: DATABASE QUESTIONS BROWSER (Theme -> Subtheme -> Type -> Question)
# ---------------------------------------------------------

with tab_db:
    st.markdown("### Просмотр доступных вопросов по темам")
    st.markdown("<span style='color: #64748b;'>Нажимайте на раскрывающиеся toggle списки, чтобы изучить иерархию и вопросы.</span>", unsafe_allow_html=True)
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
                        type_questions = [q for q in lt["questions"] if q["question_type"].value == qtype]
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
                                    st.markdown(f"<div class='question-card'>", unsafe_allow_html=True)
                                    
                                    # Badge matching type
                                    badge_class = "badge-theory"
                                    if qtype == "Algorithms":
                                        badge_class = "badge-coding"
                                    elif qtype == "BugHunting":
                                        badge_class = "badge-bughunting"
                                    elif qtype in ["TestArch", "TestDesign"]:
                                        badge_class = "badge-theory" # Neutral indigo
                                        
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
                                        col_btn_sp, col_btn_del = st.columns([0.8, 0.2])
                                        with col_btn_del:
                                            if st.button("🗑️ Удалить вопрос", key=f"del_{q['id']}", use_container_width=True):
                                                st.session_state[confirm_key] = True
                                                st.rerun()
                                        
                                    st.markdown("</div>", unsafe_allow_html=True)
                                    if q_idx < q_count:
                                        st.write("---")

# ---------------------------------------------------------
# TAB 2: AI QUESTION GENERATOR FORM (Dynamic Allowed Types)
# ---------------------------------------------------------

with tab_gen:
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
