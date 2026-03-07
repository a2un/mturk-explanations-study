# =============================================================================
# utils.py
# Utility functions used across pages:
#   - Streamlit session state initialisation
#   - Survey data loading (cached)
#   - Response JSON persistence
#   - Screener attempt tracking (file-backed)
#   - Shared UI renderer (problem statement / code / selected line)
#   - Completion code generator
# =============================================================================

import json
import random
import string

import pandas as pd
import streamlit as st

from config import (
    ATTEMPTS_FILE,
    DATA_FILE,
    JAVA_SCREENER_QUESTIONS,
    MAX_ATTEMPTS,
    PAGE_SCREENER,
    RESPONSES_FILE,
)


# ── Completion code ───────────────────────────────────────────────────────────

def generate_completion_code() -> str:
    """Return a random XXXX-XXXX-XXXX alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return "-".join("".join(random.choices(chars, k=4)) for _ in range(3))


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_survey_data(path: str = DATA_FILE) -> pd.DataFrame:
    """Load the survey CSV. Stops the app with an error if the file is missing."""
    try:
        return pd.read_csv(path).reset_index(drop=True)
    except FileNotFoundError:
        st.error(
            f"⚠️ Could not find `{path}`. "
            "Place it in the same folder as main.py and restart."
        )
        st.stop()


# ── Response persistence ──────────────────────────────────────────────────────

def save_response(payload: dict) -> None:
    """Append a single response record (dict) as a newline-delimited JSON entry."""
    try:
        with open(RESPONSES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        st.warning(f"Could not save response to file: {exc}")


# ── Screener attempt tracking ─────────────────────────────────────────────────

def _load_attempts() -> dict:
    """Read {worker_id: count} from disk. Returns empty dict on missing/corrupt file."""
    try:
        with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_attempts(data: dict) -> None:
    try:
        with open(ATTEMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        st.warning(f"Could not persist attempt record: {exc}")


def get_attempt_count(worker_id: str) -> int:
    """Return the number of screener attempts recorded for this worker_id."""
    if not worker_id:
        return 0
    return _load_attempts().get(worker_id, 0)


def increment_attempt(worker_id: str) -> int:
    """Increment the attempt count for worker_id, persist, and return the new count."""
    if not worker_id:
        return 0
    data = _load_attempts()
    data[worker_id] = data.get(worker_id, 0) + 1
    _save_attempts(data)
    return data[worker_id]


def reshuffle_screener_options() -> list:
    """
    Build and return a freshly shuffled list of option lists for the screener.
    One list per question; each list contains [correct, *distractors] shuffled.
    """
    shuffled = []
    for q in JAVA_SCREENER_QUESTIONS:
        opts = [q["correct"]] + q["distractors"]
        random.shuffle(opts)
        shuffled.append(opts)
    return shuffled


# ── Session state initialisation ──────────────────────────────────────────────

def init_session_state(df: pd.DataFrame) -> None:
    """
    Initialise all session-state keys that are not already set.
    Call once at the top of main.py after load_survey_data().
    """
    defaults = {
        "page":              PAGE_SCREENER,
        "worker_id":         "",
        "completion_code":   generate_completion_code(),
        "java_level":        None,
        "screener_checked":  False,
        "screener_score":    0,
        "demographics":      {},
        "task_mode":         random.choice(["rate", "pick"]),
        "problem_idx":       random.randint(0, len(df) - 1),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # options_order depends on problem_idx, so initialise separately
    if "options_order" not in st.session_state:
        row = df.iloc[st.session_state.problem_idx]
        options = [
            ("correct",      row["explanation"]),
            ("distractor_1", row["distractor_1"]),
            ("distractor_2", row["distractor_2"]),
        ]
        random.shuffle(options)
        st.session_state.options_order = options

    # Screener option shuffle (one list of shuffled options per question)
    if "screener_options" not in st.session_state:
        st.session_state.screener_options = reshuffle_screener_options()


# ── Shared UI renderer ────────────────────────────────────────────────────────

def render_problem(row: pd.Series) -> None:
    """
    Render the three shared content blocks used on the survey page:
    problem statement card, solution source code, and selected line.
    """
    st.markdown("### Problem statement")
    st.markdown(
        f'<div class="card">{row["problem_statement"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Solution source code")
    st.code(row["solution_source_code"], language="python")
    st.markdown("### Selected line")
    st.markdown(
        f'<div class="highlight-line">&#9654;&nbsp;&nbsp;{row["selected_line"]}</div>',
        unsafe_allow_html=True,
    )