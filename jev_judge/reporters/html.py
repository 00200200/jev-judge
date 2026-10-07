"""Self-contained interactive HTML report generator for jev-judge test suites."""

import html
from typing import List
from jev_judge.models import TestSuiteResult


def generate_html_report(suite_results: List[TestSuiteResult], title: str = "Jev-Judge Test Report") -> str:
    """Generate a single-file, self-contained interactive HTML dashboard."""
    total_suites = len(suite_results)
    total_cases = sum(s.total_tests for s in suite_results)
    passed_cases = sum(s.passed_tests for s in suite_results)
    failed_cases = sum(s.failed_tests for s in suite_results)
    total_duration_ms = sum(s.duration_ms for s in suite_results)
    total_cost_usd = sum(s.total_cost_usd for s in suite_results)
    gpt4o_est_cost = total_cases * 0.025
    savings_pct = ((gpt4o_est_cost - total_cost_usd) / gpt4o_est_cost * 100.0) if gpt4o_est_cost > 0 else 0.0

    all_passed = failed_cases == 0 and total_cases > 0
    status_color = "#10b981" if all_passed else "#f43f5e"
    status_text = "ALL PASSED" if all_passed else f"{failed_cases} FAILED"

    # Build suite cards
    suite_html_blocks = []
    for s_idx, suite in enumerate(suite_results):
        suite_badge = '<span class="badge badge-pass">PASS</span>' if suite.is_success else '<span class="badge badge-fail">FAIL</span>'
        cases_html = []

        for c_idx, res in enumerate(suite.results):
            tc = res.test_case
            c_badge = '<span class="badge badge-pass">✓ PASS</span>' if res.passed else '<span class="badge badge-fail">✕ FAIL</span>'
            status_class = "case-pass" if res.passed else "case-fail"

            # Assertions table
            assertion_rows = []
            for name, dec in res.decisions.items():
                dec_status = '<span class="badge badge-pass">PASS</span>' if dec.passed else '<span class="badge badge-fail">FAIL</span>'
                val_repr = html.escape(str(dec.value)) if dec.value is not None else "-"
                prob_repr = f"{dec.probability:.2f}" if dec.probability is not None else "-"
                thresh_repr = f"{dec.threshold:.2f}" if dec.threshold is not None else "-"
                err_text = html.escape(dec.error or "") if dec.error else ""
                
                assertion_rows.append(f"""
                <tr>
                    <td class="font-mono text-indigo-400">{html.escape(name)}</td>
                    <td class="font-mono text-zinc-400">{html.escape(dec.decision_type.value if hasattr(dec.decision_type, 'value') else str(dec.decision_type))}</td>
                    <td>{val_repr}</td>
                    <td class="font-mono">{prob_repr}</td>
                    <td class="font-mono">{thresh_repr}</td>
                    <td>{dec_status}</td>
                    <td class="text-rose-400 text-xs font-mono">{err_text}</td>
                </tr>
                """)

            assertions_table = f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Assertion</th>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Probability</th>
                        <th>Threshold</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(assertion_rows)}
                </tbody>
            </table>
            """

            # Optional I/O blocks
            io_blocks = []
            if tc.input:
                io_blocks.append(f"""
                <div class="io-block">
                    <div class="io-label">User Input / Query</div>
                    <pre>{html.escape(tc.input)}</pre>
                </div>
                """)
            if tc.context:
                ctx_str = str(tc.context)
                io_blocks.append(f"""
                <div class="io-block">
                    <div class="io-label">Grounding Context</div>
                    <pre>{html.escape(ctx_str)}</pre>
                </div>
                """)
            if tc.output:
                io_blocks.append(f"""
                <div class="io-block">
                    <div class="io-label">Model Output</div>
                    <pre>{html.escape(tc.output)}</pre>
                </div>
                """)

            case_card = f"""
            <div class="case-card {status_class}" data-passed="{'true' if res.passed else 'false'}">
                <div class="case-header" onclick="toggleDetails('c_{s_idx}_{c_idx}')">
                    <div class="case-title-row">
                        {c_badge}
                        <span class="case-name">{html.escape(tc.name)}</span>
                    </div>
                    <div class="case-meta">
                        <span>{res.duration_ms:.1f}ms</span>
                        <span>${res.total_cost_usd:.5f}</span>
                        <span class="chevron" id="chevron_c_{s_idx}_{c_idx}">▼</span>
                    </div>
                </div>
                <div class="case-details" id="c_{s_idx}_{c_idx}">
                    {''.join(io_blocks)}
                    <div class="io-label" style="margin-top:12px;">Evaluations & Decisions</div>
                    {assertions_table}
                </div>
            </div>
            """
            cases_html.append(case_card)

        suite_card = f"""
        <div class="suite-card">
            <div class="suite-header">
                <div class="suite-title-row">
                    {suite_badge}
                    <span class="suite-name">{html.escape(suite.file_path or suite.suite_name)}</span>
                    <span class="text-zinc-500 text-xs">({suite.passed_tests}/{suite.total_tests} passed)</span>
                </div>
                <div class="suite-meta">
                    <span>{suite.duration_ms:.1f} ms</span>
                    <span>${suite.total_cost_usd:.5f}</span>
                </div>
            </div>
            <div class="suite-body">
                {''.join(cases_html)}
            </div>
        </div>
        """
        suite_html_blocks.append(suite_card)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --bg-base: #0b0f19;
            --bg-surface: #111827;
            --bg-card: #1f2937;
            --border: #374151;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent: #6366f1;
            --pass: #10b981;
            --fail: #f43f5e;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 32px 20px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
            margin-bottom: 28px;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-icon {{
            font-size: 28px;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
        }}
        h1 {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }}
        .stat-sub {{
            font-size: 11px;
            color: #10b981;
            margin-top: 4px;
        }}
        .controls-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .filter-buttons {{
            display: flex;
            gap: 8px;
        }}
        .filter-btn {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.15s;
        }}
        .filter-btn.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        .search-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 7px 14px;
            border-radius: 6px;
            font-size: 13px;
            width: 260px;
        }}
        .search-box:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .suite-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .suite-header {{
            background: rgba(31, 41, 55, 0.5);
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }}
        .suite-title-row {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .suite-name {{
            font-size: 14px;
            font-weight: 600;
            font-family: monospace;
        }}
        .suite-meta {{
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            gap: 12px;
        }}
        .case-card {{
            border-bottom: 1px solid rgba(55, 65, 81, 0.4);
        }}
        .case-card:last-child {{
            border-bottom: none;
        }}
        .case-header {{
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: background 0.1s;
        }}
        .case-header:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .case-title-row {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .case-name {{
            font-size: 13px;
            font-weight: 500;
        }}
        .case-meta {{
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .chevron {{
            font-size: 9px;
            transition: transform 0.2s;
        }}
        .case-details {{
            display: none;
            padding: 14px 16px 16px;
            background: rgba(17, 24, 39, 0.6);
            border-top: 1px dashed rgba(55, 65, 81, 0.5);
        }}
        .io-block {{
            margin-bottom: 10px;
        }}
        .io-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            font-weight: 600;
            margin-bottom: 4px;
        }}
        pre {{
            background: #080c14;
            border: 1px solid rgba(55, 65, 81, 0.5);
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            white-space: pre-wrap;
            word-break: break-word;
            color: #e5e7eb;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 6px;
            font-size: 12px;
        }}
        .data-table th {{
            text-align: left;
            padding: 6px 10px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .data-table td {{
            padding: 6px 10px;
            border-bottom: 1px solid rgba(55, 65, 81, 0.3);
        }}
        .badge {{
            display: inline-block;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        .badge-pass {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .badge-fail {{
            background: rgba(244, 63, 94, 0.15);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }}
        footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}
        .font-mono {{ font-family: ui-monospace, SFMono-Regular, monospace; }}
        .text-indigo-400 {{ color: #818cf8; }}
        .text-rose-400 {{ color: #fb7185; }}
        .text-zinc-400 {{ color: #9ca3af; }}
        .text-zinc-500 {{ color: #6b7280; }}
        .text-xs {{ font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <span class="brand-icon">⚡</span>
                <div>
                    <h1>{html.escape(title)}</h1>
                    <div style="font-size: 12px; color: var(--text-secondary);">Vitest for LLM outputs • Powered by TypeSafe Jev (System One)</div>
                </div>
            </div>
            <div>
                <span class="badge" style="background: {status_color}22; color: {status_color}; border: 1px solid {status_color}55; font-size: 13px; padding: 6px 14px;">
                    {status_text}
                </span>
            </div>
        </header>

        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-label">Test Results</div>
                <div class="stat-value">{passed_cases}/{total_cases}</div>
                <div class="stat-sub">{total_suites} suites evaluated</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Execution Time</div>
                <div class="stat-value">{total_duration_ms:.1f} ms</div>
                <div class="stat-sub">sub-100ms per decision</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Evaluator Cost</div>
                <div class="stat-value">${total_cost_usd:.5f}</div>
                <div class="stat-sub">Saved {savings_pct:.1f}% vs GPT-4o</div>
            </div>
        </div>

        <div class="controls-bar">
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="setFilter('all')">All ({total_cases})</button>
                <button class="filter-btn" onclick="setFilter('passed')">Passed ({passed_cases})</button>
                <button class="filter-btn" onclick="setFilter('failed')">Failed ({failed_cases})</button>
            </div>
            <input type="text" class="search-box" placeholder="Search test cases..." oninput="handleSearch(this.value)">
        </div>

        <div id="suites-container">
            {''.join(suite_html_blocks)}
        </div>

        <footer>
            Built with <strong>jev-judge</strong> • <a href="https://github.com/00200200/jev-judge" style="color: var(--accent); text-decoration: none;" target="_blank">GitHub Repository</a>
        </footer>
    </div>

    <script>
        function toggleDetails(id) {{
            const details = document.getElementById(id);
            const chevron = document.getElementById('chevron_' + id);
            if (details.style.display === 'block') {{
                details.style.display = 'none';
                if (chevron) chevron.style.transform = 'rotate(0deg)';
            }} else {{
                details.style.display = 'block';
                if (chevron) chevron.style.transform = 'rotate(180deg)';
            }}
        }}

        let currentFilter = 'all';
        let searchQuery = '';

        function setFilter(filter) {{
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.toLowerCase().startsWith(filter));
            }});
            applyFilters();
        }}

        function handleSearch(query) {{
            searchQuery = query.toLowerCase();
            applyFilters();
        }}

        function applyFilters() {{
            document.querySelectorAll('.case-card').forEach(card => {{
                const isPassed = card.getAttribute('data-passed') === 'true';
                const text = card.textContent.toLowerCase();
                let matchesStatus = true;
                if (currentFilter === 'passed') matchesStatus = isPassed;
                if (currentFilter === 'failed') matchesStatus = !isPassed;

                const matchesSearch = !searchQuery || text.includes(searchQuery);
                card.style.display = (matchesStatus && matchesSearch) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
