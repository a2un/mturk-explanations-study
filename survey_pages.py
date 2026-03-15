import time
from datetime import datetime, timezone

import streamlit as st

from config import MAX_ATTEMPTS, PAGE_CONSENT, PAGE_COMPLETE, PAGE_SURVEY, SPEED_FLAG_SECS,PASS_SCORE
from utils import (
    get_attempt_count, get_qualified_worker, increment_attempt,
    mark_worker_qualified, pick_new_problem, record_completed_problem,
    record_completion_code, render_problem, reshuffle_screener_options,
    save_response, verify_worker_id,
)

def _active_questions():
    if st.session_state.get("screener_escalated"):
        return st.session_state.questions_escalated
    return st.session_state.questions_standard


def page_screener():
    st.markdown(
        "<h2 style='margin:0 0 0.1rem'>Java Eligibility Check</h2>"
        "<p style='color:#d1c4e9;font-size:0.9rem;margin:0 0 0.9rem'>"
        "This task requires Java programming proficiency. You are allowed to perform "
        "the task only if you pass the test, and payment will only be given if you do both: "
        "passing the eligibility test and performing the task. "
        "Enter your MTurk ID to start the eligibility test.</p>",
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

    # --- Skip screener for workers who already qualified ---
    qualified = get_qualified_worker(wid)
    if qualified:
        prev_score = qualified["score"]
        st.success(
            f"✓ **Welcome back!** You already passed the eligibility check "
            f"({prev_score}/3). Skipping ahead…"
        )
        st.session_state.java_level = f"Passed screener ({prev_score}/3)"
        st.session_state.demographics.update({
            "java_screener_score":     prev_score,
            "java_screener_passed":    True,
            "java_screener_returning": True,
        })
        done_count = len(qualified.get("completed_problems", []))
        if done_count:
            st.caption(f"You have completed {done_count} task(s) so far.")
        col, _ = st.columns([1, 3])
        with col:
            if st.button("Continue →"):
                st.session_state.page = PAGE_CONSENT
                st.rerun()
        return

    attempt_count = get_attempt_count(wid)
    if attempt_count >= MAX_ATTEMPTS:
        st.error(
            "We are sorry you didn't pass the eligibility test. Please close this form."
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
        mark_worker_qualified(wid, score)
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
            "We are sorry you didn't pass the eligibility test. Please close this form."
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

    # ── CHANGED: replaced checkbox with anonymization notice + linked consent form + radio ──
    st.markdown(
        "Your responses will only be used for research purposes and the responses will be **ANONYMIZED**.\n\n"
        "Please read the attached [consent form](https://example.com/consent-form) and provide your consent below:",
        unsafe_allow_html=False,
    )

    consent_check = st.radio(
        "Do you consent to participate?",
        ["I consent", "I do not consent"],
        key="consent_check",
        index=None,
    )
    worker_ok = bool(st.session_state.worker_id)
    # ── END CHANGED ──

    consented = consent_check == "I consent"

    if consent_check == "I do not consent":
        st.warning("You must consent to participate. Please return this HIT on MTurk without submitting.")

    if not worker_ok:
        st.caption("Enter your Worker ID to continue.")

    col, _ = st.columns([1, 3])
    with col:
        if st.button("I Agree & Begin", disabled=not (consented and worker_ok)):
            st.session_state.page = PAGE_SURVEY
            st.rerun()


def page_survey(problems):

    problem = problems[st.session_state.problem_idx]
    explanations = problem["explanations"]
    num_expl = len(explanations)

    # ── Initialise per-problem paging state ──
    if "expl_page" not in st.session_state:
        st.session_state.expl_page = 0
    if "collected_ratings" not in st.session_state:
        st.session_state.collected_ratings = []

    current_page = st.session_state.expl_page
    expl_text = explanations[current_page]

    # ── Badge + progress (top of page) ──
    st.markdown(
        '<span class="mode-badge mode-rate">EVALUATE STUDENT EXPLANATIONS</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:#a89cc8;font-size:0.85rem;margin:0.2rem 0 0.1rem'>"
        f"Explanation <strong>{current_page + 1}</strong> of "
        f"<strong>{num_expl}</strong></p>",
        unsafe_allow_html=True,
    )
    st.progress((current_page + 1) / num_expl)

    # ── Problem context ──
    render_problem(problem)

    # ── Current explanation card ──
    st.markdown(
        f'<div style="margin:0.3rem 0 0.1rem">'
        f'<strong style="color:#a78bfa;font-size:0.85rem">Explanation {current_page + 1} of {num_expl}'
        f'</strong></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="card" style="margin:0.1rem 0 0.3rem;padding:0.4rem 0.8rem">{expl_text}</div>',
        unsafe_allow_html=True,
    )

    # ── Rating questions (definitions inline with each question) ──
    _DEF_STYLE = (
        'style="background:#1e1b2e;border-left:3px solid #a78bfa;'
        'padding:0.35rem 0.7rem;border-radius:0.3rem;margin:0.3rem 0 0.15rem;'
        'font-size:0.82rem;color:#d1c4e9"'
    )

    st.markdown(
        f'<div class="def-card" {_DEF_STYLE}>'
        '<strong style="color:#a78bfa">Correct</strong> — A correct explanation explains '
        'why the line is used while implementing this program given the problem statement '
        'and source code.</div>',
        unsafe_allow_html=True,
    )
    q_correct = st.radio(
        "**Q1.** Is this explanation correct or incorrect?",
        ["Correct", "Incorrect"],
        key=f"q_correct_{current_page}", index=None,
    )

    st.markdown(
        f'<div class="def-card" {_DEF_STYLE}>'
        '<strong style="color:#a78bfa">Complete</strong> — A complete explanation covers '
        'all aspects about why the line is used while implementing this program given the '
        'problem statement and source code.</div>',
        unsafe_allow_html=True,
    )
    q_complete = st.radio(
        "**Q2.** Is this explanation complete or incomplete?",
        ["Complete", "Incomplete"],
        key=f"q_complete_{current_page}", index=None,
    )

    q_why = st.text_area(
        "**Q3.** Why did you choose those options?",
        key=f"q_why_{current_page}",
        placeholder="Explain your reasoning…", height=80,
    )

    page_filled = bool(q_correct and q_complete and q_why and q_why.strip())
    is_last = current_page == num_expl - 1

    # ── Navigation ──
    col_back, _, col_next = st.columns([1, 3, 1])

    with col_back:
        if current_page == 0:
            if st.button("← Back to Consent"):
                st.session_state.pop("expl_page", None)
                st.session_state.pop("collected_ratings", None)
                st.session_state.page = PAGE_CONSENT
                st.rerun()
        else:
            if st.button("← Previous"):
                st.session_state.expl_page -= 1
                st.rerun()

    with col_next:
        if is_last:
            if st.button("Submit ✓", disabled=not page_filled):
                _save_current_rating(current_page, expl_text, q_correct, q_complete, q_why)

                all_ratings = st.session_state.collected_ratings
                payload = {
                    "mturk_worker_id":       st.session_state.worker_id,
                    "completion_code":       st.session_state.completion_code,
                    "timestamp_utc":         datetime.now(timezone.utc).isoformat(),
                    "task_mode":             "rate",
                    "problem_index":         int(st.session_state.problem_idx),
                    "problem_id":            problem.get("problem_id"),
                    "problem_statement":     problem["problem_statement"],
                    "solution_source_code":  problem["solution_source_code"],
                    "selected_line":         problem["selected_line"],
                    "num_explanations":      num_expl,
                    "demographics":          st.session_state.demographics,
                    "java_experience_level": st.session_state.java_level,
                    "ratings":               all_ratings,
                }
                st.session_state.response_payload = payload
                save_response(payload)
                record_completed_problem(st.session_state.worker_id, int(st.session_state.problem_idx))
                record_completion_code(st.session_state.worker_id, st.session_state.completion_code)
                st.session_state.pop("expl_page", None)
                st.session_state.pop("collected_ratings", None)
                st.session_state.page = PAGE_COMPLETE
                st.rerun()
        else:
            if st.button("Next →", disabled=not page_filled):
                _save_current_rating(current_page, expl_text, q_correct, q_complete, q_why)
                st.session_state.expl_page += 1
                st.rerun()

    if not page_filled:
        st.caption("Answer all three questions to continue.")


def _save_current_rating(idx, expl_text, q_correct, q_complete, q_why):
    """Store or update the rating for explanation at index `idx`."""
    ratings = st.session_state.collected_ratings
    entry = {
        "explanation_index":    idx,
        "explanation_text":     expl_text,
        "correctness_rating":   q_correct,
        "completeness_rating":  q_complete,
        "reasoning":            q_why,
    }
    for i, r in enumerate(ratings):
        if r["explanation_index"] == idx:
            ratings[i] = entry
            return
    ratings.append(entry)


def page_complete(problems):
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

    # --- Start another task (new completion code, new problem) ---
    new_idx = pick_new_problem(problems, st.session_state.worker_id)
    if new_idx is not None:
        st.markdown("---")
        st.markdown(
            '<div style="background:#1e1b2e;border-left:3px solid #a78bfa;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:0.5rem 0;font-size:0.9rem;color:#d1c4e9">'
            '🔄 More tasks are available! You will receive a new completion code for each task.'
            '</div>',
            unsafe_allow_html=True,
        )
        hit_submitted = st.checkbox(
            "I have submitted my completion code on MTurk for the current HIT.",
            key="hit_submitted_confirm",
        )
        if not hit_submitted:
            st.caption("Please submit your current HIT on MTurk before starting a new task.")
        col, _ = st.columns([1, 3])
        with col:
            if st.button("Start New Task →", disabled=not hit_submitted):
                st.session_state.confirm_new_task = True

        if st.session_state.get("confirm_new_task"):
            st.warning(
                f"⚠️ **Please confirm:** Did you paste code **{code}** into the MTurk HIT "
                f"and click **Submit** on the MTurk page? Starting a new task without "
                f"submitting means you will **not** be paid for the task you just completed."
            )
            col_yes, col_no, _ = st.columns([1, 1, 2])
            with col_yes:
                if st.button("Yes, I submitted ✓"):
                    st.session_state.confirm_new_task = False
                    keys_to_keep = {
                        "page", "worker_id", "java_level",
                        "demographics", "questions_standard", "questions_escalated",
                    }
                    for k in list(st.session_state.keys()):
                        if k not in keys_to_keep:
                            del st.session_state[k]
                    from utils import generate_completion_code
                    st.session_state.completion_code = generate_completion_code()
                    st.session_state.problem_idx = new_idx
                    st.session_state.page = PAGE_SURVEY
                    st.rerun()
            with col_no:
                if st.button("No, go back"):
                    st.session_state.confirm_new_task = False
                    st.rerun()
    else:
        st.markdown(
            '<div style="background:#1e1b2e;border-left:3px solid #22c55e;'
            'padding:0.6rem 0.9rem;border-radius:0.4rem;margin:1rem 0;font-size:0.9rem;color:#d1c4e9">'
            '🎉 You have completed all available tasks. Thank you for your contributions!'
            '</div>',
            unsafe_allow_html=True,
        )