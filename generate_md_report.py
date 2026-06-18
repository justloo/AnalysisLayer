import json
from pathlib import Path
from analysis_layer.simulator.loader import load_scenario
from analysis_layer.simulator.synthetic import run_scenario

custom_files = [
    # Batch 1 (files)
    "echo_inflation_no_real_signal.json",
    "mirror_imaging_trap.json",
    "noise_pileup_vs_signal.json",
    "thin_evidence_honest_null.json",
    "weak_signal_early_cut.json",
    # Batch 2 (files1)
    "fifty_fifty_mixed.json",
    "high_volume_rich_stream.json",
    "minimal_single_signal.json",
    "only_correct_data.json",
    "only_wrong_data.json"
]

md_lines = [
    "# Custom Scenarios Analysis Results",
    "",
    "This report provides a detailed breakdown of the deterministic analysis runs for the ten custom scenarios, showing how the disconfirmation engine handled echos, noise, weak signals, high-volume streams, and conflicting data.",
    "",
    "## Summary of Runs",
    "",
    "| Scenario ID | Expected Forecast | Actual Forecast | Status | Likelihood | Confidence |",
    "| :--- | :--- | :--- | :---: | :--- | :--- |"
]

results = []

for filename in custom_files:
    path = Path("analysis_layer/simulator/scenarios") / filename
    scenario = load_scenario(path)
    res = run_scenario(scenario)
    a = res.assessment
    
    # Sort hypotheses by likelihood
    hyps = sorted(a.hypotheses, key=lambda x: x.relative_likelihood, reverse=True)
    
    status_emoji = "✅ PASS" if res.passed else "❌ FAIL"
    md_lines.append(
        f"| **{scenario.id}** | `{res.expected_leading}` | `{res.leading_hypothesis}` | {status_emoji} | {a.likelihood.term.value} | {a.confidence.level.value} |"
    )
    
    results.append((scenario, res, a, hyps))

md_lines.append("")
md_lines.append("---")
md_lines.append("")

for scenario, res, a, hyps in results:
    md_lines.append(f"## Scenario: `{scenario.id}`")
    md_lines.append("")
    
    status_str = "🟢 **PASS**" if res.passed else "🔴 **FAIL**"
    md_lines.append(f"**Verification Status:** {status_str}")
    md_lines.append("")
    
    md_lines.append("> [!NOTE]")
    md_lines.append(f"> **BLUF:** {a.bluf}")
    md_lines.append("")
    
    md_lines.append("### Ground Truth & Setup")
    md_lines.append(f"- **True State of World:** {scenario.ground_truth.state}")
    md_lines.append(f"- **True Resolution:** `{scenario.ground_truth.resolves_to}`")
    md_lines.append(f"- **Recommended Action:** *{a.recommended_action}*")
    md_lines.append("")
    
    md_lines.append("### Hypothesis Posteriors (ACH Disconfirmation)")
    md_lines.append("")
    md_lines.append("| Hypothesis | Prior / Base Rate | Posterior Probability | Status | Rationale |")
    md_lines.append("| :--- | :---: | :---: | :---: | :--- |")
    
    base_rates = {
        "price_cut": 0.18,
        "price_increase": 0.15,
        "repackaging": 0.12,
        "no_change": 0.5,
        "deception": 0.05
    }
    
    for h in hyps:
        prior = base_rates.get(h.id, 0.1)
        prob_str = f"{h.relative_likelihood * 100:.2f}%"
        status_badge = f"**{h.status.value.upper()}**" if h.status.value == "leading" else h.status.value
        md_lines.append(
            f"| {h.statement} (`{h.id}`) | {prior:.2f} | **{prob_str}** | {status_badge} | {h.rationale} |"
        )
        
    md_lines.append("")
    md_lines.append("### Evidence & Signal Stream")
    md_lines.append("")
    md_lines.append("| Signal ID | Content | Reliability | Credibility | Origin ID | Diagnosticity | Role |")
    md_lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :--- |")
    
    for e in a.evidence:
        orig = e.origin_id
        sig = next((s for s in scenario.signal_stream if s.id == e.id), None)
        role = sig.role.value if sig and sig.role else "noise"
        
        weak_prefix = "⚠️ [WEAK] " if e.weak_signal else ""
        md_lines.append(
            f"| `{e.id}` | {weak_prefix}{e.content} | `{e.source_reliability.value}` | `{e.information_credibility.value}` | `{orig}` | **{e.diagnostic_value:.2f}** | {role} |"
        )
        
    md_lines.append("")
    
    # Red team
    md_lines.append("### Red Team Review")
    md_lines.append(f"- **Red Team Outcome:** `{a.red_team.outcome.value}`")
    if a.red_team.challenges_raised:
        md_lines.append("- **Challenges Raised:**")
        for challenge in a.red_team.challenges_raised:
            md_lines.append(f"  > ⚠️ {challenge}")
    else:
        md_lines.append("- **Challenges Raised:** None. Passed without objections.")
    md_lines.append("")
    
    # Assumptions & Gaps
    md_lines.append("### Assumptions & Gaps")
    md_lines.append("")
    md_lines.append("**Load-Bearing Assumptions:**")
    for ass in a.assumptions:
        md_lines.append(f"- *{ass.statement}* (Fragility: **{ass.fragility}**)")
        
    md_lines.append("")
    md_lines.append("**Information / Collection Gaps:**")
    if a.gaps:
        for gap in a.gaps:
            md_lines.append(f"- {gap}")
    else:
        md_lines.append("- None identified.")
        
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

# Write to the artifact directory
artifact_path = Path("/Users/galmeyer1/.gemini/antigravity-ide/brain/826e3629-8ffb-484d-83ce-2601872032a9/custom_scenarios_results.md")
artifact_path.write_text("\n".join(md_lines))
print(f"Successfully generated artifact at: {artifact_path}")
