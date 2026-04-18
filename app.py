"""Flask web UI for MissionSpec AI."""

from __future__ import annotations

import json

from flask import Flask, Response, render_template_string, request

from missionspec import generate_checklist, generate_scaffold, generate_tests, parse_requirements


app = Flask(__name__)

DEFAULT_REQUIREMENT = (
    "The navigation system shall maintain positional accuracy within 10 meters CEP "
    "under GPS-denied conditions at sea state 4."
)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MissionSpec AI</title>
    <style>
        :root {
            --bg: #06162b;
            --panel: #0d2342;
            --panel-border: #21456d;
            --text: #f7fbff;
            --muted: #b7c9dc;
            --accent: #ffffff;
            --button: #12345b;
            --button-hover: #1a4778;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(180deg, #04101f 0%, var(--bg) 100%);
            color: var(--text);
        }

        .page {
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px 20px 48px;
        }

        .hero {
            margin-bottom: 24px;
        }

        .hero h1 {
            margin: 0 0 10px;
            font-size: 2.4rem;
            letter-spacing: 0.02em;
        }

        .hero p {
            margin: 0;
            color: var(--muted);
            max-width: 760px;
            line-height: 1.5;
        }

        .form-card,
        .panel {
            background: rgba(13, 35, 66, 0.92);
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.24);
        }

        .form-card {
            padding: 20px;
            margin-bottom: 24px;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 10px;
        }

        textarea {
            width: 100%;
            min-height: 180px;
            resize: vertical;
            border: 1px solid #31557f;
            border-radius: 12px;
            padding: 14px 16px;
            background: #08172d;
            color: var(--text);
            font: inherit;
            line-height: 1.5;
        }

        textarea::placeholder {
            color: #88a2bd;
        }

        .actions {
            display: flex;
            gap: 12px;
            align-items: center;
            margin-top: 14px;
        }

        button {
            border: 0;
            border-radius: 999px;
            padding: 12px 22px;
            font: inherit;
            font-weight: 700;
            color: #06162b;
            background: var(--accent);
            cursor: pointer;
            transition: background 0.2s ease, transform 0.2s ease;
        }

        button:hover {
            background: #dde9f5;
            transform: translateY(-1px);
        }

        .helper {
            color: var(--muted);
            font-size: 0.95rem;
        }

        .error {
            margin-top: 14px;
            padding: 12px 14px;
            border-radius: 12px;
            background: rgba(140, 24, 43, 0.28);
            border: 1px solid rgba(255, 133, 160, 0.35);
            color: #ffd9e2;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
        }

        .panel {
            padding: 18px;
            min-height: 280px;
        }

        .panel h2 {
            margin: 0 0 12px;
            font-size: 1.05rem;
            letter-spacing: 0.02em;
        }

        pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            background: #071325;
            border: 1px solid rgba(88, 121, 158, 0.35);
            border-radius: 12px;
            padding: 14px;
            color: #f7fbff;
            line-height: 1.45;
            overflow-x: auto;
        }

        .empty {
            color: var(--muted);
        }

        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .hero h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <main class="page">
        <section class="hero">
            <h1>MissionSpec AI</h1>
            <p>Paste a technical requirement below to break it into testable sub-requirements and generate implementation, tests, and a compliance checklist.</p>
        </section>

        <section class="form-card">
            <form method="post">
                <label for="requirement">Technical Requirement</label>
                <textarea id="requirement" name="requirement">{{ requirement_text }}</textarea>
                <div class="actions">
                    <button type="submit">Submit</button>
                    <button type="submit" name="action" value="download">Download Report</button>
                </div>
            </form>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </section>

        <section class="grid">
            <article class="panel">
                <h2>Parsed Sub-Requirements</h2>
                {% if outputs %}
                <pre>{{ outputs.subrequirements }}</pre>
                {% else %}
                <p class="empty">Generated sub-requirements will appear here.</p>
                {% endif %}
            </article>

            <article class="panel">
                <h2>Generated Code Scaffold</h2>
                {% if outputs %}
                <pre>{{ outputs.scaffold }}</pre>
                {% else %}
                <p class="empty">Generated scaffold code will appear here.</p>
                {% endif %}
            </article>

            <article class="panel">
                <h2>Generated Tests</h2>
                {% if outputs %}
                <pre>{{ outputs.tests }}</pre>
                {% else %}
                <p class="empty">Generated pytest tests will appear here.</p>
                {% endif %}
            </article>

            <article class="panel">
                <h2>Compliance Checklist</h2>
                {% if outputs %}
                <pre>{{ outputs.checklist }}</pre>
                {% else %}
                <p class="empty">Generated checklist content will appear here.</p>
                {% endif %}
            </article>
        </section>
    </main>
</body>
</html>
"""


def _build_outputs(requirement_text: str) -> dict[str, str]:
    """Generate all UI output panels from a requirement."""
    subrequirements = parse_requirements(requirement_text)
    return {
        "subrequirements": json.dumps(subrequirements, indent=2),
        "scaffold": generate_scaffold(subrequirements),
        "tests": generate_tests(subrequirements),
        "checklist": generate_checklist(subrequirements),
    }


def _build_markdown_report(requirement_text: str, outputs: dict[str, str]) -> str:
    """Format a single markdown report containing all MissionSpec outputs."""
    return "\n".join(
        [
            "# MissionSpec AI Report",
            "",
            "## Source Requirement",
            requirement_text,
            "",
            "## Parsed Sub-Requirements",
            "```json",
            outputs["subrequirements"],
            "```",
            "",
            "## Generated Code Scaffold",
            "```python",
            outputs["scaffold"].rstrip(),
            "```",
            "",
            "## Generated Tests",
            "```python",
            outputs["tests"].rstrip(),
            "```",
            "",
            "## Compliance Checklist",
            outputs["checklist"].rstrip(),
            "",
        ]
    )


@app.route("/", methods=["GET", "POST"])
def index() -> str | Response:
    """Render the MissionSpec AI web UI."""
    requirement_text = DEFAULT_REQUIREMENT
    outputs: dict[str, str] | None = None
    error = ""

    if request.method == "POST":
        requirement_text = request.form.get("requirement", DEFAULT_REQUIREMENT).strip() or DEFAULT_REQUIREMENT
        action = request.form.get("action", "submit")
        if not requirement_text:
            error = "Please provide a technical requirement before submitting."
        else:
            outputs = _build_outputs(requirement_text)
            if action == "download":
                report = _build_markdown_report(requirement_text, outputs)
                return Response(
                    report,
                    mimetype="text/markdown",
                    headers={"Content-Disposition": "attachment; filename=missionspec_report.md"},
                )

    return render_template_string(
        PAGE_TEMPLATE,
        requirement_text=requirement_text,
        outputs=outputs,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
