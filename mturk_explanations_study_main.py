import streamlit as st

from config import apply_page_config, PAGE_SCREENER, PAGE_CONSENT, PAGE_SURVEY, PAGE_COMPLETE
from styles import inject_styles
from utils import init_session_state, load_survey_data, load_screener_questions
from survey_pages import page_screener, page_consent, page_survey, page_complete

apply_page_config()
inject_styles()

df                   = load_survey_data()
questions            = load_screener_questions()
questions_standard   = questions["standard"]
questions_escalated  = questions["escalated"]

init_session_state(df, questions_standard, questions_escalated)

page = st.session_state.page
if   page == PAGE_SCREENER: page_screener()
elif page == PAGE_CONSENT:  page_consent()
elif page == PAGE_SURVEY:   page_survey(df)
elif page == PAGE_COMPLETE: page_complete()
else:
    st.session_state.page = PAGE_SCREENER
    st.rerun()