# =============================================================================
# styles.py
# Injects the global CSS stylesheet into the Streamlit app.
# Call inject_styles() once from main.py after apply_page_config().
# =============================================================================

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Base ──────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0d0d12; color: #e8e6f0; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; max-width: 760px; }

/* ── Typography ────────────────────────────────────────────────────────────── */
h2 {
    font-family: 'Space Mono', monospace;
    font-size: 1.15rem !important;
    color: #c4b5fd;
    letter-spacing: -0.01em;
    margin-bottom: 0.15rem !important;
}
h3 {
    font-size: 0.75rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #7c6fa0;
    margin: 0.6rem 0 0.15rem !important;
}

/* ── Cards ─────────────────────────────────────────────────────────────────── */
.card {
    background: #14111f;
    border: 1px solid #2a2040;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.92rem;
    line-height: 1.6;
}

/* ── Code blocks ───────────────────────────────────────────────────────────── */
.stCodeBlock, pre {
    background: #0a0814 !important;
    border: 1px solid #2a2040 !important;
    border-radius: 6px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.74rem !important;
    margin-bottom: 0.4rem !important;
}
/* Limit code block height so it never forces a scroll on the whole page */
.stCodeBlock pre, pre {
    max-height: 180px;
    overflow-y: auto !important;
}
.highlight-line {
    background: #1a1230;
    border-left: 3px solid #a855f7;
    border-radius: 0 6px 6px 0;
    padding: 0.45rem 0.9rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #d4b8ff;
    margin: 0.3rem 0 0.6rem;
}

/* ── Survey task ───────────────────────────────────────────────────────────── */
.expl-option {
    background: #12101e;
    border: 1px solid #2a2040;
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.4rem;
    font-size: 0.88rem;
    line-height: 1.55;
    color: #ccc4e8;
}
.mode-badge {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 0.15rem 0.55rem;
    border-radius: 99px;
    margin-bottom: 0.6rem;
}
.mode-rate { background: #1e2d1e; color: #6ee7b7; }
.mode-pick { background: #1e1e2d; color: #93c5fd; }

/* ── Inputs ────────────────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.4rem 1.5rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    box-shadow: 0 3px 14px rgba(168, 85, 247, 0.22) !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stRadio label, .stCheckbox label { font-size: 0.9rem; color: #ccc4e8 !important; }
.stRadio > div { gap: 0.2rem; }
/* Tighten Streamlit's default widget vertical spacing */
div[data-testid="stVerticalBlock"] > div { gap: 0rem; }
.stTextInput input, .stTextArea textarea {
    background: #14111f !important;
    border: 1px solid #2a2040 !important;
    color: #e8e6f0 !important;
    border-radius: 7px !important;
    font-size: 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.18) !important;
}
.stSelectbox div[data-baseweb="select"] {
    background: #14111f !important;
    border-color: #2a2040 !important;
}

/* ── Consent page ──────────────────────────────────────────────────────────── */
.consent-text {
    font-size: 0.83rem;
    line-height: 1.65;
    color: #a89cc8;
    background: #12101e;
    border: 1px solid #2a2040;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    max-height: 130px;
    overflow-y: auto;
    margin: 0.4rem 0 0.6rem;
}

/* ── Completion page ───────────────────────────────────────────────────────── */
.completion-code-wrapper { text-align: center; margin: 0.5rem 0 0.6rem; }
.completion-code-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    color: #7c6fa0;
    margin-bottom: 0.4rem;
}
.completion-code {
    display: inline-block;
    background: #1a1230;
    border: 2px dashed #7c3aed;
    border-radius: 10px;
    padding: 0.65rem 1.8rem;
    font-family: 'Space Mono', monospace;
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    color: #e0d0ff;
    user-select: all;
    cursor: text;
}
.completion-code-hint { font-size: 0.75rem; color: #6b5f8a; margin-top: 0.3rem; }
.mturk-box {
    background: #0f0c1a;
    border: 1px solid #352a5a;
    border-left: 3px solid #a855f7;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.87rem;
    color: #b8a8d8;
    line-height: 1.65;
    margin: 0.5rem 0;
}
.mturk-box strong { color: #d4b8ff; }
.json-preview {
    background: #0a0814;
    border: 1px solid #2a2040;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    color: #a89cc8;
    max-height: 240px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
}

/* ── Screener page ─────────────────────────────────────────────────────────── */
/* Tighten expander padding */
.streamlit-expanderContent { padding: 0.5rem 0.75rem !important; }
.streamlit-expanderHeader { font-size: 0.88rem !important; padding: 0.4rem 0.75rem !important; }
.attempt-counter {
    display: inline-block;
    background: #2d1f4e;
    color: #c4b5fd;
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 99px;
    margin-left: 0.3rem;
}

/* ── Streamlit native alert boxes — keep compact ───────────────────────────── */
div[data-testid="stAlert"] { padding: 0.55rem 0.85rem !important; font-size: 0.88rem !important; margin-bottom: 0.5rem !important; }
</style>
"""


def inject_styles():
    """Inject the global stylesheet. Call once from main.py."""
    st.markdown(_CSS, unsafe_allow_html=True)