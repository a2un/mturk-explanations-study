# =============================================================================
# pages.py  —  Four compact, scroll-free page renderers
# =============================================================================

import json
from datetime import datetime, timezone

import streamlit as st

from config import (
    JAVA_SCREENER_QUESTIONS,
    MAX_ATTEMPTS,
    PAGE_CONSENT,
    PAGE_COMPLETE,
    PAGE_SURVEY,
)
from utils import (
    get_attempt_count,
    increment_attempt,
    render_problem,
    reshuffle_screener_options,
    save_response,
)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 0 — JAVA KNOWLEDGE SCREENER
# ─────────────────────────────────────────────────────────────────────────────

def page_screener() -> None:
    st.markdown(
        "<h2 style='margin:0 0 0.1rem'>Java Eligibility Check</h2>"
        "<p style='color:#7c6fa0;font-size:0.85rem;margin:0 0 0.9rem'>Answer all 3 questions correctly to qualify.</p>",
        unsafe_allow_html=True,
    )

    # Worker ID
    wid = st.text_input(
        "MTurk Worker ID",
        value=st.session_state.worker_id,
        placeholder="e.g. A1B2C3D4E5F6G7",
        key="screener_worker_id",
        help=f"Each Worker ID may attempt this check at most {MAX_ATTEMPTS} times.",
    ).strip()
    st.session_state.worker_id = wid

    if not wid:
        st.caption("Enter your Worker ID above to load the questions.")
        return

    # Attempt count gate
    attempt_count = get_attempt_count(wid)
    if attempt_count >= MAX_ATTEMPTS:
        st.error(
            f"**Worker ID `{wid}` is locked.** All {MAX_ATTEMPTS} allowed attempts have been used. "
            "Please return this HIT on MTurk without submitting."
        )
        return

    # Attempt counter
    current = attempt_count + 1
    if attempt_count > 0:
        st.warning(f"⚠ **Final attempt** ({current} of {MAX_ATTEMPTS}). Answer carefully.")
    else:
        st.caption(f"Attempt {current} of {MAX_ATTEMPTS}. Answers are for screening only.")

    # Questions — one expander per question keeps vertical footprint small
    answers = []
    for i, (q, opts) in enumerate(zip(JAVA_SCREENER_QUESTIONS, st.session_state.screener_options)):
        with st.expander(f"Question {i + 1} of 3", expanded=True):
            st.markdown(q["question"])
            answer = st.radio(
                "Select your answer",
                opts,
                key=f"screener_ans_{q['id']}",
                index=None,
                label_visibility="collapsed",
            )
            answers.append(answer)

    all_answered = all(a is not None for a in answers)
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        check_clicked = st.button("Check Eligibility", disabled=not all_answered, key="screener_submit")
    if not all_answered:
        st.caption("Answer all 3 questions to continue.")

    # Score & persist
    if check_clicked and all_answered:
        correct_answers = [q["correct"] for q in JAVA_SCREENER_QUESTIONS]
        score     = sum(1 for a, c in zip(answers, correct_answers) if a == c)
        new_count = increment_attempt(wid)
        st.session_state.screener_score         = score
        st.session_state.screener_checked       = True
        st.session_state.screener_attempts_used = new_count
        st.session_state.screener_answers       = answers

    # Result
    if not st.session_state.get("screener_checked"):
        return

    score     = st.session_state.screener_score
    used      = st.session_state.get("screener_attempts_used", attempt_count)
    passed    = score == 3
    exhausted = used >= MAX_ATTEMPTS

    if passed:
        st.success(f"✓ **Eligibility confirmed** — {score}/3 correct.")
        col2, _ = st.columns([1, 3])
        with col2:
            if st.button("Continue →"):
                st.session_state.java_level = f"Passed screener ({score}/3)"
                st.session_state.demographics.update({
                    "java_screener_score":    score,
                    "java_screener_passed":   True,
                    "java_screener_attempts": used,
                })
                st.session_state.page = PAGE_CONSENT
                st.rerun()

    elif exhausted:
        st.error(
            f"**Maximum attempts reached.** You scored {score}/3 on your final attempt. "
            f"Worker ID `{wid}` is now permanently locked. "
            "Please return this HIT on MTurk without submitting."
        )

    else:
        remaining = MAX_ATTEMPTS - used
        st.error(
            f"**{score}/3 correct** — all 3 required. "
            f"You have **{remaining} attempt{'s' if remaining > 1 else ''} remaining**."
        )
        col_retry, _ = st.columns([1, 3])
        with col_retry:
            if st.button("Try Again →"):
                for q in JAVA_SCREENER_QUESTIONS:
                    st.session_state.pop(f"screener_ans_{q['id']}", None)
                st.session_state.screener_options = reshuffle_screener_options()
                st.session_state.screener_checked = False
                st.session_state.screener_score   = 0
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — CONSENT
# ─────────────────────────────────────────────────────────────────────────────

