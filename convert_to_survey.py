"""
convert_to_survey.py
--------------------
Converts an input CSV into survey_data.csv format.

Input CSV columns (in any order):
  - problem_name      : used to locate the problem file (same filename, any extension)
  - line_of_code      : the selected line of source code
  - explanation_1     : first explanation (correct or distractor)
  - explanation_2     : second explanation (correct or distractor)
  - rating            : binary 1/0 or true/false — 1 means explanation_1 is CORRECT

Output CSV columns:
  - problem_statement      : read from the problem file (first block before "---" or entire file)
  - solution_source_code   : read from the problem file (block after "---" separator)
  - selected_line          : line_of_code from input
  - explanation            : the CORRECT explanation (based on rating)
  - distractor_1           : the distractor from the same row
  - distractor_2           : a distractor borrowed from a DIFFERENT row (never empty)

distractor_2 mixing strategy:
  Since each input row only has one distractor, distractor_2 is filled by
  borrowing a distractor from another row using this priority:
    1. Same problem_name, different row  (keeps distractors topically close)
    2. Different problem_name            (cross-problem borrow)
  Borrowing is round-robin so distractors are spread evenly across rows.
  The borrowed distractor is always different from both the correct explanation
  and distractor_1 of the target row.

Problem file format (supported):
  Option A — plain .txt/.md with a separator line "---":
      <problem statement>
      ---
      <source code>

  Option B — .py/.java/.js/etc. with problem statement in a top docstring/comment:
      The entire file is treated as source_code, and the problem statement
      is extracted from the leading block comment or docstring.

  If no separator is found, the whole file content is used as source_code
  and problem_statement will be left empty with a warning.

Usage:
  python convert_to_survey.py --input data.csv --problems ./problems --output survey_data.csv

Arguments:
  --input     Path to the input CSV file (required)
  --problems  Directory containing problem files (default: same directory as input CSV)
  --output    Path for the output CSV (default: survey_data.csv)
  --ext       File extension to look for, e.g. .txt .py .java (default: auto-detect)
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEPARATOR_PATTERN = re.compile(r"^-{3,}$", re.MULTILINE)


def find_problem_file(problem_name: str, problems_dir: Path, preferred_ext: str = None) -> Path | None:
    """
    Locate the problem file by name.  Tries:
      1. Exact filename if problem_name already has an extension.
      2. preferred_ext if supplied.
      3. Common extensions in order.
    """
    # If the name already includes an extension
    direct = problems_dir / problem_name
    if direct.exists():
        return direct

    candidates_ext = []
    if preferred_ext:
        candidates_ext.append(preferred_ext if preferred_ext.startswith(".") else f".{preferred_ext}")

    candidates_ext += [".txt", ".md", ".py", ".java", ".js", ".ts", ".cpp", ".c", ".cs", ".rb", ".go"]

    for ext in candidates_ext:
        p = problems_dir / f"{problem_name}{ext}"
        if p.exists():
            return p

    # Fallback: glob for any file whose stem matches
    matches = list(problems_dir.glob(f"{problem_name}.*"))
    if matches:
        return matches[0]

    return None


def parse_problem_file(filepath: Path) -> tuple[str, str]:
    """
    Returns (problem_statement, source_code) from a problem file.

    Splitting strategy:
      1. Look for a "---" separator line → above is statement, below is code.
      2. For code files (.py .java etc.), extract leading docstring/block comment
         as the statement and the rest as source_code.
      3. Fallback: entire content → source_code, statement = "".
    """
    content = filepath.read_text(encoding="utf-8", errors="replace").strip()

    # Strategy 1: explicit separator
    parts = SEPARATOR_PATTERN.split(content, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    suffix = filepath.suffix.lower()

    # Strategy 2a: Python — leading triple-quoted docstring
    if suffix == ".py":
        m = re.match(r'^(?:\'\'\'|""")(.*?)(?:\'\'\'|""")', content, re.DOTALL)
        if m:
            statement = m.group(1).strip()
            source_code = content[m.end():].strip()
            return statement, source_code

    # Strategy 2b: C-style block comment /* ... */
    if suffix in {".java", ".js", ".ts", ".cpp", ".c", ".cs", ".go"}:
        m = re.match(r"^/\*(.*?)\*/", content, re.DOTALL)
        if m:
            statement = re.sub(r"^\s*\*\s?", "", m.group(1), flags=re.MULTILINE).strip()
            source_code = content[m.end():].strip()
            return statement, source_code

    # Strategy 3: plain text / markdown — whole file is the statement (no code)
    if suffix in {".txt", ".md"}:
        return content, ""

    # Fallback
    return "", content


def resolve_correct_distractor(explanation_1: str, explanation_2: str, rating: str):
    """
    Returns (correct_explanation, distractor_1).

    rating == "1" / "true" / "yes"  → explanation_1 is correct
    rating == "0" / "false" / "no"  → explanation_2 is correct
    """
    truthy = {"1", "true", "yes", "correct"}
    is_exp1_correct = rating.strip().lower() in truthy

    if is_exp1_correct:
        return explanation_1, explanation_2
    else:
        return explanation_2, explanation_1


