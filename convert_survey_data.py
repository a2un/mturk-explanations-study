#!/usr/bin/env python3
"""
convert_survey_data.py — Convert long-form explanation data into the
grouped JSON format expected by the survey app.

INPUTS
------
1. A CSV file (long form) with columns:
       problem_key, line_number, explanation

   - problem_key:  matches a filename in the problems folder (e.g. "two_sum"
                    matches "two_sum.txt").
   - line_number:  1-based index into the SOURCE CODE lines of that problem.
   - explanation:  a student's explanation of the line.

   Multiple rows may share the same (problem_key, line_number) — each row is
   a different student explanation for that line.

2. A folder of problem text files.  Each file is named <problem_key>.txt and
   has the structure:

       <problem statement text>
       (may span multiple lines)
       ---
       <source code>
       (may span multiple lines)

   Everything before the first "---" line is the problem statement.
   Everything after is the source code.

OUTPUT
------
A JSON file (default: ./data/survey_data.json) with structure:

[
  {
    "problem_id": 0,
    "problem_key": "two_sum",
    "problem_statement": "Given an array of integers ...",
    "solution_source_code": "def two_sum(nums, target):\\n  ...",
    "selected_line": "if complement in seen:",
    "line_number": 4,
    "explanations": [
      "Student explanation 1 ...",
      "Student explanation 2 ...",
      ...
    ]
  },
  ...
]

Usage:
    python convert_survey_data.py
    python convert_survey_data.py --csv explanations.csv --problems ./problems --out ./data/survey_data.json
"""

import argparse
import csv
import json
import os
import sys
from collections import OrderedDict

DEFAULT_CSV      = os.path.join(".", "data", "explanations.csv")
DEFAULT_PROBLEMS = os.path.join(".", "data", "problems")
DEFAULT_OUTPUT   = os.path.join(".", "data", "survey_data.json")
DELIMITER        = "---"


# ── Parse a problem file ─────────────────────────────────────────────────────

def parse_problem_file(filepath):
    """Read a problem file and split on the '---' delimiter.

    Returns (problem_statement: str, source_code: str, code_lines: list[str]).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split(f"\n{DELIMITER}\n", maxsplit=1)
    if len(parts) != 2:
        # Try alternate split (delimiter might be at very start or have \r\n)
        parts = content.split(DELIMITER, maxsplit=1)
    if len(parts) != 2:
        print(f"  ⚠ Could not find '{DELIMITER}' delimiter in {filepath}")
        return None, None, None

    problem_statement = parts[0].strip()
    source_code = parts[1].strip()
    code_lines = source_code.splitlines()

    return problem_statement, source_code, code_lines


def load_all_problems(problems_dir):
    """Load all .txt problem files from a directory.

    Returns dict: problem_key → {problem_statement, source_code, code_lines}.
    """
    problems = {}
    if not os.path.isdir(problems_dir):
        print(f"Error: Problems directory not found — {problems_dir}")
        sys.exit(1)

    for filename in sorted(os.listdir(problems_dir)):
        if not filename.endswith(".txt"):
            continue
        key = filename[:-4]  # strip .txt
        filepath = os.path.join(problems_dir, filename)
        stmt, code, lines = parse_problem_file(filepath)
        if stmt is None:
            continue
        problems[key] = {
            "problem_statement": stmt,
            "source_code": code,
            "code_lines": lines,
        }

    return problems


# ── Main conversion ──────────────────────────────────────────────────────────

def convert(csv_path, problems_dir, output_path):
    # ── Load problems ──
    problems = load_all_problems(problems_dir)
    print(f"Loaded {len(problems)} problem file(s) from {problems_dir}")
    if not problems:
        print("Error: No problem files found. Aborting.")
        sys.exit(1)

    # ── Read CSV ──
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        required = {"problem_key", "line_number", "explanation"}
        missing = required - columns
        if missing:
            print(f"Error: CSV is missing required columns: {missing}")
            print(f"Found columns: {columns}")
            sys.exit(1)
        rows = list(reader)

    print(f"Read {len(rows)} rows from {csv_path}")

    # ── Group by (problem_key, line_number) ──
    #    Each group becomes one survey item with multiple explanations.
    groups = OrderedDict()
    skipped = 0

    for row in rows:
        pkey = row["problem_key"].strip()
        try:
            line_num = int(row["line_number"].strip())
        except ValueError:
            print(f"  ⚠ Skipping row with invalid line_number: {row['line_number']}")
            skipped += 1
            continue

        explanation = row["explanation"].strip()
        if not explanation:
            skipped += 1
            continue

        # Resolve problem
        if pkey not in problems:
            print(f"  ⚠ Problem key '{pkey}' not found in {problems_dir}/ — skipping row.")
            skipped += 1
            continue

        prob = problems[pkey]
        code_lines = prob["code_lines"]

        # Validate line number (1-based)
        if line_num < 1 or line_num > len(code_lines):
            print(f"  ⚠ Line {line_num} out of range for '{pkey}' "
                  f"(has {len(code_lines)} lines) — skipping row.")
            skipped += 1
            continue

        selected_line = code_lines[line_num - 1]  # convert to 0-based

        group_key = (pkey, line_num)
        if group_key not in groups:
            groups[group_key] = {
                "problem_key":          pkey,
                "problem_statement":    prob["problem_statement"],
                "solution_source_code": prob["source_code"],
                "selected_line":        selected_line,
                "line_number":          line_num,
                "explanations":         [],
            }

        if explanation not in groups[group_key]["explanations"]:
            groups[group_key]["explanations"].append(explanation)

    if skipped:
        print(f"  Skipped {skipped} row(s) due to errors.")

    # ── Assign problem IDs and build output ──
    output = []
    for idx, group in enumerate(groups.values()):
        group["problem_id"] = idx
        output.append(group)

    # ── Stats ──
    total_explanations = sum(len(g["explanations"]) for g in output)
    expl_counts = [len(g["explanations"]) for g in output]
    unique_problems = len(set(g["problem_key"] for g in output))

    print(f"\nGrouped into {len(output)} unique (problem, line) combinations")
    print(f"  Across {unique_problems} problem(s)")
    print(f"  Total student explanations: {total_explanations}")
    if expl_counts:
        print(f"  Explanations per line:  min={min(expl_counts)}, "
              f"max={max(expl_counts)}, avg={total_explanations/len(output):.1f}")

    # ── Write JSON ──
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {output_path}")
    print("Done.")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert long-form explanations CSV + problem files into survey JSON."
    )
    parser.add_argument(
        "--csv", default=DEFAULT_CSV,
        help=f"Path to the explanations CSV (default: {DEFAULT_CSV})"
    )
    parser.add_argument(
        "--problems", default=DEFAULT_PROBLEMS,
        help=f"Directory containing problem .txt files (default: {DEFAULT_PROBLEMS})"
    )
    parser.add_argument(
        "--out", default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()
    convert(args.csv, args.problems, args.out)


if __name__ == "__main__":
    main()