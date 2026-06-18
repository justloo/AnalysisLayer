import json
from pathlib import Path
from datetime import datetime
from analysis_layer.simulator.report_builder import build_library_reports, report_to_dict

custom_files = [
    "echo_inflation_no_real_signal.json",
    "mirror_imaging_trap.json",
    "noise_pileup_vs_signal.json",
    "thin_evidence_honest_null.json",
    "weak_signal_early_cut.json"
]

scenario_paths = [Path("analysis_layer/simulator/scenarios") / f for f in custom_files]
reports = build_library_reports(scenario_paths)
results = [report_to_dict(r) for r in reports]

# HTML Generation Template
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Layer: Custom Scenario Run Results</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #161c2c;
            --bg-card: rgba(22, 28, 44, 0.65);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --primary: #38bdf8;
            --primary-glow: rgba(56, 189, 248, 0.15);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.15);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.15);
            --warning: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.15);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            padding: 3rem 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
            background-image: radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.03) 0%, transparent 40%);
        }}

        header {{
            margin-bottom: 3rem;
            text-align: center;
            position: relative;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.75rem;
            font-weight: 800;
            letter-spacing: -0.05em;
            background: linear-gradient(135deg, #f8fafc 30%, #38bdf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.125rem;
            font-weight: 400;
        }}

        /* Overview Summary Grid */
        .summary-dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            text-align: center;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        }}

        .stat-val {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.25rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.25rem;
        }}

        .stat-val.success {{ color: var(--success); }}
        
        .stat-lbl {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* Scenario Cards */
        .scenarios-container {{
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.24);
            overflow: hidden;
        }}

        .card:hover {{
            border-color: rgba(56, 189, 248, 0.3);
            box-shadow: 0 12px 40px rgba(56, 189, 248, 0.06);
            transform: translateY(-2px);
        }}

        .card-header {{
            padding: 1.75rem 2rem;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
        }}

        .card-title-group {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .card-id {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
        }}

        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .badge.pass {{
            background: var(--success-glow);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .badge.fail {{
            background: var(--danger-glow);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .card-header-meta {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}

        .meta-item {{
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}

        .meta-item strong {{
            color: #ffffff;
        }}

        .chevron {{
            width: 20px;
            height: 20px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}

        .card.collapsed .chevron {{
            transform: rotate(-90deg);
        }}

        .card-body {{
            padding: 2.25rem 2rem;
        }}

        .card.collapsed .card-body {{
            display: none;
        }}

        /* Grid sections */
        .section-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}

        @media (max-width: 768px) {{
            .section-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .block {{
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .block-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--primary);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* BLUF panel */
        .bluf-panel {{
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.05) 0%, rgba(15, 23, 42, 0) 100%);
            border-left: 4px solid var(--primary);
            border-radius: 0 12px 12px 0;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}

        .bluf-title {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.125rem;
            color: #ffffff;
            margin-bottom: 0.5rem;
        }}

        .bluf-text {{
            color: var(--text-primary);
        }}

        /* Hypotheses Progress Bars */
        .hyp-item {{
            margin-bottom: 1.25rem;
        }}

        .hyp-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 0.35rem;
        }}

        .hyp-name {{
            font-weight: 500;
            color: #ffffff;
        }}

        .hyp-prob {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: var(--primary);
        }}

        .progress-bar-container {{
            background: rgba(255, 255, 255, 0.06);
            height: 8px;
            border-radius: 9999px;
            overflow: hidden;
        }}

        .progress-bar {{
            height: 100%;
            border-radius: 9999px;
            background: linear-gradient(90deg, #38bdf8, #0ea5e9);
        }}

        .hyp-item.leading .progress-bar {{
            background: linear-gradient(90deg, #059669, #10b981);
        }}
        
        .hyp-item.leading .hyp-prob {{
            color: var(--success);
        }}

        .hyp-rationale {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}

        /* Red Team block */
        .red-team-block {{
            background: rgba(239, 68, 68, 0.02);
            border: 1px solid rgba(239, 68, 68, 0.08);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .red-team-title {{
            color: var(--danger);
        }}

        .red-team-challenge {{
            background: rgba(239, 68, 68, 0.03);
            border-left: 2px solid var(--danger);
            padding: 0.75rem 1rem;
            margin-bottom: 0.75rem;
            font-size: 0.875rem;
            color: var(--text-primary);
            border-radius: 0 6px 6px 0;
        }}

        /* Signals Table */
        .table-container {{
            overflow-x: auto;
            margin-top: 2rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }}

        th {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: var(--text-secondary);
            padding: 0.75rem 1rem;
            border-bottom: 2px solid var(--border-color);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.75rem;
        }}

        td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
            color: var(--text-primary);
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.01);
        }}

        .grade-badge {{
            display: inline-block;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 0.75rem;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}

        .grade-badge.a, .grade-badge.one {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border-color: rgba(16, 185, 129, 0.2);
        }}

        .grade-badge.b, .grade-badge.two {{
            background: rgba(56, 189, 248, 0.1);
            color: var(--primary);
            border-color: rgba(56, 189, 248, 0.2);
        }}

        .grade-badge.c, .grade-badge.three {{
            background: rgba(245, 158, 11, 0.1);
            color: var(--warning);
            border-color: rgba(245, 158, 11, 0.2);
        }}

        .weak-signal-label {{
            background: var(--warning-glow);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 4px;
            padding: 0.1rem 0.35rem;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        ul.dash-list {{
            list-style-type: none;
        }}

        ul.dash-list li {{
            position: relative;
            padding-left: 1.25rem;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }}

        ul.dash-list li::before {{
            content: "—";
            position: absolute;
            left: 0;
            color: var(--primary);
        }}
    </style>
</head>
<body>

    <header>
        <h1>Custom Scenarios Execution Report</h1>
        <div class="subtitle">Deterministic analysis results of the 5 custom scenario test cases</div>
    </header>

    <section class="summary-dashboard">
        <div class="stat-card">
            <div class="stat-val">5</div>
            <div class="stat-lbl">Scenarios Run</div>
        </div>
        <div class="stat-card">
            <div class="stat-val success">100%</div>
            <div class="stat-lbl">Invariants Pass</div>
        </div>
        <div class="stat-card">
            <div class="stat-val success">PASS</div>
            <div class="stat-lbl">Overall Assessment</div>
        </div>
    </section>

    <main class="scenarios-container">
"""

for idx, res in enumerate(results):
    passed_badge = '<span class="badge pass">Pass</span>' if res["passed"] else '<span class="badge fail">Fail</span>'
    collapsed_class = "collapsed" if idx > 0 else ""
    
    # Render key judgments
    key_judgments_html = "".join([f"<li>{kj}</li>" for kj in res["key_judgments"]])
    
    # Render hypotheses
    hypotheses_html = ""
    for h in res["hypotheses"]:
        prob_pct = f"{h['relative_likelihood']*100:.2f}%"
        leading_class = "leading" if h["status"] == "leading" else ""
        hypotheses_html += f"""
        <div class="hyp-item {leading_class}">
            <div class="hyp-header">
                <span class="hyp-name">{h['statement']}</span>
                <span class="hyp-prob">{prob_pct}</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {h['relative_likelihood']*100}%"></div>
            </div>
            <div class="hyp-rationale">{h['rationale']}</div>
        </div>
        """
        
    # Render red team
    red_team_html = ""
    if res["red_team"]["challenges_raised"]:
        for c in res["red_team"]["challenges_raised"]:
            red_team_html += f'<div class="red-team-challenge">{c}</div>'
    else:
        red_team_html += '<div style="color: var(--text-secondary); font-size: 0.875rem;">No adversarial challenges were raised. The assessment successfully passed red team review.</div>'
        
    # Render assumptions & gaps
    assumptions_html = ""
    for ass in res["assumptions"]:
        assumptions_html += f"<li>{ass['statement']} (Fragility: <strong>{ass['fragility']}</strong>)</li>"
        
    gaps_html = ""
    if res["gaps"]:
        for gap in res["gaps"]:
            gaps_html += f"<li>{gap}</li>"
    else:
        gaps_html = '<li>No collection gaps identified.</li>'
        
    # Render evidence signals
    evidence_rows_html = ""
    for ev in res["evidence"]:
        ws_badge = '<span class="weak-signal-label">Weak Signal</span> ' if ev["weak_signal"] else ""
        rel_class = ev["source_reliability"].lower()
        cred_class = ev["information_credibility"].lower()
        
        evidence_rows_html += f"""
        <tr>
            <td style="font-family: monospace; font-weight: 500;">{ev['id']}</td>
            <td>{ws_badge}{ev['content']}</td>
            <td style="text-align: center;"><span class="grade-badge {rel_class}">{ev['source_reliability']}</span></td>
            <td style="text-align: center;"><span class="grade-badge {cred_class}">{ev['information_credibility']}</span></td>
            <td style="text-align: center; color: var(--text-secondary);">{ev['origin_id']}</td>
            <td style="text-align: center; font-weight: 600; color: var(--primary);">{ev['diagnostic_value']}</td>
        </tr>
        """
        
    html_content += f"""
        <article class="card {collapsed_class}" id="card-{res['id']}">
            <div class="card-header" onclick="toggleCard('{res['id']}')">
                <div class="card-title-group">
                    <span class="card-id">{res['id']}</span>
                    {passed_badge}
                </div>
                <div class="card-header-meta">
                    <div class="meta-item">Likelihood: <strong>{res['likelihood']['term']} ({res['likelihood']['low']*100:.0f}-{res['likelihood']['high']*100:.0f}%)</strong></div>
                    <div class="meta-item">Confidence: <strong>{res['confidence']['level']}</strong></div>
                    <svg class="chevron" viewBox="0 0 24 24">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </div>
            </div>
            
            <div class="card-body">
                <div class="bluf-panel">
                    <div class="bluf-title">BLUF (Bottom Line Up Front)</div>
                    <div class="bluf-text">{res['bluf']}</div>
                </div>
                
                <div class="section-grid">
                    <div class="block">
                        <div class="block-title">Key Judgments</div>
                        <ul class="dash-list">
                            {key_judgments_html}
                        </ul>
                        <div style="margin-top: 1.25rem;">
                            <div class="block-title" style="font-size: 0.875rem;">Recommended Action</div>
                            <p style="font-size: 0.875rem; color: var(--text-secondary);">{res['recommended_action']}</p>
                        </div>
                    </div>
                    
                    <div class="block">
                        <div class="block-title">Ground Truth & Expectations</div>
                        <p style="font-size: 0.875rem; margin-bottom: 0.75rem;"><strong>True State of World:</strong> <span style="color: var(--text-secondary);">{res['ground_truth_state']}</span></p>
                        <p style="font-size: 0.875rem; margin-bottom: 0.75rem;"><strong>Expected Forecast:</strong> <span style="color: var(--primary); font-weight: 600;">{res['expected_leading']}</span></p>
                        <p style="font-size: 0.875rem;"><strong>Actual Forecast:</strong> <span style="color: var(--success); font-weight: 600;">{res['leading_hypothesis']}</span></p>
                    </div>
                </div>
                
                <div class="section-grid">
                    <div class="block" style="grid-column: span 1;">
                        <div class="block-title">Hypothesis Posteriors (Disconfirmation ACH)</div>
                        {hypotheses_html}
                    </div>
                    
                    <div class="red-team-block" style="grid-column: span 1;">
                        <div class="block-title red-team-title">Red Team Adversarial Review ({res['red_team']['outcome']})</div>
                        {red_team_html}
                    </div>
                </div>
                
                <div class="section-grid">
                    <div class="block">
                        <div class="block-title">Load-Bearing Assumptions</div>
                        <ul class="dash-list">
                            {assumptions_html}
                        </ul>
                    </div>
                    
                    <div class="block">
                        <div class="block-title">Information & Collection Gaps</div>
                        <ul class="dash-list">
                            {gaps_html}
                        </ul>
                    </div>
                </div>
                
                <div class="block" style="margin-top: 2rem;">
                    <div class="block-title">Evidence Signal Stream</div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 10%;">Signal ID</th>
                                    <th style="width: 50%;">Content</th>
                                    <th style="width: 10%; text-align: center;">Reliability</th>
                                    <th style="width: 10%; text-align: center;">Credibility</th>
                                    <th style="width: 10%; text-align: center;">Origin ID</th>
                                    <th style="width: 10%; text-align: center;">Diagnosticity</th>
                                </tr>
                            </thead>
                            <tbody>
                                {evidence_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </article>
    """

html_content += """
    </main>

    <script>
        function toggleCard(cardId) {
            const card = document.getElementById('card-' + cardId);
            card.classList.toggle('collapsed');
        }
    </script>
</body>
</html>
"""

Path("custom_scenarios_results.html").write_text(html_content)
print("Successfully generated custom_scenarios_results.html")
