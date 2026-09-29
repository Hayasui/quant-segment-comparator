#!/usr/bin/env python3
"""Audit two groups and compare binary outcomes without third-party packages.

This helper performs descriptive counts, two-sided Fisher exact tests, and
Holm/BH p-value adjustment. It does not fit covariate-adjusted models.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

MISSING_DEFAULT = {"", "97", "98", "99", "NA", "N/A", "null", "None"}


@dataclass
class Outcome:
    variable_id: str
    question: str
    item_label: str
    eligible_expression: str
    positive_value: str
    analysis_family: str
    include_primary: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--group-column", required=True)
    parser.add_argument("--group-a", required=True)
    parser.add_argument("--group-b", required=True)
    parser.add_argument("--population-column")
    parser.add_argument("--population-value")
    parser.add_argument("--id-column")
    parser.add_argument("--missing", default=",".join(sorted(MISSING_DEFAULT)))
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit-output", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_manifest(path: Path) -> list[Outcome]:
    rows = read_csv(path)
    outcomes = []
    for row in rows:
        if row.get("variable_type", "").strip().lower() != "binary":
            continue
        outcomes.append(
            Outcome(
                variable_id=row["variable_id"].strip(),
                question=row.get("question", "").strip(),
                item_label=row.get("item_label", "").strip(),
                eligible_expression=row.get("eligible_expression", "").strip(),
                positive_value=row.get("positive_value", "1").strip() or "1",
                analysis_family=row.get("analysis_family", "primary").strip() or "primary",
                include_primary=row.get("include_primary", "1").strip().lower()
                in {"1", "true", "yes", "y"},
            )
        )
    return outcomes


def eligible(row: dict[str, str], expression: str) -> bool:
    """Support a deliberately small eligibility grammar: blank or column == value."""
    if not expression:
        return True
    if "==" not in expression:
        raise ValueError(f"Unsupported eligible_expression: {expression!r}")
    column, expected = (part.strip() for part in expression.split("==", 1))
    return row.get(column, "") == expected.strip("'\"")


def log_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    row_a = a + b
    col_yes = a + c
    low = max(0, row_a - (total - col_yes))
    high = min(row_a, col_yes)

    def log_probability(x: int) -> float:
        return (
            log_choose(col_yes, x)
            + log_choose(total - col_yes, row_a - x)
            - log_choose(total, row_a)
        )

    observed = log_probability(a)
    probability = sum(
        math.exp(log_probability(x))
        for x in range(low, high + 1)
        if log_probability(x) <= observed + 1e-12
    )
    return min(1.0, probability)


def adjust_holm(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0] * len(values)
    running = 0.0
    count = len(values)
    for rank, index in enumerate(order):
        running = max(running, (count - rank) * values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def adjust_bh(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0] * len(values)
    running = 1.0
    count = len(values)
    for rank, index in reversed(list(enumerate(order, start=1))):
        running = min(running, values[index] * count / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def odds_ratio(a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
    # Haldane-Anscombe correction makes sparse descriptive estimates finite.
    aa, bb, cc, dd = (value + 0.5 for value in (a, b, c, d))
    estimate = aa * dd / (bb * cc)
    standard_error = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    return (
        estimate,
        math.exp(math.log(estimate) - 1.96 * standard_error),
        math.exp(math.log(estimate) + 1.96 * standard_error),
    )


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("No result rows were produced")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rows = read_csv(args.data)
    outcomes = read_manifest(args.manifest)
    if not rows:
        raise ValueError("Input data has no rows")
    if not outcomes:
        raise ValueError("Manifest has no binary outcomes")

    columns = set(rows[0])
    required = {args.group_column, *(item.variable_id for item in outcomes)}
    if args.population_column:
        required.add(args.population_column)
    if args.id_column:
        required.add(args.id_column)
    missing_columns = sorted(required - columns)
    if missing_columns:
        raise KeyError(f"Missing columns: {missing_columns}")

    if args.id_column:
        identifiers = [row[args.id_column] for row in rows]
        duplicates = len(identifiers) - len(set(identifiers))
        if duplicates:
            raise ValueError(f"ID column contains {duplicates} duplicate rows")

    population = rows
    if args.population_column:
        if args.population_value is None:
            raise ValueError("--population-value is required with --population-column")
        population = [
            row for row in rows if row[args.population_column] == args.population_value
        ]

    group_a = [row for row in population if row[args.group_column] == args.group_a]
    group_b = [row for row in population if row[args.group_column] == args.group_b]
    ungrouped = len(population) - len(group_a) - len(group_b)
    missing_values = {value.strip() for value in args.missing.split(",")}

    results: list[dict[str, object]] = []
    for item in outcomes:
        selected: dict[str, list[str]] = {}
        for label, members in (("a", group_a), ("b", group_b)):
            selected[label] = [
                row[item.variable_id]
                for row in members
                if eligible(row, item.eligible_expression)
                and row[item.variable_id] not in missing_values
            ]
        values_a, values_b = selected["a"], selected["b"]
        if not values_a or not values_b:
            continue
        yes_a = sum(value == item.positive_value for value in values_a)
        yes_b = sum(value == item.positive_value for value in values_b)
        no_a, no_b = len(values_a) - yes_a, len(values_b) - yes_b
        p_value = fisher_two_sided(yes_a, no_a, yes_b, no_b)
        estimate, ci_low, ci_high = odds_ratio(yes_a, no_a, yes_b, no_b)
        results.append(
            {
                "variable_id": item.variable_id,
                "question": item.question,
                "item_label": item.item_label,
                "analysis_family": item.analysis_family,
                "n_a": len(values_a),
                "yes_a": yes_a,
                "proportion_a": yes_a / len(values_a),
                "n_b": len(values_b),
                "yes_b": yes_b,
                "proportion_b": yes_b / len(values_b),
                "raw_difference_pp": 100
                * (yes_a / len(values_a) - yes_b / len(values_b)),
                "unadjusted_or": estimate,
                "unadjusted_or_ci_low": ci_low,
                "unadjusted_or_ci_high": ci_high,
                "fisher_p_raw": p_value,
                "holm_p": "",
                "bh_p": "",
                "include_in_body": "",
                "model_status": "descriptive_only",
            }
        )

    for family in sorted({str(row["analysis_family"]) for row in results}):
        indexes = [
            index
            for index, row in enumerate(results)
            if row["analysis_family"] == family
        ]
        raw = [float(results[index]["fisher_p_raw"]) for index in indexes]
        for index, holm, bh in zip(indexes, adjust_holm(raw), adjust_bh(raw)):
            results[index]["holm_p"] = holm
            results[index]["bh_p"] = bh
            results[index]["include_in_body"] = holm < args.alpha

    write_csv(args.output, results)
    audit = {
        "data_rows": len(rows),
        "population_rows": len(population),
        "group_a_rows": len(group_a),
        "group_b_rows": len(group_b),
        "ungrouped_rows": ungrouped,
        "outcomes_in_manifest": len(outcomes),
        "result_rows": len(results),
        "warning": "Results are unadjusted descriptive comparisons; fit the pre-specified covariate model separately.",
    }
    audit_path = args.audit_output or args.output.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