def page_consent() -> None:

    st.markdown(
        "<h2 style='margin:0 0 0.1rem'>Participant Consent</h2>",
        unsafe_allow_html=True,
    )

    # Worker ID confirmation (pre-filled)
    worker_id = st.text_input(
        "MTurk Worker ID",
        value=st.session_state.worker_id,
        placeholder="e.g. A1B2C3D4E5F6G7",
        key="worker_id_input",
        help="Pre-filled from the eligibility check. Edit if incorrect.",
    )
    st.session_state.worker_id = worker_id.strip()

    # Condensed study info in a scrollable box
    with open('./study_desc/instructions.md', 'r') as f:
        instructions = f.read()
        st.markdown(instructions)
    
    # st.markdown("""
    # <div class="consent-text">
    # <strong>Purpose:</strong> This study examines how developers evaluate line-level code explanations.<br>
    # <strong>Task:</strong> You will see one programming problem, its solution, a highlighted line, and either
    # one explanation to rate <em>or</em> three options to choose from. Then answer a short set of questions.<br>
    # <strong>Duration:</strong> ~5–8 minutes.&nbsp;&nbsp;
    # <strong>Confidentiality:</strong> Responses are anonymous and used for research only.&nbsp;&nbsp;
    # <strong>Voluntary:</strong> You may withdraw at any time.
    # </div>
    # """, unsafe_allow_html=True)

    # Demographics inline — single row
    col1, col2 = st.columns(2)
    with col1:
        exp = st.selectbox(
            "Experience (optional)",
            ["Prefer not to say", "< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
            key="exp",
        )
    with col2:
        role = st.selectbox(
            "Role (optional)",
            ["Prefer not to say", "Student", "Junior Developer", "Mid-level Developer",
             "Senior Developer", "Researcher", "Other"],
            key="role",
        )
    st.session_state.demographics.update({"experience": exp, "role": role})

    consent_check = st.checkbox("I have read the above and agree to participate.", key="consent_check")
    worker_ok     = bool(st.session_state.worker_id)

    if not worker_ok:
        st.caption("Enter your Worker ID to continue.")

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("I Agree & Begin", disabled=not (consent_check and worker_ok)):
            st.session_state.page = PAGE_SURVEY
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — SURVEY TASK
# ─────────────────────────────────────────────────────────────────────────────

def page_survey(df) -> None:
    row  = df.iloc[st.session_state.problem_idx]
    mode = st.session_state.task_mode

    badge_class = "mode-rate" if mode == "rate" else "mode-pick"
    badge_text  = "EVALUATE EXPLANATION" if mode == "rate" else "IDENTIFY CORRECT EXPLANATION"
    st.markdown(f'<span class="mode-badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)

    render_problem(row)

    # ── MODE A: Rate a single explanation ─────────────────────────────────────
    if mode == "rate":
        st.markdown(
            f'<div class="card" style="margin-top:0.5rem">{row["explanation"]}</div>',
            unsafe_allow_html=True,
        )

        q_correct = st.radio(
            "**Q1.** Is this explanation correct or incorrect?",
            ["Correct — it accurately describes what the line does",
             "Incorrect — it does not accurately describe what the line does"],
            key="q_correct", index=None,
        )
        q_complete = st.radio(
            "**Q2.** Is this explanation complete or incomplete?",
            ["Complete — it covers all important aspects of the line",
             "Incomplete — it is missing important aspects of the line"],
            key="q_complete", index=None,
        )
        q_why = st.text_area(
            "**Q3.** Why did you choose those options?",
            key="q_why", placeholder="Explain your reasoning…", height=90,
        )

        all_required = bool(q_correct and q_complete and q_why and q_why.strip())
        answers = {
            "correctness_rating":  q_correct,
            "completeness_rating": q_complete,
            "reasoning":           q_why,
        }

    # ── MODE B: Pick the correct explanation ──────────────────────────────────
    else:
        options       = st.session_state.options_order
        option_labels = [f"Option {chr(65 + i)}" for i in range(len(options))]

        for i, (_, text) in enumerate(options):
            st.markdown(
                f'<div class="expl-option">'
                f'<strong style="color:#a78bfa">{option_labels[i]}.</strong> {text}'
                f'</div>',
                unsafe_allow_html=True,
            )

        q_pick = st.radio(
            "Select the correct explanation:",
            option_labels, key="q_pick", index=None,
        )

        selected_key = None
        if q_pick:
            selected_key = options[option_labels.index(q_pick)][0]

        all_required = bool(q_pick)
        answers = {
            "selected_option_label": q_pick,
            "selected_option_key":   selected_key,
            "is_correct":            selected_key == "correct",
            "options_order": [
                {"position": option_labels[i], "key": k, "text_preview": t[:60] + "…"}
                for i, (k, t) in enumerate(options)
            ],
        }

    col_back, _, col_next = st.columns([1, 3, 1])
    with col_back:
        if st.button("← Back"):
            st.session_state.page = PAGE_CONSENT
            st.rerun()
    with col_next:
        if st.button("Submit ✓", disabled=not all_required):
            payload = {
                "mturk_worker_id":       st.session_state.worker_id,
                "completion_code":       st.session_state.completion_code,
                "timestamp_utc":         datetime.now(timezone.utc).isoformat(),
                "task_mode":             mode,
                "problem_index":         int(st.session_state.problem_idx),
                "problem_statement":     row["problem_statement"],
                "solution_source_code":  row["solution_source_code"],
                "selected_line":         row["selected_line"],
                "correct_explanation":   row["explanation"],
                "demographics":          st.session_state.demographics,
                "java_experience_level": st.session_state.java_level,
                "responses":             answers,
            }
            st.session_state.response_payload = payload
            save_response(payload)
            st.session_state.page = PAGE_COMPLETE
            st.rerun()

    if not all_required:
        st.caption("Answer all questions before submitting.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — COMPLETION
# ─────────────────────────────────────────────────────────────────────────────

def page_complete() -> None:
    code   = st.session_state.completion_code
    worker = st.session_state.worker_id or "Not provided"

    st.markdown(
        "<h2 style='margin:0 0 0.2rem'>Survey Complete ✓</h2>"
        "<p style='color:#a89cc8;font-size:0.9rem;margin:0 0 0.8rem'>"
        "Thank you for participating. Copy your completion code below.</p>",
        unsafe_allow_html=True,
    )

    # Completion code — prominent, copyable
    st.markdown(f"""
    <div class="completion-code-wrapper">
        <div class="completion-code-label">Paste this code into the MTurk HIT form</div>
        <div class="completion-code">{code}</div>
        <div class="completion-code-hint">Click to select &middot; Ctrl+C / Cmd+C</div>
    </div>
    """, unsafe_allow_html=True)
    st.code(code, language=None)

    # Compact instructions
    st.markdown(f"""
    <div class="mturk-box">
        1. Return to the MTurk HIT page.&nbsp;&nbsp;
        2. Find the <em>Survey Code</em> field.&nbsp;&nbsp;
        3. Paste <strong>{code}</strong> and click <strong>Submit</strong>.<br>
        <span style="font-size:0.82rem;color:#7c6fa0">Worker ID: {worker}</span>
    </div>
    """, unsafe_allow_html=True)

    if "response_payload" in st.session_state:
        with st.expander("View recorded response (JSON)"):
            st.json(st.session_state.response_payload)

    col_c, _, _ = st.columns([1, 2, 1])
    with col_c:
        if st.button("Restart"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()