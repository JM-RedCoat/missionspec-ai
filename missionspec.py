"""MissionSpec AI: generate implementation scaffolds, tests, and checklists from a plain-text requirement."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SubRequirement:
    """Represents a testable slice of the original requirement."""

    identifier: str
    title: str
    description: str
    acceptance_criteria: str


def _normalize_text(requirement_text: str) -> str:
    """Collapse whitespace so parsing behaves predictably."""
    return re.sub(r"\s+", " ", requirement_text.strip())


def _split_into_candidate_clauses(requirement_text: str) -> list[str]:
    """Break the requirement into sentence-like or list-like clauses."""
    normalized = _normalize_text(requirement_text)
    if not normalized:
        return []

    numbered_parts = re.split(r"(?:^|\s)(?:\d+[\.\)]|[a-zA-Z][\.\)])\s+", normalized)
    if len([part for part in numbered_parts if part.strip()]) > 1:
        clauses = [part.strip(" ;,.") for part in numbered_parts if part.strip()]
    else:
        clauses = re.split(r"[;]|(?:\.\s+)", normalized)
        clauses = [part.strip(" ;,.") for part in clauses if part.strip()]

    if len(clauses) <= 1:
        leading_subject_match = re.match(r"^(.*?\bshall\b)\s+(.*)$", normalized, flags=re.IGNORECASE)
        lead_in = ""
        body = normalized
        if leading_subject_match:
            lead_in = leading_subject_match.group(1).strip()
            body = leading_subject_match.group(2).strip()

        raw_clauses = re.split(r",\s+(?=(?:log|record|store|raise|provide|support|monitor|validate|report|transmit|maintain)\b)", body, flags=re.IGNORECASE)
        clauses = []

        for index, clause in enumerate(raw_clauses):
            cleaned = clause.strip(" ;,.")
            if not cleaned:
                continue
            if lead_in and index == 0:
                cleaned = f"{lead_in} {cleaned}"
            clauses.append(cleaned)

    return clauses or [normalized]


def _make_acceptance_criteria(clause: str) -> str:
    """Convert a clause into a compact verification statement."""
    clause = clause[0].upper() + clause[1:] if clause else clause
    return f"Verify that the system satisfies: {clause}."


def _make_function_name(item: dict[str, str]) -> str:
    """Create a stable Python function name for a sub-requirement."""
    sanitized = re.sub(r"[^a-z0-9]+", "_", item["title"].lower()).strip("_")
    return f"implement_{sanitized or item['id'].lower().replace('-', '_')}"


def parse_requirements(requirement_text: str) -> list[dict[str, str]]:
    """
    Parse a technical requirement into 3-5 testable sub-requirements.

    Returns a list of dictionaries so the output is easy to serialize and inspect.
    """
    normalized = _normalize_text(requirement_text)
    if not normalized:
        raise ValueError("Requirement text must not be empty.")

    clauses = _split_into_candidate_clauses(normalized)
    subrequirements: list[SubRequirement] = []

    next_identifier = 1

    for clause in clauses:
        cleaned = clause.strip()
        if len(cleaned) < 20:
            continue

        title_words = cleaned.split()[:8]
        title = " ".join(word.strip(",.") for word in title_words).capitalize()
        subrequirements.append(
            SubRequirement(
                identifier=f"SR-{next_identifier}",
                title=title,
                description=cleaned,
                acceptance_criteria=_make_acceptance_criteria(cleaned),
            )
        )
        next_identifier += 1

    if not subrequirements:
        subrequirements.append(
            SubRequirement(
                identifier="SR-1",
                title="Primary system requirement",
                description=normalized,
                acceptance_criteria=_make_acceptance_criteria(normalized),
            )
        )

    while len(subrequirements) < 3:
        next_index = len(subrequirements) + 1
        basis = subrequirements[0].description
        subrequirements.append(
            SubRequirement(
                identifier=f"SR-{next_index}",
                title=f"Derived verification objective {next_index}",
                description=f"Derived objective from the original requirement: {basis}",
                acceptance_criteria=f"Verify the implementation provides measurable evidence for objective {next_index}.",
            )
        )

    subrequirements = subrequirements[:5]

    return [
        {
            "id": item.identifier,
            "title": item.title,
            "description": item.description,
            "acceptance_criteria": item.acceptance_criteria,
        }
        for item in subrequirements
    ]


def generate_scaffold(subrequirements: list[dict[str, str]]) -> str:
    """Generate a Python scaffold with one function stub per sub-requirement."""
    function_blocks: list[str] = []

    for item in subrequirements:
        func_name = _make_function_name(item)
        block = f'''
def {func_name}(system_state: dict[str, Any]) -> dict[str, Any]:
    """
    {item["id"]}: {item["description"]}
    Acceptance criteria: {item["acceptance_criteria"]}
    """
    return {{
        "requirement_id": "{item["id"]}",
        "status": "not_implemented",
        "details": "{item["description"]}",
        "system_state": system_state,
    }}
'''.strip("\n")
        function_blocks.append(block)

    scaffold = """
