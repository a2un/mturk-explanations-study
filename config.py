# =============================================================================
# config.py
# App-wide constants, Streamlit page configuration, screener question bank,
# and data file paths. Import this module first in main.py.
# =============================================================================

import streamlit as st

# ── File paths ────────────────────────────────────────────────────────────────
DATA_FILE     = "survey_data.csv"
RESPONSES_FILE = "responses.json"
ATTEMPTS_FILE  = "screener_attempts.json"

# ── Screener settings ─────────────────────────────────────────────────────────
MAX_ATTEMPTS = 2          # maximum screener attempts per Worker ID
PASS_SCORE   = 3          # number of correct answers required to pass

# ── Page index constants ──────────────────────────────────────────────────────
PAGE_SCREENER = 0
PAGE_CONSENT  = 1
PAGE_SURVEY   = 2
PAGE_COMPLETE = 3

# ── Intermediate Java MCQ bank ────────────────────────────────────────────────
# Each entry: id (str), question (markdown str), correct (str), distractors (list[str])
# Options are shuffled at runtime in session state (see main.py init).
JAVA_SCREENER_QUESTIONS = [
    {
        "id": "q_interface",
        "question": (
            "Consider the following Java code:\n\n"
            "```java\n"
            "interface Drawable {\n"
            "    void draw();\n"
            "    default void describe() {\n"
            "        System.out.println(\"I am drawable\");\n"
            "    }\n"
            "}\n"
            "\n"
            "class Circle implements Drawable {\n"
            "    public void draw() {\n"
            "        System.out.println(\"Drawing circle\");\n"
            "    }\n"
            "}\n"
            "```\n\n"
            "Which statement about this code is **correct**?"
        ),
        "correct": "Circle must implement draw() but inherits describe() from the interface",
        "distractors": [
            "Circle must override both draw() and describe() or the code will not compile",
            "Interfaces in Java cannot have method bodies, so this code is invalid",
            "describe() will throw an AbstractMethodError at runtime if not overridden",
        ],
    },
    {
        "id": "q_generics",
        "question": (
            "What is the output of the following Java snippet?\n\n"
            "```java\n"
            "import java.util.*;\n\n"
            "List<Integer> nums = new ArrayList<>(Arrays.asList(3, 1, 4, 1, 5));\n"
            "Collections.sort(nums);\n"
            "System.out.println(nums.get(0) + \" \" + nums.get(nums.size() - 1));\n"
            "```"
        ),
        "correct": "1 5",
        "distractors": [
            "3 5",
            "1 4",
            "The code throws an UnsupportedOperationException",
        ],
    },
    {
        "id": "q_exception",
        "question": (
            "Examine this Java method:\n\n"
            "```java\n"
            "public static int divide(int a, int b) {\n"
            "    try {\n"
            "        return a / b;\n"
            "    } catch (ArithmeticException e) {\n"
            "        return -1;\n"
            "    } finally {\n"
            "        System.out.println(\"done\");\n"
            "    }\n"
            "}\n"
            "```\n\n"
            "What is printed and returned when `divide(10, 0)` is called?"
        ),
        "correct": "Prints \"done\", returns -1",
        "distractors": [
            "Prints nothing, throws ArithmeticException to the caller",
            "Prints \"done\", throws ArithmeticException to the caller",
            "Prints \"done\", returns 0",
        ],
    },
]


def apply_page_config():
    """Call once at the top of main.py to configure the Streamlit page."""
    st.set_page_config(
        page_title="Code Comprehension Survey",
        page_icon="🔬",
        layout="centered",
        initial_sidebar_state="collapsed",
    )