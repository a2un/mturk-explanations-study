import streamlit as st

DATA_FILE              = "survey_data.csv"
RESPONSES_FILE         = "responses.json"
ATTEMPTS_FILE          = "screener_attempts.json"
QUESTIONS_FILE         = "screener_questions.json"
COMPLETED_WORKERS_FILE = "completed_workers.json"

MAX_ATTEMPTS    = 2
PASS_SCORE      = 3
SPEED_FLAG_SECS = 8

# MTurk API settings — set USE_MTURK_SANDBOX = False for production
USE_MTURK_SANDBOX    = True
AWS_REGION           = "us-east-1"

PAGE_SCREENER = 0
PAGE_CONSENT  = 1
PAGE_SURVEY   = 2
PAGE_COMPLETE = 3


def apply_page_config():
    st.set_page_config(
        page_title="Code Comprehension Survey",
        page_icon="🔬",
        layout="centered",
        initial_sidebar_state="collapsed",
    )