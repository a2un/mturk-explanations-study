import json
import random
import re
import string
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from config import (
    ATTEMPTS_FILE, COMPLETED_WORKERS_FILE, DATA_FILE,
    PAGE_SCREENER, QUALIFIED_WORKERS_FILE, QUESTIONS_FILE,
    RESPONSES_FILE, USE_MTURK_SANDBOX, AWS_REGION,
)


@st.cache_data
def load_survey_data(path=DATA_FILE):
    try:
        return pd.read_csv(path).reset_index(drop=True)
    except FileNotFoundError:
        st.error(f"Could not find `{path}`. Place it in the data/ folder and restart.")
        st.stop()


@st.cache_data
def load_screener_questions(path=QUESTIONS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Could not find `{path}`. Place it in the data/ folder and restart.")
        st.stop()


def generate_completion_code():
    chars = string.ascii_uppercase + string.digits
    return "-".join("".join(random.choices(chars, k=4)) for _ in range(3))


def save_response(payload):
    try:
        with open(RESPONSES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        st.warning(f"Could not save response: {exc}")


# ---------------------------------------------------------------------------
# Duplicate prevention — track workers who already submitted
# ---------------------------------------------------------------------------

def _load_completed_workers():
    try:
        with open(COMPLETED_WORKERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_completed_workers(data):
    try:
        with open(COMPLETED_WORKERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        st.warning(f"Could not persist completed-workers list: {exc}")


def mark_worker_completed(worker_id):
    workers = _load_completed_workers()
    if worker_id not in workers:
        workers.append(worker_id)
        _save_completed_workers(workers)


def has_worker_completed(worker_id):
    if not worker_id:
        return False
    return worker_id in _load_completed_workers()


# ---------------------------------------------------------------------------
# Qualified workers — skip screener for workers who already passed
# ---------------------------------------------------------------------------

def _load_qualified_workers():
    try:
        with open(QUALIFIED_WORKERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_qualified_workers(data):
    try:
        with open(QUALIFIED_WORKERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        st.warning(f"Could not persist qualified-workers list: {exc}")


def mark_worker_qualified(worker_id, score):
    workers = _load_qualified_workers()
    if worker_id not in workers:
        workers[worker_id] = {
            "score": score,
            "completion_codes": [],
            "completed_problems": [],
            "qualified_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_qualified_workers(workers)


def record_completion_code(worker_id, code):
    """Append a completion code to this worker's list."""
    workers = _load_qualified_workers()
    rec = workers.get(worker_id)
    if rec:
        codes = rec.setdefault("completion_codes", [])
        if code not in codes:
            codes.append(code)
            _save_qualified_workers(workers)


def record_completed_problem(worker_id, problem_idx):
    """Add a problem index to this worker's completed list."""
    workers = _load_qualified_workers()
    rec = workers.get(worker_id)
    if rec:
        done = rec.setdefault("completed_problems", [])
        if problem_idx not in done:
            done.append(problem_idx)
            _save_qualified_workers(workers)


def get_qualified_worker(worker_id):
    """Returns the qualification record dict if the worker previously
    passed the screener, or None otherwise."""
    if not worker_id:
        return None
    return _load_qualified_workers().get(worker_id)


def pick_new_problem(df, worker_id):
    """Pick a random problem index the worker hasn't done yet.
    Returns the index, or None if all problems are exhausted."""
    qualified = get_qualified_worker(worker_id)
    done = qualified.get("completed_problems", []) if qualified else []
    available = [i for i in range(len(df)) if i not in done]
    if not available:
        return None
    return random.choice(available)


# ---------------------------------------------------------------------------
# MTurk Worker ID format + API validation
# ---------------------------------------------------------------------------

_WORKER_ID_PATTERN = re.compile(r"^[A-Z0-9]{10,14}$")


def is_valid_worker_id_format(worker_id):
    """Quick client-side check: MTurk Worker IDs are 10-14 uppercase
    alphanumeric characters (e.g. A1B2C3D4E5F6G7)."""
    return bool(_WORKER_ID_PATTERN.match(worker_id))


@st.cache_data(ttl=300, show_spinner=False)
def validate_worker_via_mturk(worker_id):
    """Call the MTurk API to confirm the Worker ID exists.

    Returns (is_valid: bool, message: str).
    Requires boto3 and valid AWS credentials (via env vars, IAM role, or
    ~/.aws/credentials).  Falls back gracefully if boto3 is unavailable or
    credentials are missing.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        return True, "boto3 not installed — skipping API verification."

    endpoint = (
        "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
        if USE_MTURK_SANDBOX
        else "https://mturk-requester.us-east-1.amazonaws.com"
    )

    try:
        client = boto3.client(
            "mturk",
            region_name=AWS_REGION,
            endpoint_url=endpoint,
        )
        # get_worker returns worker info; raises RequestError for invalid IDs
        client.get_worker(WorkerId=worker_id)
        return True, "Worker ID verified via MTurk API."
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("RequestError", "ServiceException"):
            return False, "MTurk API could not find this Worker ID."
        return True, f"MTurk API returned an unexpected error ({code}) — allowing entry."
    except NoCredentialsError:
        return True, "AWS credentials not configured — skipping API verification."
    except Exception as exc:
        return True, f"MTurk API check failed ({exc}) — allowing entry."


def verify_worker_id(worker_id):
    """Run all verification checks on a Worker ID.

    Returns (ok: bool, error_message: str | None).
    """
    if not worker_id:
        return False, "Please enter your Worker ID."

    if not is_valid_worker_id_format(worker_id):
        return False, (
            f"`{worker_id}` does not look like a valid MTurk Worker ID. "
            "Worker IDs are 10–14 uppercase letters and digits (e.g. A1B2C3D4E5F6G7)."
        )

    api_ok, api_msg = validate_worker_via_mturk(worker_id)
    if not api_ok:
        return False, (
            f"**Worker ID `{worker_id}` could not be verified.** {api_msg} "
            "Please double-check your ID and try again."
        )

    return True, None


def _load_attempts():
    try:
        with open(ATTEMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_attempts(data):
    try:
        with open(ATTEMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        st.warning(f"Could not persist attempt record: {exc}")


def get_attempt_count(worker_id):
    if not worker_id:
        return 0
    return _load_attempts().get(worker_id, 0)


def increment_attempt(worker_id):
    if not worker_id:
        return 0
    data = _load_attempts()
    data[worker_id] = data.get(worker_id, 0) + 1
    _save_attempts(data)
    return data[worker_id]


def reshuffle_screener_options(questions):
    shuffled = []
    for q in questions:
        opts = [q["correct"]] + q["distractors"]
        random.shuffle(opts)
        shuffled.append(opts)
    return shuffled


def init_session_state(df, questions_standard, questions_escalated):
    defaults = {
        "page":            PAGE_SCREENER,
        "worker_id":       "",
        "completion_code": generate_completion_code(),
        "java_level":      None,
        "screener_checked": False,
        "screener_score":  0,
        "demographics":    {},
        "task_mode":       random.choice(["rate", "pick"]),
        "problem_idx":     random.randint(0, len(df) - 1),
        "questions_standard":  questions_standard,
        "questions_escalated": questions_escalated,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "options_order" not in st.session_state:
        row = df.iloc[st.session_state.problem_idx]
        options = [
            ("correct",      row["explanation"]),
            ("distractor_1", row["distractor_1"]),
            ("distractor_2", row["distractor_2"]),
        ]
        random.shuffle(options)
        st.session_state.options_order = options

    if "screener_options" not in st.session_state:
        st.session_state.screener_options = reshuffle_screener_options(questions_standard)


def render_problem(row):
    st.markdown("### Problem statement")
    st.markdown(f'<div class="card">{row["problem_statement"]}</div>', unsafe_allow_html=True)
    st.markdown("### Solution source code")
    st.code(row["solution_source_code"], language="python")
    st.markdown("### Selected line")
    st.markdown(
        f'<div class="highlight-line">&#9654;&nbsp;&nbsp;{row["selected_line"]}</div>',
        unsafe_allow_html=True,
    )