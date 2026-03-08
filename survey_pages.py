import time
from datetime import datetime, timezone

import streamlit as st

from config import MAX_ATTEMPTS, PAGE_CONSENT, PAGE_COMPLETE, PAGE_SURVEY, SPEED_FLAG_SECS,PASS_SCORE
from utils import get_attempt_count, increment_attempt, render_problem, reshuffle_screener_options, save_response, verify_worker_id

def _active_questions():
    if st.session_state.get("screener_escalated"):
        return st.session_state.questions_escalated
    return st.session_state.questions_standard


def page_screener():
    st.markdown(
        "<h2 style='margin:0 0 0.1rem'>Java Eligibility Check</h2>"
        "<p style='color:#7c6fa0;font-size:0.85rem;margin:0 0 0.9rem'>"
        "Answer all 3 questions correctly to qualify.</p>",
        unsafe_allow_html=True,
    )

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

    # --- Worker ID verification (format + MTurk API + duplicate) ---
    wid_ok, wid_error = verify_worker_id(wid)
    if not wid_ok:
        st.error(wid_error)
        return

    attempt_count = get_attempt_count(wid)
    if attempt_count >= MAX_ATTEMPTS:
        st.error(
            f"**Worker ID `{wid}` is locked.** All {MAX_ATTEMPTS} allowed attempts used. "
            "Please return this HIT on MTurk without submitting."
        )
        return

    current = attempt_count + 1
    if attempt_count > 0:
        st.warning(f"⚠ **Final attempt** ({current} of {MAX_ATTEMPTS}). Answer carefully.")
    else:
        st.caption(f"Attempt {current} of {MAX_ATTEMPTS}.")

    questions = _active_questions()
    q1        = questions[0]
    q1_opts   = st.session_state.screener_options[0]
    q1_scored = st.session_state.get("q1_scored", False)

    if "q1_displayed_at" not in st.session_state:
        st.session_state.q1_displayed_at = time.monotonic()

    with st.expander("Question 1 of 3", expanded=True):
        st.markdown(q1["question"])
        ans_q1 = st.radio(
            "Select your answer", q1_opts,
            key=f"screener_ans_{q1['id']}",
            index=None, label_visibility="collapsed",
        )

    if not q1_scored:
        col, _ = st.columns([1, 3])
        with col:
            if st.button("Next →", disabled=(ans_q1 is None), key="q1_next"):
                elapsed = time.monotonic() - st.session_state.q1_displayed_at
                st.session_state.update({
                    "q1_answer":  ans_q1,
                    "q1_correct": ans_q1 == q1["correct"],
                    "q1_elapsed": elapsed,
                    "q1_scored":  True,
                    "screener_escalated": elapsed < SPEED_FLAG_SECS,
                })
                escalated = elapsed < SPEED_FLAG_SECS
                st.session_state.screener_options = reshuffle_screener_options(
                    st.session_state.questions_escalated if escalated
                    else st.session_state.questions_standard
                )
                st.rerun()
        if ans_q1 is None:
            st.caption("Answer Question 1 to continue.")
        return

    questions = _active_questions()
    if st.session_state.get("screener_escalated"):
        st.markdown(
            "<p style='color:#7c6fa0;font-size:0.8rem;margin:0.2rem 0 0.6rem'>"
            "⚡ Questions 2 and 3 have been adjusted based on your response time.</p>",
            unsafe_allow_html=True,
        )

    answers_q23 = []
    for i, (q, opts) in enumerate(zip(questions[1:], st.session_state.screener_options[1:]), start=2):
        with st.expander(f"Question {i} of 3", expanded=True):
            st.markdown(q["question"])
            ans = st.radio(
                "Select your answer", opts,
                key=f"screener_ans_{q['id']}",
                index=None, label_visibility="collapsed",
            )
            answers_q23.append(ans)

    all_answered = all(a is not None for a in answers_q23)
    col, _ = st.columns([1, 3])
    with col:
        check_clicked = st.button("Check Eligibility", disabled=not all_answered, key="screener_submit")
    if not all_answered:
        st.caption("Answer both remaining questions to continue.")

    if check_clicked and all_answered:
        all_answers = [st.session_state.q1_answer] + answers_q23
        score       = sum(a == q["correct"] for a, q in zip(all_answers, _active_questions()))
        new_count   = increment_attempt(wid)
        st.session_state.update({
            "screener_score":         score,
            "screener_checked":       True,
            "screener_attempts_used": new_count,
            "screener_answers":       all_answers,
        })

    if not st.session_state.get("screener_checked"):
        return

    score     = st.session_state.screener_score
    used      = st.session_state.get("screener_attempts_used", attempt_count)
    exhausted = used >= MAX_ATTEMPTS

    if score == PASS_SCORE:
        st.success(f"✓ **Eligibility confirmed** — {score}/3 correct.")
        col, _ = st.columns([1, 3])
        with col:
            if st.button("Continue →"):
                st.session_state.java_level = f"Passed screener ({score}/3)"
                st.session_state.demographics.update({
                    "java_screener_score":     score,
                    "java_screener_passed":    True,
                    "java_screener_attempts":  used,
                    "java_screener_escalated": st.session_state.get("screener_escalated", False),
                    "java_screener_q1_secs":   round(st.session_state.get("q1_elapsed", 0), 2),
                })
                st.session_state.page = PAGE_CONSENT
                st.rerun()

    elif exhausted:
        st.error(
            f"**Maximum attempts reached.** You scored {score}/3. "
            f"Worker ID `{wid}` is now locked. Please return this HIT without submitting."
        )

    else:
        remaining = MAX_ATTEMPTS - used
        st.error(
            f"**{score}/3 correct** — all 3 required. "
            f"**{remaining} attempt{'s' if remaining > 1 else ''} remaining.**"
        )
        col, _ = st.columns([1, 3])
        with col:
            if st.button("Try Again →"):
                keys_to_clear = [
                    "q1_scored", "q1_answer", "q1_correct", "q1_elapsed",
                    "q1_displayed_at", "screener_escalated",
                    "screener_checked", "screener_score",
                ]
                for q in st.session_state.questions_standard + st.session_state.questions_escalated:
                    keys_to_clear.append(f"screener_ans_{q['id']}")
                for k in keys_to_clear:
                    st.session_state.pop(k, None)
                st.session_state.screener_options = reshuffle_screener_options(
                    st.session_state.questions_standard
                )
                st.rerun()


