"""Canonical task names for reasoning nodes.

Each model-reasoning node identifies its task by one of these constants. The
real provider maps a task to a system prompt; the deterministic MockClient maps
it to a handler. Keeping the names in one place prevents drift between the two.
"""

GENERATE_HYPOTHESES = "generate_hypotheses"
JUDGE_CELL = "judge_cell"
GRADE_EVIDENCE = "grade_evidence"
CLASSIFY_SOURCE_TYPE = "classify_source_type"
CHECK_ASSUMPTIONS = "check_assumptions"
RED_TEAM = "red_team"
SYNTHESIZE = "synthesize"
GENERATE_SCENARIO = "generate_scenario"
