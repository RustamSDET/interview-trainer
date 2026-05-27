import streamlit as st
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_session, init_db

# Initialize database and run migrations on startup
init_db()
from src.database.repository import (
    get_all_global_topics,
    get_local_topics_by_global,
    get_questions_by_local_topic,
)
from src.web.views.db_browser import render_db_browser
from src.web.views.generator import render_generator
from src.web.views.training import render_training

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
    .badge-junior {
        background-color: rgba(34, 197, 94, 0.12) !important;
        color: #4ade80 !important;
        border-color: rgba(34, 197, 94, 0.25) !important;
    }
    .badge-middle {
        background-color: rgba(245, 158, 11, 0.12) !important;
        color: #fbbf24 !important;
        border-color: rgba(245, 158, 11, 0.25) !important;
    }
    .badge-senior {
        background-color: rgba(168, 85, 247, 0.12) !important;
        color: #c084fc !important;
        border-color: rgba(168, 85, 247, 0.25) !important;
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

@st.cache_data
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
                        "code_snippet": q.code_snippet,
                        "bad_question": q.bad_question,
                        "grade": q.grade
                    })
                gt_data["local_topics"].append(lt_data)
            hierarchy.append(gt_data)
        return hierarchy

@st.cache_data
def load_sidebar_stats():
    """
    Computes global database metrics from cached hierarchy.
    """
    hierarchy_data = load_hierarchy_data()
    total_globals = len(hierarchy_data)
    total_locals = sum(len(gt["local_topics"]) for gt in hierarchy_data)
    active_questions = sum(sum(len([q for q in lt["questions"] if not q["bad_question"]]) for lt in gt["local_topics"]) for gt in hierarchy_data)
    bad_questions = sum(sum(len([q for q in lt["questions"] if q["bad_question"]]) for lt in gt["local_topics"]) for gt in hierarchy_data)
    return {
        "total_globals": total_globals,
        "total_locals": total_locals,
        "active_questions": active_questions,
        "bad_questions": bad_questions
    }


# ---------------------------------------------------------
# SIDEBAR NAVIGATION & STATS
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 20px 0;'><h2 style='color: #818cf8; margin: 0;'>🎓 SDET Trainer</h2><small style='color: #64748b;'>Python Interview Sandbox</small></div>", unsafe_allow_html=True)
    st.write("---")
    
    # Clean, modern dynamic navigation
    active_tab = st.radio(
        "🧭 Раздел меню",
        ["🥋 Тренировочный лагерь (Training)", "📚 База вопросов", "🔮 Генерация вопросов ИИ"],
        index=0  # Default to Training for immediate user focus
    )
    st.write("---")

    # Audio Language Selection with default from .env
    from src.config import AUDIO_LANGUAGE
    if "audio_language" not in st.session_state:
        st.session_state.audio_language = AUDIO_LANGUAGE
        
    st.markdown("### 🌐 Настройки звука (Audio)")
    selected_lang = st.selectbox(
        "Язык озвучки и STT",
        ["English", "Русский"],
        index=0 if st.session_state.audio_language == "en" else 1,
        key="lang_selector"
    )
    st.session_state.audio_language = "en" if selected_lang == "English" else "ru"
    st.write("---")
    
    # Calculate global database metrics using cached stats
    stats = load_sidebar_stats()
    
    # Metrics display in sidebar
    st.markdown("### 📊 Статистика базы")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Темы", value=stats["total_globals"])
        st.metric(label="Подтемы", value=stats["total_locals"])
    with col2:
        st.metric(label="Вопросы", value=stats["active_questions"])
        st.metric(label="Забраковано", value=stats["bad_questions"])
        
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

# Dynamic Router - evaluates and renders ONLY the selected view, avoiding thousands of inactive widgets
if active_tab == "🥋 Тренировочный лагерь (Training)":
    render_training()
elif active_tab == "📚 База вопросов":
    hierarchy = load_hierarchy_data()
    render_db_browser(hierarchy)
elif active_tab == "🔮 Генерация вопросов ИИ":
    hierarchy = load_hierarchy_data()
    render_generator(hierarchy)