def page_consent():
    st.markdown("<h2 style='margin:0 0 0.1rem'>Participant Consent</h2>", unsafe_allow_html=True)

    worker_id = st.text_input(
        "MTurk Worker ID",
        value=st.session_state.worker_id,
        placeholder="e.g. A1B2C3D4E5F6G7",
        key="worker_id_input",
        help="Pre-filled from the eligibility check. Edit if incorrect.",
    )
    st.session_state.worker_id = worker_id.strip()

    with open("study_desc/instructions.md", "r") as f:
        st.markdown(f.read())

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

    col, _ = st.columns([1, 3])
    with col:
        if st.button("I Agree & Begin", disabled=not (consent_check and worker_ok)):
            st.session_state.page = PAGE_SURVEY
            st.rerun()


def page_survey(df):

    row  = df.iloc[st.session_state.problem_idx]
    mode = st.session_state.task_mode

    badge_class = "mode-rate" if mode == "rate" else "mode-pick"
    badge_text  = "EVALUATE EXPLANATION" if mode == "rate" else "IDENTIFY CORRECT EXPLANATION"
    st.markdown(f'<span class="mode-badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)

    render_problem(row)

    if mode == "rate":
        st.markdown(f'<div class="card" style="margin-top:0.3rem">{row["explanation"]}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="def-card" style="background:#1e1b2e;border-left:3px solid #a78bfa;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:0.8rem 0 0.3rem;font-size:0.9rem;color:#d1c4e9">'
            '<strong style="color:#a78bfa">Correct</strong> — A correct explanation explains why the line is used while implementing this program given the problem statement and source code.<br>'
            '</div>',
            unsafe_allow_html=True,
        )
        q_correct = st.radio(
            "**Q1.** Is this explanation correct or incorrect?",
            ["Correct", "Incorrect"],
            key="q_correct", index=None,
        )

        st.markdown(
            '<div class="def-card" style="background:#1e1b2e;border-left:3px solid #a78bfa;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:0.8rem 0 0.3rem;font-size:0.9rem;color:#d1c4e9">'
            '<strong style="color:#a78bfa">Complete</strong> — A complete explanation covers all aspects about why the line is used while implementing this program given the problem statement and source code.<br>'
            '</div>',
            unsafe_allow_html=True,
        )
        q_complete = st.radio(
            "**Q2.** Is this explanation complete or incomplete?",
            ["Complete", "Incomplete"],
            key="q_complete", index=None,
        )

        q_why = st.text_area("**Q3.** Why did you choose those options?", key="q_why",
                             placeholder="Explain your reasoning…", height=90)

        all_required = bool(q_correct and q_complete and q_why and q_why.strip())
        answers = {
            "correctness_rating":  q_correct,
            "completeness_rating": q_complete,
            "reasoning":           q_why,
        }

    else:
        options       = st.session_state.options_order
        option_labels = [f"Option {chr(65 + i)}" for i in range(len(options))]

        for i, (_, text) in enumerate(options):
            st.markdown(
                f'<div class="expl-option"><strong style="color:#a78bfa">{option_labels[i]}.</strong> {text}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="def-card" style="background:#1e1b2e;border-left:3px solid #a78bfa;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:0.8rem 0 0.3rem;font-size:0.9rem;color:#d1c4e9">'
            '<strong style="color:#a78bfa">Correct</strong> — A correct explanation explains why the line is used while implementing this program given the problem statement and source code.<br>'
            '</div>',
            unsafe_allow_html=True,
        )
        q_pick = st.radio("**Q1.** Select the correct explanation:", option_labels, key="q_pick", index=None)
        selected_key = options[option_labels.index(q_pick)][0] if q_pick else None

        st.markdown(
            '<div class="def-card" style="background:#1e1b2e;border-left:3px solid #a78bfa;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:0.8rem 0 0.3rem;font-size:0.9rem;color:#d1c4e9">'
            '<strong style="color:#a78bfa">Complete</strong> — A complete explanation covers all aspects about why the line is used while implementing this program given the problem statement and source code.<br>'
            '</div>',
            unsafe_allow_html=True,
        )
        q_complete_pick = st.radio(
            "**Q2.** Is the explanation you selected complete or incomplete?",
            ["Complete", "Incomplete"],
            key="q_complete_pick", index=None,
        )

        q_why_pick = st.text_area("**Q3.** Why did you choose those options?", key="q_why_pick",
                                  placeholder="Explain your reasoning…", height=90)

        all_required = bool(q_pick and q_complete_pick and q_why_pick and q_why_pick.strip())
        answers = {
            "selected_option_label": q_pick,
            "selected_option_key":   selected_key,
            "is_correct":            selected_key == "correct",
            "completeness_rating":   q_complete_pick,
            "reasoning":             q_why_pick,
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


def page_complete():
    code   = st.session_state.completion_code
    worker = st.session_state.worker_id or "Not provided"

    st.markdown(
        "<h2 style='margin:0 0 0.2rem'>Survey Complete ✓</h2>"
        "<p style='color:#a89cc8;font-size:0.9rem;margin:0 0 0.8rem'>"
        "Thank you for participating. Copy your completion code below.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div class="completion-code-wrapper">
        <div class="completion-code-label">Paste this code into the MTurk HIT form</div>
        <div class="completion-code">{code}</div>
        <div class="completion-code-hint">Click to select &middot; Ctrl+C / Cmd+C</div>
    </div>
    """, unsafe_allow_html=True)
    st.code(code, language=None)
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

    col, _, _ = st.columns([1, 2, 1])
    with col:
        if st.button("Restart"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()