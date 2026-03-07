# =============================================================================
# main.py
# Entry point for the Code Comprehension Survey Streamlit app.
#
# Run with:
#     streamlit run main.py
#
# Project structure:
#     main.py       ← launch & routing (this file)
#     config.py     ← constants, page config, Java question bank
#     styles.py     ← global CSS stylesheet
#     utils.py      ← data loading, persistence helpers, session init, renderers
#     pages.py      ← four page render functions (screener, consent, survey, complete)
#     survey_data.csv  ← problem statements + explanations + distractors
# =============================================================================

import streamlit as st

from config import (
    apply_page_config,
    PAGE_SCREENER,
    PAGE_CONSENT,
    PAGE_SURVEY,
    PAGE_COMPLETE,
)
from styles import inject_styles
from utils import init_session_state, load_survey_data
from pages import page_screener, page_consent, page_survey, page_complete


# ── 1. Page configuration (must be the first Streamlit call) ──────────────────
apply_page_config()

# ── 2. Inject global CSS ──────────────────────────────────────────────────────
inject_styles()

# ── 3. Load survey data ───────────────────────────────────────────────────────
df = load_survey_data()

# ── 4. Initialise session state ───────────────────────────────────────────────
init_session_state(df)

# ── 5. Route to the current page ──────────────────────────────────────────────
_page = st.session_state.page

if _page == PAGE_SCREENER:
    page_screener()

elif _page == PAGE_CONSENT:
    page_consent()

elif _page == PAGE_SURVEY:
    page_survey(df)

elif _page == PAGE_COMPLETE:
    page_complete()

else:
    # Fallback: reset to screener if page state is somehow invalid
    st.session_state.page = PAGE_SCREENER
    st.rerun()