def assign_distractors(output_rows: list[dict], problem_names: list[str]) -> None:
    """
    Assigns distractor_1 and distractor_2 in-place for every row.

    Both distractors come exclusively from rows sharing the same problem_name.
    No cross-problem borrowing ever occurs.

    Strategy
    --------
    For each problem_name group, collect the pool of all wrong explanations
    (one per row).  For each row, keep its own wrong explanation as distractor_1
    and pick one more from the same pool (round-robin, offset by position) as
    distractor_2, skipping any text that matches the correct explanation or
    distractor_1.

    Fallback: if the problem appears only once (pool size = 1), distractor_2
    will repeat distractor_1 and a warning is printed.
    """
    from collections import defaultdict

    groups: dict[str, list[int]] = defaultdict(list)
    for i, name in enumerate(problem_names):
        groups[name].append(i)

    for name, indices in groups.items():
        pool = [output_rows[i]["distractor_1"] for i in indices]

        for pos, i in enumerate(indices):
            row      = output_rows[i]
            own_d1   = row["distractor_1"]
            forbidden = {row["explanation"], own_d1}
            d2 = None

            for offset in range(1, len(pool) + 1):
                candidate = pool[(pos + offset) % len(pool)]
                if candidate not in forbidden:
                    d2 = candidate
                    break

            if d2 is None:
                d2 = own_d1
                print(f"[WARN] '{name}': only one distinct distractor available — "
                      f"distractor_2 repeats distractor_1 for input row {i + 2}.")

            row["distractor_2"] = d2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Convert input CSV + problem files → survey_data.csv")
    parser.add_argument("--input",    required=True,          help="Path to input CSV")
    parser.add_argument("--problems", default=None,           help="Directory containing problem files (default: input CSV directory)")
    parser.add_argument("--output",   default="survey_data.csv", help="Output CSV path")
    parser.add_argument("--ext",      default=None,           help="Preferred file extension for problem files (e.g. .txt)")
    args = parser.parse_args()

    input_path    = Path(args.input).resolve()
    problems_dir  = Path(args.problems).resolve() if args.problems else input_path.parent
    output_path   = Path(args.output).resolve()

    if not input_path.exists():
        sys.exit(f"[ERROR] Input file not found: {input_path}")
    if not problems_dir.exists():
        sys.exit(f"[ERROR] Problems directory not found: {problems_dir}")

    output_rows  = []
    problem_names = []
    warnings     = []

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Normalise column names: strip whitespace, lowercase
        if reader.fieldnames is None:
            sys.exit("[ERROR] Input CSV appears to be empty.")

        fieldnames = [col.strip().lower().replace(" ", "_") for col in reader.fieldnames]
        reader.fieldnames = fieldnames

        required = {"problem_name", "line_of_code", "explanation_1", "explanation_2", "rating"}
        missing  = required - set(fieldnames)
        if missing:
            sys.exit(f"[ERROR] Input CSV is missing required columns: {', '.join(sorted(missing))}\n"
                     f"  Found columns: {', '.join(fieldnames)}")

        for row_num, row in enumerate(reader, start=2):
            # Normalise keys
            row = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}

            problem_name  = row["problem_name"]
            line_of_code  = row["line_of_code"]
            explanation_1 = row["explanation_1"]
            explanation_2 = row["explanation_2"]
            rating        = row["rating"]

            # --- Locate & parse problem file ---
            problem_file = find_problem_file(problem_name, problems_dir, args.ext)
            if problem_file is None:
                warnings.append(f"  Row {row_num}: Problem file not found for '{problem_name}' in {problems_dir}")
                problem_statement = ""
                source_code       = ""
            else:
                problem_statement, source_code = parse_problem_file(problem_file)

            # --- Resolve correct vs distractor ---
            correct, distractor_1 = resolve_correct_distractor(
                explanation_1, explanation_2, rating
            )

            output_rows.append({
                "problem_statement":    problem_statement,
                "solution_source_code": source_code,
                "selected_line":        line_of_code,
                "explanation":          correct,
                "distractor_1":         distractor_1,
                "distractor_2":         "",   # filled below
            })
            problem_names.append(problem_name)

    # --- Assign distractors (same-problem only, no cross-pollination) ---
    assign_distractors(output_rows, problem_names)

    # --- Write output ---
    out_fieldnames = ["problem_statement", "solution_source_code", "selected_line",
                      "explanation", "distractor_1", "distractor_2"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Wrote {len(output_rows)} row(s) to: {output_path}")

    if warnings:
        print("\n[WARNINGS]")
        for w in warnings:
            print(w)
        print("\nFor missing problem files, those rows will have empty problem_statement and source_code.")
        print("Place problem files in the --problems directory with the same name as the problem_name column.")


if __name__ == "__main__":
    main()