from __future__ import annotations

from typing import Any


class MissionSpecGeneratedModule:
    \"\"\"Container for generated implementation stubs.\"\"\"

    def __init__(self) -> None:
        self.name = "MissionSpecGeneratedModule"

"""
    return scaffold + "\n\n" + "\n\n".join(function_blocks) + "\n"


def generate_tests(subrequirements: list[dict[str, str]]) -> str:
    """Generate pytest tests that validate each scaffolded function shape."""
    import_block = "from generated_scaffold import " + ", ".join(_make_function_name(item) for item in subrequirements)
    test_blocks: list[str] = [
        "from typing import Any",
        "",
        import_block,
        "",
    ]

    for item in subrequirements:
        func_name = _make_function_name(item)
        test_name = f"test_{func_name}_returns_requirement_metadata"
        test_body = f'''
def {test_name}() -> None:
    system_state: dict[str, Any] = {{"mode": "test"}}
    result = {func_name}(system_state)

    assert result["requirement_id"] == "{item["id"]}"
    assert result["status"] in {{"not_implemented", "implemented", "verified"}}
    assert "{item["description"]}" in result["details"]
'''.strip("\n")
        test_blocks.append(test_body)
        test_blocks.append("")

    return "\n".join(test_blocks).rstrip() + "\n"


def generate_checklist(subrequirements: list[dict[str, str]]) -> str:
    """Generate a markdown compliance checklist."""
    lines = [
        "# MissionSpec AI Compliance Checklist",
        "",
        "## Sub-requirements",
    ]

    for item in subrequirements:
        lines.extend(
            [
                f"- [ ] {item['id']}: {item['title']}",
                f"  Evidence target: {item['acceptance_criteria']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Verification Gates",
            "- [ ] Code scaffold reviewed for each sub-requirement",
            "- [ ] Pytest coverage generated for each sub-requirement",
            "- [ ] Requirement-to-test traceability confirmed",
        ]
    )

    return "\n".join(lines) + "\n"


def _verify_outputs(subrequirements: list[dict[str, str]], scaffold: str, tests: str, checklist: str) -> list[str]:
    """Perform lightweight self-checks for the Plan -> Act -> Verify loop."""
    findings: list[str] = []

    if not 3 <= len(subrequirements) <= 5:
        findings.append("Sub-requirement count is outside the target range of 3-5.")

    for item in subrequirements:
        if item["id"] not in scaffold:
            findings.append(f"Scaffold is missing requirement marker {item['id']}.")
        if item["id"] not in tests:
            findings.append(f"Tests are missing requirement marker {item['id']}.")
        if item["id"] not in checklist:
            findings.append(f"Checklist is missing requirement marker {item['id']}.")

    return findings


def _repair_scaffold(subrequirements: list[dict[str, str]], scaffold: str, test_output: str) -> tuple[str, str]:
    """Attempt a deterministic scaffold repair based on pytest feedback."""
    if "SyntaxError" in test_output or "IndentationError" in test_output:
        return generate_scaffold(subrequirements), "Regenerated scaffold to address a syntax-level failure."

    if "ImportError" in test_output or "cannot import name" in test_output:
        return generate_scaffold(subrequirements), "Regenerated scaffold to restore expected function exports."

    if "KeyError" in test_output or "AssertionError" in test_output:
        repaired = generate_scaffold(subrequirements)
        return repaired, "Regenerated scaffold to restore expected requirement metadata contract."

    return scaffold, "No automated scaffold fix matched the failure output."


def _is_environment_failure(test_output: str) -> bool:
    """Detect failures that are caused by the local Python environment instead of the scaffold."""
    environment_markers = [
        "No module named pytest",
        "ModuleNotFoundError: No module named 'pytest'",
        "pytest is not recognized",
    ]
    return any(marker in test_output for marker in environment_markers)


def _execute_pytest(working_dir: Path) -> tuple[bool, str]:
    """Run pytest against the generated scaffold and tests."""
    result = subprocess.run(
        ["python", "-m", "pytest", "test_generated_scaffold.py", "-q"],
        cwd=working_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    combined_output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, combined_output or "Pytest produced no output."


def _run_verification_loop(
    subrequirements: list[dict[str, str]],
    scaffold: str,
    tests: str,
    checklist: str,
    output_dir: Path | None,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Run generated pytest tests, repair the scaffold on failure, and log each attempt."""
    attempts: list[dict[str, Any]] = []
    current_scaffold = scaffold

    with tempfile.TemporaryDirectory(prefix="missionspec_verify_") as temp_dir:
        verify_dir = Path(temp_dir)

        for attempt_number in range(1, max_attempts + 1):
            (verify_dir / "generated_scaffold.py").write_text(current_scaffold, encoding="utf-8")
            (verify_dir / "test_generated_scaffold.py").write_text(tests, encoding="utf-8")
            (verify_dir / "compliance_checklist.md").write_text(checklist, encoding="utf-8")

            passed, pytest_output = _execute_pytest(verify_dir)
            timestamp = datetime.now(timezone.utc).isoformat()
            repair_note = "No fix required."
            environment_failure = _is_environment_failure(pytest_output)

            if not passed and not environment_failure and attempt_number < max_attempts:
                current_scaffold, repair_note = _repair_scaffold(subrequirements, current_scaffold, pytest_output)
            elif environment_failure:
                repair_note = "Verification blocked by the local environment; scaffold repair skipped."

            attempts.append(
                {
                    "attempt": attempt_number,
                    "timestamp": timestamp,
                    "passed": passed,
                    "result": "PASS" if passed else "FAIL",
                    "repair_note": repair_note,
                    "environment_failure": environment_failure,
                    "pytest_output": pytest_output,
                }
            )

            if passed or environment_failure:
                break

    verification_log = {
        "passed": attempts[-1]["passed"] if attempts else False,
        "environment_blocked": attempts[-1]["environment_failure"] if attempts else False,
        "attempt_count": len(attempts),
        "attempts": attempts,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "generated_scaffold.py").write_text(current_scaffold, encoding="utf-8")
        (output_dir / "test_generated_scaffold.py").write_text(tests, encoding="utf-8")
        (output_dir / "compliance_checklist.md").write_text(checklist, encoding="utf-8")
        (output_dir / "verification_log.json").write_text(json.dumps(verification_log, indent=2), encoding="utf-8")

    return {
        "scaffold": current_scaffold,
        "verification_run": verification_log,
    }


