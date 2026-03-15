import os

import streamlit as st

DATA_DIR               = os.path.join(".", "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE              = os.path.join(DATA_DIR, "survey_data.json")
RESPONSES_FILE         = os.path.join(DATA_DIR, "responses.json")
ATTEMPTS_FILE          = os.path.join(DATA_DIR, "screener_attempts.json")
QUESTIONS_FILE         = os.path.join(DATA_DIR, "screener_questions.json")
COMPLETED_WORKERS_FILE = os.path.join(DATA_DIR, "completed_workers.json")
QUALIFIED_WORKERS_FILE = os.path.join(DATA_DIR, "qualified_workers.json")

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