def _build_artifacts(requirement_text: str, verify: bool = False, output_dir: Path | None = None) -> dict[str, Any]:
    """Run the Plan -> Act -> Verify loop and return all generated artifacts."""
    plan = {
        "goal": "Transform a free-text technical requirement into implementation and verification assets.",
        "steps": [
            "Parse the requirement into 3-5 testable sub-requirements.",
            "Generate a Python scaffold aligned to each sub-requirement.",
            "Generate pytest unit tests for traceable verification.",
            "Generate a markdown compliance checklist.",
        ],
    }

    if verify:
        plan["steps"].append("Run generated pytest verification, repair scaffold failures, and retry up to 3 attempts.")

    subrequirements = parse_requirements(requirement_text)
    scaffold = generate_scaffold(subrequirements)
    tests = generate_tests(subrequirements)
    checklist = generate_checklist(subrequirements)
    verification_findings = _verify_outputs(subrequirements, scaffold, tests, checklist)

    verification_run = None
    if verify:
        verification_results = _run_verification_loop(subrequirements, scaffold, tests, checklist, output_dir)
        scaffold = verification_results["scaffold"]
        verification_run = verification_results["verification_run"]
        if verification_run["environment_blocked"]:
            verification_findings.append("Generated pytest verification could not run because pytest is unavailable in the local environment.")
        elif not verification_run["passed"]:
            verification_findings.append("Generated pytest verification did not pass within 3 attempts.")

    return {
        "plan": plan,
        "subrequirements": subrequirements,
        "scaffold": scaffold,
        "tests": tests,
        "checklist": checklist,
        "verification": {
            "passed": not verification_findings,
            "findings": verification_findings,
        },
        "verification_run": verification_run,
    }


def _resolve_requirement_text(requirement: str | None, requirement_file: Path | None) -> str:
    """Resolve requirement text from CLI input."""
    if requirement_file is not None:
        file_text = requirement_file.read_text(encoding="utf-8-sig").strip()
        if not file_text:
            raise ValueError(f"Requirement file is empty: {requirement_file}")
        return file_text

    if requirement is not None and requirement.strip():
        return requirement.strip()

    raise ValueError("Provide a requirement as text or with --file.")


def _write_outputs(output_dir: Path, artifacts: dict[str, Any]) -> None:
    """Persist generated artifacts when the user supplies an output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "subrequirements.json").write_text(
        json.dumps(artifacts["subrequirements"], indent=2),
        encoding="utf-8",
    )
    (output_dir / "generated_scaffold.py").write_text(artifacts["scaffold"], encoding="utf-8")
    (output_dir / "test_generated_scaffold.py").write_text(artifacts["tests"], encoding="utf-8")
    (output_dir / "compliance_checklist.md").write_text(artifacts["checklist"], encoding="utf-8")
    if artifacts.get("verification_run") is not None:
        (output_dir / "verification_log.json").write_text(
            json.dumps(artifacts["verification_run"], indent=2),
            encoding="utf-8",
        )


def _format_verification_run(verification_run: dict[str, Any] | None) -> str:
    """Render verification attempt history for the CLI."""
    if verification_run is None:
        return "Verification execution not requested."

    lines = [
        f"Verification attempts: {verification_run['attempt_count']}",
    ]
    for attempt in verification_run["attempts"]:
        lines.append(
            f"- Attempt {attempt['attempt']} at {attempt['timestamp']}: {attempt['result']} ({attempt['repair_note']})"
        )
    return "\n".join(lines)


def _format_console_output(artifacts: dict[str, Any]) -> str:
    """Prepare a readable CLI report."""
    plan_lines = "\n".join(f"- {step}" for step in artifacts["plan"]["steps"])
    verification = artifacts["verification"]
    verification_line = "PASS" if verification["passed"] else "FAIL"
    findings = "\n".join(f"- {finding}" for finding in verification["findings"]) or "- No verification issues detected."

    return (
        "MissionSpec AI\n"
        "==============\n\n"
        "PLAN\n"
        f"{artifacts['plan']['goal']}\n"
        f"{plan_lines}\n\n"
        "ACT\n"
        f"Parsed {len(artifacts['subrequirements'])} sub-requirements and generated scaffold, tests, and checklist artifacts.\n\n"
        "VERIFY\n"
        f"Status: {verification_line}\n"
        f"{findings}\n\n"
        "VERIFICATION RUN\n"
        f"{_format_verification_run(artifacts.get('verification_run'))}\n\n"
        "SUB-REQUIREMENTS\n"
        f"{json.dumps(artifacts['subrequirements'], indent=2)}\n\n"
        "GENERATED SCAFFOLD\n"
        f"{artifacts['scaffold']}\n"
        "GENERATED TESTS\n"
        f"{artifacts['tests']}\n"
        "COMPLIANCE CHECKLIST\n"
        f"{artifacts['checklist']}"
    )


def main() -> None:
    """CLI entry point for MissionSpec AI."""
    parser = argparse.ArgumentParser(
        description="MissionSpec AI: convert a plain-text technical requirement into code, tests, and a checklist."
    )
    parser.add_argument(
        "requirement",
        nargs="?",
        help="Technical system requirement expressed in plain text.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        dest="requirement_file",
        help="Path to a .txt file containing the technical system requirement.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory to write generated artifacts.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run generated pytest tests, retry scaffold fixes up to 3 times, and log each attempt.",
    )
    args = parser.parse_args()

    requirement_text = _resolve_requirement_text(args.requirement, args.requirement_file)
    artifacts = _build_artifacts(requirement_text, verify=args.verify, output_dir=args.output_dir)

    if args.output_dir:
        _write_outputs(args.output_dir, artifacts)

    print(_format_console_output(artifacts))


if __name__ == "__main__":
    main()
