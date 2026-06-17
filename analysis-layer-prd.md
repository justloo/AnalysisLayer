# Analysis Layer: Product Requirements Document

**Status:** Build-ready. This PRD operationalizes the analytic doctrine into a testable v0.
**Companion artifacts:** the system-design diagram (analysis-layer-system-design.mermaid), and the full doctrine, reproduced here as Appendix A.
**Reading order:** the PRD body defines what to build and how to know it works. Appendix A is the canonical methodology the build implements. Where the body says "satisfies R-n," it refers to the design rules in Appendix A, Section 12.

---

## 1. Summary

The analysis layer is a judgment engine. It receives a stream of signals and produces decision-ready, confidence-scored, auditable assessments. It is tool-agnostic, sitting on top of any collection source, which means it can be sold even to a team already paying for a collection tool that only produces noise.

The market work established the opening: the commercial intelligence category has solved collection and is uniformly weak on analysis. Tools surface mentions and changes but do not interpret, weight, or reason, and they tell you what already happened rather than what is coming. This layer automates the senior analyst's judgment rather than the junior analyst's clipping, which is the one part of the problem nobody has built well and the part where intelligence tradecraft is a genuine and hard-to-copy edge.

This PRD scopes a v0 whose explicit purpose is to be testable. The goal of the first build is not a product surface or a customer. It is a working reasoning core, anchored on one decision type, that a simulator can exercise against authored ground truth and score against resolved outcomes. Everything here is in service of reaching that testable state quickly and on solid foundations.

---

## 2. Goals and non-goals

**Goal one.** Stand up the reasoning core (hypothesis generation, the evidence-by-hypothesis matrix, diagnosticity scoring, disconfirmation testing, and the computed confidence model) on a single decision type, exactly as the build order in Appendix A, Section 15 prescribes.

**Goal two.** Ship the simulator alongside the core, not after it, so the layer is testable from the first functional milestone. The simulator is treated as a product component, specified in Section 7.

**Goal three.** Make the layer self-scoring. Every assessment carries a resolvable claim and a resolution criterion, and the calibration machinery scores the layer against outcomes, which is both the test rig and the eventual production monitor.

**Non-goal one.** No collection. The layer consumes signals; it does not crawl, scrape, or monitor. Collection is mocked or replayed in v0.

**Non-goal two.** No product surface or routing integrations in v0. Output is the structured assessment object. Decision-moment delivery is designed for but not built yet.

**Non-goal three.** No multi-decision-type breadth in v0. One decision type, done with full rigor, beats five done shallowly.

**Non-goal four.** No autonomy. The layer states decision inputs, never business-strategy directives, and never replaces the decision-maker (R20).

---

## 3. The v0 decision-type anchor

The v0 is built and tested entirely on competitor pricing-move early warning. It is chosen because the stakes per decision are high, the signals are observable, and ground truth is easy to author and to resolve, which makes it ideal for the simulator.

**The PIR.** Will a tracked competitor make a material pricing change within the next thirty days, and if so, in which direction and on which product line.

**Representative signals.** Pricing-page edits, public statements from leadership, relevant hiring (pricing or revenue-operations roles), channel and partner chatter, promotion activity, packaging changes, and indicators of commercial pressure such as discounting patterns.

**The hypothesis set for this decision type.** Price cut, price increase, repackaging or tier restructuring without a headline price change, no material change, and, where plausible, a deception hypothesis that a visible signal is a planted feint. This set must always include the no-change null and is the starting template the engine refines per event (R7).

**The assessment, in plain terms.** A leading judgment such as a likely entry-tier price cut within the window, expressed with an ICD 203 likelihood term and its numeric band, carried with a separate five-factor confidence rating, supported by graded evidence, accompanied by the rejected alternatives and why, the load-bearing assumptions, the open gaps, a watch list of the specific future signals that would confirm or break the call, and a recommended action framed as an input to the operator's own pricing decision.

---

## 4. System architecture

The architecture is specified in full by Appendix A, Sections 2 through 11, and depicted in the companion diagram. The essentials for this PRD:

The control flow is a deterministic pipeline with language-model reasoning nodes inside it. It is not an autonomous agent that chooses its own path. This is forced by R3, which requires that no judgment skip grading, hypothesis testing, or adversarial review, and by R19, which requires the reasoning to be auditable, so the evidence-by-hypothesis matrix must be explicit, inspectable state held in code rather than implied inside one prompt.

Three node types make up the system. Deterministic code performs orchestration, relay collapse, diagnosticity arithmetic, leading-hypothesis selection, the confidence formula, the likelihood-band lookup, schema assembly, and all calibration math. Model reasoning performs hypothesis generation, per-cell consistency judgment, the assumptions check, the red-team challenge, and synthesis. Embedding and lightweight machine learning performs event clustering, deduplication, and source-type classification. The model judges; the code computes. That split is the answer to whether this is code-based or agent-based: it is both, in defined places.

Agents appear in the doctrine's specific sense. Several model analysts run the reasoning nodes in parallel, with their judgments aggregated by code and their disagreement preserved as a confidence signal (R18). The red team is a separate adversarial agent with genuine authority to downgrade confidence or return an event for collection (R16). Beyond these, nothing roams.

---

## 5. Functional requirements

Each requirement names the pipeline stage it builds and the acceptance criteria, expressed against the doctrine rules so the build is checkable.

**FR-1, Intake and source typing.** Normalize each incoming signal and capture full provenance, and classify source type as primary or relaying and as subjective or objective at intake. *Accepts when:* every evidence item carries provenance and a source-type tag, and relays carry a reference to the origin they echo (R6).

**FR-2, Event clustering.** Collapse signals describing one underlying event into a single unit of analysis tied to a PIR. *Accepts when:* duplicate and echoing signals about one event resolve to one event object carrying the full underlying set (R2).

**FR-3, Source and information grading.** Assign source reliability and information credibility on the corrected two-axis model, scoring the axes independently, permitting off-diagonal grades, collapsing relays so echo is not corroboration, and escalating rather than burying a high-reliability uncorroborated surprising claim. *Accepts when:* the engine can emit and act on an off-diagonal grade, echo across relays of one origin counts as one source, and a planted weak signal from a reliable source is escalated as a gap rather than downgraded into silence (R4, R5, R6).

**FR-4, Hypothesis generation.** Produce a hypothesis set that is as mutually exclusive and exhaustive as the question allows, always including the null and, where plausible, a deception hypothesis, before any evidence is weighed. *Accepts when:* the null is always present, the deception hypothesis appears when the scenario warrants it, and generation precedes scoring (R7).

**FR-5, Matrix and diagnosticity.** Build the evidence-by-hypothesis matrix, judge each cell for consistency, and score each item by diagnostic value, discounting items consistent with every hypothesis. *Accepts when:* the matrix is explicit, inspectable state, and non-diagnostic evidence does not drive the conclusion regardless of its vividness (R8).

**FR-6, Disconfirmation testing and updating.** Reach the leading judgment by elimination as the hypothesis with the least diagnostic evidence against it, keep and rank the rejected alternatives with reasons, and update from base rates in proportion to diagnostic weight. *Accepts when:* the leading judgment follows the disconfirmation rule, alternatives are retained with rationale, and updating starts from base rates and moves proportionally rather than by salience (R9, R10).

**FR-7, Assumptions and gaps.** Enumerate and rate the load-bearing assumptions, identify what would raise confidence, and emit those gaps as collection requirements. *Accepts when:* assumptions carry fragility ratings and gaps are emitted as structured requirements that feed back to collection.

**FR-8, Adversarial review.** Run the red-team pass over the fixed bias catalog, the single-source dependency check, and the deception check, with authority to downgrade or block. *Accepts when:* a case engineered to trip a specific bias is caught, a single-source-dependent conclusion is flagged and capped, and a successful challenge can actually stop a release or return the event (R16).

**FR-9, Confidence computation.** Compute confidence from the five-factor set, capped by its weakest link, and expose the drivers on demand. *Accepts when:* confidence is reproducible from the same inputs, a single severe weakness caps it low, and every value expands into its drivers (R15, R19).

**FR-10, Likelihood expression.** State likelihood using the ICD 203 lexicon with the numeric band rendered beside the term, kept in a separate field from confidence. *Accepts when:* likelihood and confidence never share a field or sentence, and the numeric band always accompanies the verbal term (R13, R14).

**FR-11, Synthesis.** Produce the assessment object in BLUF form with key judgments, graded evidence, the hypothesis set with statuses, assumptions, gaps, a recommended action framed as a decision input, and a watch list whose indicators carry explicit resolution criteria. *Accepts when:* the output validates against the schema in Section 6 and every assessment carries a resolvable claim with a resolution criterion (R17).

**FR-12, Aggregation.** Where multiple analysts run, aggregate their judgments and surface their disagreement as a confidence input rather than averaging it away. *Accepts when:* disagreement among analysts lowers confidence and is preserved in the output (R18).

**FR-13, Calibration logging.** Persist every assessment and its resolvable claim, and on resolution score it and feed the result back into the confidence model. *Accepts when:* resolved claims produce a Brier contribution and feed the per-segment calibration record (Section 11 of Appendix A).

---

## 6. The assessment object

The schema is the contract every consumer and the simulator build against. It is reproduced from Appendix A, Section 10, and is canonical there.

```
assessment {
  id
  pir_ref
  created_at
  bluf

  likelihood { term, probability_band }

  confidence {
    level                         // high | moderate | low
    band
    drivers { evidence_grade, independent_corroboration,
              hypothesis_margin, assumption_fragility, question_coverage }
  }

  key_judgments[]

  evidence[] {
    content, source_reliability, information_credibility,
    source_type, origin_id, provenance, diagnostic_value, grade_rationale
  }

  hypotheses[] { statement, status, rationale, relative_likelihood }
  assumptions[] { statement, fragility }
  gaps[]
  indicators_watch[] { indicator, direction, resolution_criterion }
  recommended_action

  red_team { checks_run[], challenges_raised[], outcome }
  human_overrides[]
  calibration { resolvable_claim, status, brier_contribution }
}
```

---

## 7. The simulator

The simulator is how the layer becomes testable, and it is a first-class component built in parallel with the core, not bolted on afterward. Its design reuses the live calibration machinery, which means the test rig and the production monitor are the same system fed different outcomes. It runs in six modes.

### 7.1 Mode one: deterministic fixtures

The code nodes are tested as ordinary software. Given a fixed matrix, the expected leading hypothesis. Given a fixed factor vector, the expected confidence band. Given a fixed set of relays, the expected collapsed corroboration count. These are conventional unit tests with fixed input and fixed output, and they cover the parts of the system that must behave identically every time.

### 7.2 Mode two: invariants

A set of properties that must hold on every run regardless of content, run as assertions against live pipeline output. The null hypothesis is always present. A high-reliability uncorroborated surprising claim is always escalated, never buried. Echo never counts as corroboration. Likelihood and confidence never share a sentence. The red team can actually block, verified by feeding cases engineered to trip one specific failure (a mirror-imaging trap, a single-source-dependency trap, a planted-deception trap) and asserting the challenge fires. These map to R5, R6, R7, R13, and R16 and are pass-or-fail gates.

### 7.3 Mode three: reference cases

Curated real events with an analyst-graded good hypothesis set and matrix. Because the reasoning nodes are non-deterministic, these are not exact-match assertions. The harness scores how close the engine's hypothesis set and diagnosticity judgments come to the analyst gold standard, which catches reasoning regressions that invariants miss.

### 7.4 Mode four: synthetic scenario simulation

This is the core of the rig and where most failure-mode testing lives. The operator authors ground truth, then declares the signal stream that such a world would emit, including the genuine early indicators, the noise, an echo cluster repeating one origin, a weak early signal from a reliable source, and optionally a planted deception signal. The harness injects the stream into the pipeline exactly as collection would, runs the full pipeline, and checks the things that matter: whether the engine reached the right leading hypothesis, whether it caught the weak signal rather than burying it, whether it resisted the deception, and whether its confidence tracked the quality of the planted evidence rather than its volume. Because the operator controls ground truth, specific failure modes can be probed on demand, and because the entities are synthetic, the contamination problem in Section 7.5 does not arise.

The scenario format is declarative:

```
scenario {
  id
  decision_type                 // competitor_pricing_move
  pir
  ground_truth {
    state                       // the true world state, hidden from the pipeline
    resolves_to                 // the outcome the forecast is scored against
  }
  signal_stream[] {             // injected in timestamp order
    content
    true_source_reliability     // authoring truth, used to score grading accuracy
    source_type                 // primary | relaying ; subjective | objective
    echo_of                     // id of the origin this relays, or null
    timestamp
    role                        // genuine_indicator | noise | echo | weak_signal | deception
  }
  expectations {
    leading_hypothesis
    must_catch_weak_signal      // true | false
    must_resist_deception       // true | false
    confidence_tracks           // evidence_quality_not_volume
  }
}
```

### 7.5 Mode five: backtesting on history

Real resolved events, replayed with only the information that existed before the outcome resolved, scored for whether the forecast was right and, more importantly, whether it was calibrated. This is the Good Judgment Project method used as a test. Its one failure mode is lookahead leakage, where the model already knows how the story ended and scores well from memory rather than reasoning. The defenses are mandatory: prefer events after the model's training cutoff, anonymize or transform entities so a case is not recognizable, and lean on synthetic scenarios for any probing of specific behaviors.

### 7.6 Mode six: shadow

Once live, the layer runs beside a human analyst or an incumbent tool without acting on its outputs, logging everything, before any graduated rollout. This is a deployment mode rather than a unit of the offline harness, included here because it is part of the same testing continuum.

### 7.7 The scenario-generator agent

An adversarial agent whose job is to invent synthetic scenarios designed to break the pipeline, the same critique-loop instinct the layer runs internally turned on the whole system. Its candidate scenarios are reviewed and the useful ones are added to the frozen library. This keeps the test set adversarial and growing rather than static.

### 7.8 The scoreboard

The output of the harness is a curve, not a green checkmark. Across all resolved and synthetic judgments it reports the calibration curve, the Brier score, and resolution, broken down per decision type and per source class exactly as Appendix A, Section 11 specifies. Overconfidence shows up as the curve sagging below the diagonal. Because the reasoning nodes are non-deterministic, every benchmark runs many times and the scoreboard reports the distribution rather than a single pass. The suite is frozen and re-run on every prompt change, model swap, or confidence reweighting, so an improvement in one place cannot silently regress calibration elsewhere.

### 7.9 Acceptance thresholds

These are the bars that define a passing v0. The values below are starting proposals and are to be set deliberately rather than treated as fixed, because the right bar depends on the base rate of the decision type.

| Check | Proposed bar for v0 |
| --- | --- |
| Invariant suite (Mode two) | 100 percent pass, every run |
| Deterministic fixtures (Mode one) | 100 percent pass |
| Leading-hypothesis accuracy on the seed synthetic library | above an agreed bar, reported with its run distribution |
| Weak-signal catch rate | above an agreed bar, no silent burials |
| Deception-resistance rate | above an agreed bar |
| Calibration on the backtest set | curve within an agreed tolerance of the diagonal, per segment |
| Run-to-run stability | confidence and leading hypothesis stable across repeated runs of the same scenario |

---

## 8. Testing and acceptance plan

The layer is considered ready to start testing when the reasoning core and the synthetic-scenario engine both exist, which is milestone M1 in Section 11. From that point the harness grows with the system.

A change is accepted into the build only if the frozen suite passes at or above the Section 7.9 bars on its distribution of runs. A regression in any segment of the calibration curve blocks the change even if the average improves, because a layer that gets better on pricing moves and worse on packaging changes has not improved. The shadow mode in Section 7.6 gates any move from offline testing toward a live setting.

---

## 9. Tech stack and build environment

### 9.1 Is Cursor the right place to build this

Yes for authoring, with one honest caveat: the integrated development environment is the least consequential decision in this project. What this is, technically, is a standard Python backend service plus a simulation harness. Cursor is well suited to writing exactly that, and it is a particularly good fit here because the codebase spans many interdependent files (the pipeline stages, the schema, the simulator, and the scenario library) that must stay in sync, which is where Cursor's repository-wide agentic editing earns its place. You already run Claude Code, and either tool works for this; choose by preference rather than by capability, since nothing about the project requires one over the other.

The decisions that matter far more than the editor are three. Keep the model layer behind a clean interface so a hosted frontier model can be swapped for a self-hosted open one without touching the pipeline, which the doctrine's provider-agnostic stance already assumes and which the data-sensitivity spectrum in Section 10 will eventually require. Hold the evidence-by-hypothesis matrix as explicit state rather than burying it inside a prompt, because R19 and the simulator both depend on inspecting it. And build the orchestration as an explicit deterministic workflow with model-call nodes rather than reaching for an autonomous-agent framework, because a framework that lets the model choose its own path actively fights R3. A thin orchestration layer is enough and keeps the enforced stage order honest.

### 9.2 Recommended stack

Python throughout. A model-client interface wrapping whichever providers are in use, with a strong reasoning tier for hypothesis generation and the red team and a small fast tier for the high-volume per-cell judgments and clustering, since the pipeline runs on every event and per-event cost compounds quickly. sentence-transformers for the embedding and clustering nodes, which is familiar ground. Postgres with pgvector as the single store for assessments, the calibration record, and the embeddings. pytest as the spine of the harness, with the simulator's synthetic and backtest engines built on top of it.

For v0 specifically, keep infrastructure minimal to reach a testable state fastest. No HTTP API and no task queue are needed at first; a command-line runner that executes the pipeline on a scenario file and prints the assessment plus the scoreboard is the shortest path to running tests. The asynchronous queue and the service wrapper are added only when the system moves past offline testing.

### 9.3 Repository layout

```
analysis-layer/
  pipeline/
    intake.py            # FR-1, source typing
    cluster.py           # FR-2, embeddings
    grade.py             # FR-3, corrected two-axis model
    weight.py            # FR-3, relay collapse, evidence weight
    hypotheses.py        # FR-4, generation
    matrix.py            # FR-5, matrix and diagnosticity
    test_step.py         # FR-6, disconfirmation and updating
    assumptions.py       # FR-7, assumptions and gaps
    redteam.py           # FR-8, adversarial agent
    confidence.py        # FR-9, five-factor model
    likelihood.py        # FR-10, ICD 203 lexicon
    synthesis.py         # FR-11, assessment object
    aggregate.py         # FR-12, ensemble aggregation
    orchestrator.py      # enforces stage order, R3
  models/
    client.py            # the swappable model interface
    tiers.py             # strong and fast tier routing
  schema/
    assessment.py        # the Section 6 contract
  calibration/
    store.py             # Postgres and pgvector
    scoring.py           # FR-13, Brier and calibration curve
  simulator/
    synthetic.py         # Mode four
    backtest.py          # Mode five
    invariants.py        # Mode two
    reference.py         # Mode three
    generator.py         # the scenario-generator agent
    scoreboard.py        # Section 7.8
    scenarios/           # the frozen scenario library
  tests/                 # Mode one deterministic fixtures
  cli.py                 # the v0 runner
```

---

## 10. Data and privacy posture

The deployment axis that matters for the target market is data sensitivity, and it should be designed for from the start even though v0 runs locally. The spectrum runs from multi-tenant managed service, to a single-tenant private instance, to fully on-premise or air-gapped with self-hosted open models. Intelligence-adjacent, defense, and financial buyers will push down this spectrum, and some will refuse any third-party model touching their data. The clean model interface in Section 9.1 is what makes serving the whole spectrum possible without forking the pipeline.

---

## 11. Milestones

The build order follows Appendix A, Section 15, with the simulator brought forward so testing begins at M1.

**M0, Foundations.** Repository scaffold, the model-client interface and tier routing, the assessment schema, configuration, and the Postgres and pgvector store. No reasoning yet.

**M1, Reasoning core and synthetic simulator. This is the testing-start gate.** Hypothesis generation, the matrix, diagnosticity scoring, disconfirmation testing, and the confidence model, on the pricing decision type, with graded inputs hand-fed. Shipped together with the deterministic fixtures, the invariant suite, and the synthetic-scenario engine, so the core is testable the moment it exists. A passing M1 is the first defensible proof of the thesis.

**M2, Processing front end.** Intake and source typing, clustering, and the corrected grading with relay collapse and weak-signal handling. The simulator can now inject closer-to-raw signal streams rather than pre-graded evidence.

**M3, Adversarial review and the gap loop.** The red-team agent with genuine blocking authority, and the assumptions-and-gap check that emits collection requirements. The R16 invariant test becomes meaningful here.

**M4, Expression and synthesis.** The ICD 203 likelihood lexicon, and synthesis into the full assessment object with the BLUF and the watch list carrying resolution criteria.

**M5, Calibration and the full scoreboard.** The calibration store and outcome logging, the Brier and calibration-curve scoring broken down per segment, the backtest engine, and the scenario-generator agent. The layer can now prove it is any good rather than assert it.

**M6, Ensemble and shadow.** Parallel analysts with aggregation and the disagreement signal, per-decision-type calibration tuning, and shadow operation beside a human or an incumbent tool ahead of any rollout.

---

## 12. Risks and open questions

The hardest part to demo is better analysis, since alerts are tangible and judgment is not, which is a sales risk more than a build risk and is the reason the published calibration claim from M5 matters so much. Incumbents can bolt on an analysis feature, so the defense is depth of method and auditable reasoning that a bolt-on cannot fake, plus the compounding record of graded, scored judgments. The acceptance thresholds in Section 7.9 are genuinely open and should be set against the base rate of the pricing decision type before M1 is graded. Lookahead leakage in backtesting is a standing hazard that the Section 7.5 defenses mitigate but do not eliminate, which is the deeper reason synthetic scenarios carry most of the testing weight.

---

## 13. Definition of done for v0

The v0 is done when the pricing-move reasoning core runs end to end on a hand-fed event and emits a schema-valid assessment, the deterministic fixtures and the full invariant suite pass on every run, the synthetic-scenario engine can author ground truth and score the pipeline against it across the four behaviors that matter, and the scoreboard reports a calibration curve, a Brier score, and resolution per segment over the seed scenario library. At that point the layer is not a product, but it is a testable, self-scoring proof of the one thing no incumbent has built.

---
---

# Appendix A: The Analysis Layer Methodological Guide

**Status:** Foundational reference. This is the canonical doctrine the build implements.
**Scope:** The analysis layer only. Collection, storage, and presentation sit outside it.
**Premise:** The layer automates the judgment of a senior intelligence analyst, not the clipping work of a junior one. Everything below exists to make that judgment disciplined, auditable, and scoreable against reality.

## A0. Purpose, scope, and contract

The analysis layer is a judgment engine. It receives raw signals and produces decision-ready, confidence-scored, auditable assessments. It is deliberately tool-agnostic: it sits on top of any collection source, which means it can be sold even to a team already paying for a collection tool that only gives them noise.

**Input contract.** A stream of signals, each carrying provenance (origin, URL or handle, timestamp, capture method) and the decision or Priority Intelligence Requirement (PIR) it was collected against.

**Output contract.** An assessment object: a structured, decision-ready analytic product carrying a leading judgment, an explicit likelihood, a separate confidence rating, the reasoning and graded evidence behind both, the rejected alternatives, the assumptions, the open gaps, and a forward-looking watch list. The full schema is in Section A10.

**What the layer is not.** It is not a collection engine, not a dashboard, not a search box, and not a substitute for the decision-maker. It does not recommend business strategy. It produces graded assessments that a human acts on. Keeping this boundary sharp is what keeps the product honest and defensible.

**The one reason this is worth building.** The intelligence literature spends fifty years lamenting two things: analysts skip rigorous technique because it is laborious, and the human mind cannot hold many hypotheses against much evidence at once (the cited working limit is that four variables are hard and five are nearly impossible to juggle simultaneously). A model has neither constraint. It can run the full discipline on every event, hold the entire hypothesis-by-evidence grid in working state, and never tire or anchor out of fatigue. The layer's whole value proposition is executing the tradecraft that humans know they should do and rarely can.

## A1. First principles

These are the non-negotiable beliefs the layer rests on. Every design rule in Section A12 traces back to one of them.

**Intelligence is reasoned judgment under irreducible uncertainty.** If something were established fact, it would not require analysis. The output is never certainty; it is a calibrated belief with its reasoning exposed.

**Bias is structural, not a character flaw.** Any reasoner, human or model, simplifies under incomplete information and jumps to the first coherent explanation. Heuer's central claim holds for models too: these mindsets cannot be willed away, only managed by process. The layer manages them by forcing structure, not by trusting the reasoner to be neutral.

**The unit of value is a judgment, not a signal.** A change detected is not intelligence. A graded, reasoned, decision-ready assessment is. The layer's job begins exactly where collection ends.

**Diagnosticity beats volume.** Past the point where there is enough to form a judgment, more information generally raises confidence without raising accuracy (Heuer). The layer therefore treats information value as a function of how well an item discriminates between live hypotheses, not how much of it there is.

**Disconfirmation beats confirmation.** The most probable hypothesis is usually the one with the least evidence against it, not the one with the most evidence for it (Heuer). The engine is built to attack hypotheses, especially the favored one, not to accumulate support for them.

**Two uncertainties, never conflated.** The likelihood of an event and the analyst's confidence in the judgment are different quantities (ICD 203). A high-likelihood call can rest on a thin, fragile evidentiary base, and a low-likelihood call can be held with high confidence. The output keeps them separate by construction.

**Every judgment must be auditable, and ultimately scoreable.** A confidence number that cannot be expanded into its drivers is marketing. A forecast that is never checked against what actually happened cannot be trusted. The layer exposes its reasoning on every assessment and scores itself against resolved outcomes over time.

## A2. The intelligence cycle as the layer's spine

The classical cycle runs direction, collection, processing, analysis, dissemination. The layer owns processing and analysis, owns the dissemination contract, and drives direction by emitting requirements back to collection.

The critical inheritance is that evaluation belongs in processing: collected information is never accepted at face value. The critical inversion from commercial practice is that the cycle is decision-anchored, not competitor-anchored. The operator does not configure a list of competitors to watch. The operator declares the decisions they are trying to make, expressed as PIRs (a pricing move, a market entry, a churn defense, an acquisition watch). Collection is then driven by those requirements, and the analysis layer is the part that decides which incoming signals actually bear on a live decision.

This single choice kills over-collection at the root, because nothing is gathered or assessed except against a requirement, and it gives every assessment a decision to attach to, which is what makes it actionable rather than interesting.

## A3. The analytic pipeline

This is the heart of the layer: a fixed, ordered sequence of stages. The discipline is the point. The engine must not be able to emit a judgment that skipped grading, hypothesis testing, or adversarial review. A generic model asked "what does this competitor move mean" skips all of these. The pipeline makes skipping structurally impossible.

Each stage below names its purpose, its method, its lineage, its dominant failure mode, and the design rule it enforces.

### A3.1 Intake and normalization

**Purpose.** Turn a raw signal into a typed evidence item with full provenance.

**Method.** Capture origin, capture method, timestamp, and the PIR reference. Critically, classify the source's structural type at intake, because the corrected evaluation model in Section A4 depends on it: is the source primary (first-hand) or relaying (repeating someone else's claim), and is it subjective (a human assertion) or objective (a sensor, a filing, a price page, a logged fact).

**Failure mode.** Treating a relay as a source. Ten outlets repeating one wire story is one source, not ten, and a layer that misses this manufactures false corroboration.

### A3.2 Event clustering and deduplication

**Purpose.** Collapse the many signals describing one underlying event into a single thing to assess. The unit of analysis is an event tied to a PIR, never an individual alert.

**Method.** Cluster signals by referent event, link them to the PIR they bear on, and carry the full set of underlying items as the evidence base for that event. Most of the noise in the system dies here, before any reasoning is spent.

**Failure mode.** Assessing the same event five times because it arrived through five channels, or splitting one event into fragments too small to reason about.

### A3.3 Source and information evaluation

**Purpose.** Grade the quality of what is known before reasoning on it.

**Method.** Apply the corrected two-axis model from Section A4: source reliability (about the source) and information credibility (about the item), kept genuinely independent, with relays collapsed so that echo is not counted as corroboration, and with weak-signal protection so a high-reliability anomaly is not silently buried for lacking corroboration.

**Lineage and deviation.** Inherits the Admiralty (NATO) code. Deviates deliberately from it on four documented defects, detailed in Section A4.

### A3.4 Hypothesis generation

**Purpose.** Produce the full set of plausible explanations and outcomes before weighing evidence.

**Method.** Generate a hypothesis set that is as close to mutually exclusive and collectively exhaustive as the question allows. The set must always include the mundane or null hypothesis (nothing meaningful is happening), and, where deception is possible, an explicit hypothesis that the signal is planted or misleading. Generating hypotheses before scoring evidence is what prevents the engine from anchoring on the first coherent story.

**Lineage.** Heuer's Analysis of Competing Hypotheses, step one, and structured brainstorming from the Pherson techniques.

**Failure mode.** Too few hypotheses, or a set that quietly omits the explanation the operator would least like to be true.

### A3.5 Evidence-hypothesis matrix and diagnosticity scoring

**Purpose.** Make the relationship between every piece of evidence and every hypothesis explicit, and identify which evidence actually discriminates.

**Method.** Build the ACH matrix with hypotheses across the top and evidence down the side. For each cell, assess whether the item is consistent, inconsistent, or not applicable to that hypothesis. Then score each item's diagnosticity: an item consistent with every hypothesis discriminates nothing and is near-worthless, regardless of how striking it is; an item that is inconsistent with some hypotheses and consistent with others is diagnostic and carries the weight. This is the stage where the machine's lack of a working-memory limit matters most, because it can hold the whole grid that a human cannot.

**Lineage.** Heuer, ACH steps two and three, and the concept of diagnosticity.

**Failure mode.** Letting vivid but non-diagnostic evidence drive the conclusion.

### A3.6 Hypothesis testing and updating

**Purpose.** Reach a leading judgment by elimination, and update it correctly as evidence arrives.

**Method.** Work down the matrix trying to disprove hypotheses, focusing on inconsistency. The surviving hypothesis is the one with the least diagnostic evidence against it, which becomes the leading judgment. Rejected hypotheses are kept and ranked, each with the reason it was set aside. Updating follows a Bayesian posture detailed in Section A6: start from base rates, update proportionally to the diagnostic weight of new evidence, and avoid both anchoring (under-updating) and over-reaction (over-updating).

**Lineage.** Heuer for the disconfirmation logic; Tetlock for the updating discipline.

**Failure mode.** Confirmation drift, where the engine accumulates support for the first hypothesis and discounts what contradicts it.

### A3.7 Key assumptions check and gap identification

**Purpose.** Surface what the judgment silently depends on, and turn ignorance into action.

**Method.** Enumerate the assumptions the leading judgment rests on and rate each for fragility (how much the judgment would change if the assumption were wrong). Then identify the gaps: what would need to be known to raise confidence. Emit those gaps as fresh collection requirements, which closes the loop back to direction. The layer does not merely consume signals; it tells the collection side what to go find next.

**Lineage.** The Key Assumptions Check from the Pherson techniques.

**Failure mode.** Treating a load-bearing assumption as an established fact.

### A3.8 Adversarial review

**Purpose.** Attack the leading judgment before it ships.

**Method.** A dedicated red-team pass argues that the leading hypothesis is wrong, runs the bias catalog from Section A9 (confirmation, anchoring, mirror-imaging the competitor as if they reason like you, vividness, availability), checks whether a single source is carrying too much of the conclusion, and checks whether the deception hypothesis was given fair weight. A successful challenge does one of two things: it downgrades confidence, or it routes the event back for more collection before anything is emitted. This is skepticism engineered into the machine rather than left to a tired human.

**Lineage.** Devil's Advocacy, Red Team Analysis, and Premortem from the Pherson techniques.

**Failure mode.** A rubber-stamp red team that always agrees. The challenge must be able to actually block a release.

### A3.9 Confidence computation

**Purpose.** Compute, not assert, how much to trust the judgment.

**Method.** Combine the explicit factor set in Section A8 (evidence grade, breadth of independent corroboration, how decisively the leading hypothesis beat the alternatives, assumption fragility, and coverage of the question) into a confidence rating with a numeric band. Every confidence value must expand to show these drivers.

**Lineage.** The analytic-confidence tradition (Mercyhurst and related work), which holds that confidence rests on the logic and evidentiary base, not on the strength of the claim.

**Failure mode.** Confidence that tracks how dramatic the conclusion sounds rather than how well-supported it is.

### A3.10 Likelihood expression

**Purpose.** State how probable the event or judgment is, in language that means the same thing to every reader.

**Method.** Use the ICD 203 lexicon with its numeric bands (Section A7), show the number alongside the word, and never put a likelihood and a confidence level in the same sentence. Likelihood and confidence are reported as two separate fields.

**Lineage.** Kent's words of estimative probability; ICD 203; the empirical finding that bracketing the number next to the word roughly doubles correct interpretation.

**Failure mode.** A bare verbal term ("likely") that different readers silently price anywhere from coin-flip to near-certain.

### A3.11 Synthesis into the assessment object

**Purpose.** Produce the decision-ready product.

**Method.** Emit the assessment in BLUF form (the bottom line first, in one decision-ready sentence), followed by key judgments, graded evidence, the hypothesis set with statuses, assumptions, gaps, the likelihood and confidence fields, a recommended action framed as a decision input rather than a strategy directive, and an indicators-and-warning watch list. The watch list is what makes the layer predictive rather than a rearview mirror: it names, in advance, the specific future signals that would confirm or break the call, and each of those becomes a monitored requirement.

**Lineage.** BLUF writing convention; Indicators and Signposts of Change from the Pherson techniques.

### A3.12 Dissemination and decision-moment routing

**Purpose.** Put the assessment where the decision is made, at the moment it is made.

**Method.** Route the assessment to the decision owner in the surface where they already work, keyed to the PIR. Intelligence that lands in a dashboard nobody reads is wasted. Distribution is part of the analytic product, not an afterthought.

**Failure mode.** Correct analysis, delivered to the wrong place or after the decision window closed.

### A3.13 Outcome logging and calibration

**Purpose.** Close the loop so the layer can prove it is any good and get better.

**Method.** Every assessment carries a resolvable claim and a resolution criterion drawn from its watch list. When reality resolves the claim, log the outcome, score the forecast (Section A11), and feed the result back into the confidence model. Capture human overrides as signal. The accumulating record of graded judgments, outcomes, and corrections is the layer's compounding proprietary asset.

## A4. Source and information evaluation (deep dive)

This is where standard practice is most wrong and where domain expertise matters most, so it gets its own treatment.

### A4.1 The baseline

The Admiralty (NATO) code, formalized in AJP-2.1 and the relevant STANAGs, evaluates each item on two axes during the processing stage.

| Source reliability | Information credibility |
| --- | --- |
| A: Completely reliable | 1: Confirmed by other independent sources |
| B: Usually reliable | 2: Probably true |
| C: Fairly reliable | 3: Possibly true |
| D: Not usually reliable | 4: Doubtful |
| E: Unreliable | 5: Improbable |
| F: Reliability cannot be judged | 6: Credibility cannot be judged |

Reliability is about the source (its track record, competence, and access). Credibility is about the item (its plausibility and corroboration). The note on F matters: it does not mean untrustworthy, only that there is no basis to judge, for example a source with no reporting history.

### A4.2 The four defects, and the fixes

A naive implementation of this code inherits four well-documented failures. The layer fixes each.

**Defect one: the two axes are not independent in practice.** Raters are told to score reliability and credibility separately, but empirical work found roughly 87 percent of ratings fall on the diagonal (A1, B2, C3), meaning judgment of credibility bleeds into judgment of reliability. *Fix:* score the axes in separate stages with separate inputs, and explicitly permit and surface off-diagonal grades. The engine must be able to emit and act on an A4 (a highly reliable source reporting something currently doubtful) rather than quietly collapsing it.

**Defect two: weak signals are suppressed.** Because credibility is driven by corroboration and consistency with what is already known, a reliable source reporting something that does not fit the prevailing picture scores low on credibility, the rating collapses toward that low number, and the early-warning signal is buried. This is the exact mechanism behind intelligence surprises. *Fix:* a high-reliability source reporting an uncorroborated, inconsistent claim is treated as a live weak signal. It is not downgraded into silence; it is escalated as a gap and routed to the watch list and to collection. Lack of corroboration becomes a reason to look harder, not a reason to dismiss.

**Defect three: no distinction between source types.** The code was built for human intelligence and does not separate primary sources from secondary or relaying ones, or subjective human sources from objective sensors. *Fix:* source type is captured at intake (Section A3.1) and used everywhere downstream. A primary first-hand source and an outlet relaying it are scored differently, and relays are collapsed in the corroboration graph so that echo across many relays of one origin counts as one source, not many.

**Defect four: the code masks uncertainty rather than exposing it.** A two-character grade gives a false sense of rigor and is applied inconsistently. *Fix:* the grade is an auditable input to confidence, never a precise output. The reasoning behind each grade is recorded and surfaced, so a reader can see why a source was rated as it was.

### A4.3 The corrected model in one paragraph

Reliability is assessed from the source's track record, competence, and access, independent of the current item. Credibility is assessed from the item's internal plausibility and its corroboration by genuinely independent sources, where independence is established by collapsing relays to their origin. Source type (primary or relaying, subjective or objective) modifies both. A high-reliability source making an uncorroborated, surprising claim is never silently dismissed; it is flagged as a weak signal and converted into a collection requirement. Every grade carries its rationale. The resulting evidence weight feeds the diagnosticity matrix in Section A3.5.

### A4.4 Deception

Reliability and credibility must stay separate precisely because a reliable source can be a conduit for planted information. A trusted channel deliberately fed false material is reliable and not credible at the same time, and only a two-axis model that keeps the axes independent can represent that. Where the operating environment makes deception plausible, the deception hypothesis is mandatory in Section A3.4 and is specifically checked in the red-team pass.

## A5. Hypothesis discipline (deep dive)

Analysis of Competing Hypotheses is the reasoning core, so its operationalization is specified here.

**The procedure.** ACH is an eight-step method: identify the full hypothesis set; list the significant evidence and arguments for and against each; build the evidence-by-hypothesis matrix; refine the matrix and reconsider the hypotheses; draw tentative conclusions by trying to disprove hypotheses rather than prove them; analyze how sensitive the conclusion is to the few most diagnostic items; report all hypotheses with their relative likelihoods, not just the leading one; and identify the future indicators that would change the judgment.

**Generating a good hypothesis set.** A weak set is the most common way the whole method fails. The set must be as mutually exclusive and collectively exhaustive as the question allows, must include the mundane or null hypothesis, and, where relevant, must include a deception hypothesis. For complex questions, decompose the question into simpler sub-questions and run the procedure on each, then recombine (the structured variant of ACH).

**Diagnosticity is the central idea.** Evidence that is consistent with every hypothesis tells you nothing about which is true, no matter how attention-grabbing it is. The conclusion must be driven by the items that discriminate. The engine ranks evidence by diagnostic value, not by volume or vividness.

**The disconfirmation rule.** The engine seeks evidence that would break hypotheses, and the leading judgment is the hypothesis left with the least diagnostic evidence against it. Seeking disconfirmation does not come naturally to any reasoner, which is why it is enforced by the pipeline rather than left to the model's instinct.

**Pitfalls to design against.** Anchoring on the first plausible hypothesis; satisficing on a good-enough explanation before the alternatives are tested; and quietly dropping the hypothesis the operator would find most unwelcome.

## A6. Updating: how information changes the output (deep dive)

This section specifies the single most important behavior: what the layer does when a new piece of information arrives.

**Start from the outside view.** Before weighing the specifics, anchor on the base rate: how often does this kind of event or outcome occur in general. Specific evidence then moves the judgment away from the base rate in proportion to its diagnostic weight. Starting from base rates is one of the few mechanical habits that separates accurate forecasters from inaccurate ones.

**Update Bayesianly, and proportionally.** Each diagnostic item updates the belief across the hypothesis set. The discipline is to update a lot but not too much: accurate forecasting requires frequent updating, while over-updating on each new headline is its own failure. The engine moves the posterior by an amount tied to the item's diagnosticity and source grade, not by the item's emotional salience.

**Enforce the diagnosticity gate and a stopping rule.** Because more information past a threshold buys confidence rather than accuracy, the engine does not treat additional non-diagnostic corroboration as progress. It asks of every new item whether it discriminates between live hypotheses. If it does not, it is logged but does not move the judgment, and the appetite for further raw collection on that event is capped. The trigger for more collection is a diagnostic gap, identified in Section A3.7, not a desire for more volume.

**Represent ignorance honestly.** Not knowing is different from believing the odds are even. A question with almost no relevant evidence is a state of high ignorance, which must be reflected as low confidence, and must not be laundered into a confident-looking fifty-fifty. The output keeps "we do not have enough to say" as a first-class possible result, expressed as low confidence with the gaps named.

## A7. Uncertainty expression (deep dive)

How the judgment is stated is part of the analysis, not packaging. Two readers who price the same words differently have not received the same assessment.

**The two-axis output.** Every assessment reports two separate things. Likelihood is the probability of the event or judgment. Confidence is how much to trust that the likelihood is right, given the evidence and reasoning. They are different quantities and are reported in different fields. A high-likelihood judgment on a thin base, and a low-likelihood judgment held firmly, are both coherent and both common.

**The likelihood lexicon.** Use the ICD 203 standard terms with their numeric bands, and do not mix terms across the scale within one product.

| Term | Probability band |
| --- | --- |
| Almost no chance | 01 to 05 percent |
| Very unlikely | 05 to 20 percent |
| Unlikely | 20 to 45 percent |
| Roughly even chance | 45 to 55 percent |
| Likely | 55 to 80 percent |
| Very likely | 80 to 95 percent |
| Almost certain | 95 to 99 percent |

**Always show the number with the word.** Verbal terms alone are read inconsistently. In controlled testing, correct interpretation of these terms rose from about 32 percent to about 66 percent simply by bracketing the numeric range next to the word in the text. The layer always renders the band alongside the term. This resolves the old "poets versus mathematicians" tension in favor of doing both at once.

**Keep likelihood and confidence in separate sentences.** ICD 203 forbids combining a confidence level and a degree of likelihood in the same sentence, because doing so blurs two distinct ideas into one ambiguous claim. The schema enforces the separation structurally by giving them separate fields.

**Expose the basis, do not just stamp a label.** There is a live academic critique that confidence labels are poorly defined and routinely conflated with likelihood, and that analysts would do better to explain the nature and strength of the evidence directly. The layer honors both positions: it reports a confidence rating for scannability, and it always exposes the evidentiary basis behind that rating, so the label never stands alone.

## A8. The confidence model (specification)

Confidence is computed from an explicit, auditable factor set, then mapped to a band. The factors are scored per assessment and stored so the value can be expanded into its drivers on demand.

**Factor one: evidence grade.** The aggregate source-reliability and information-credibility of the diagnostic evidence, after the corrections in Section A4. Thinly graded evidence caps confidence regardless of the other factors.

**Factor two: independent corroboration.** The number of genuinely independent sources supporting the leading judgment, counted after relays are collapsed. Echo does not count.

**Factor three: hypothesis margin.** How decisively the leading hypothesis beat the next-best alternative in the diagnosticity matrix. A narrow margin means the alternatives are live and confidence is lower, even if the evidence is otherwise good.

**Factor four: assumption fragility.** How much the judgment would change if its load-bearing assumptions were wrong. Fragile assumptions lower confidence.

**Factor five: coverage of the question.** How much of what would ideally be known is actually known. Large unfilled gaps lower confidence and are named in the output.

**Combination and mapping.** The factors combine into a high, moderate, or low confidence rating, each tied to an internal numeric band so the rating can be calibrated against outcomes over time (Section A11). The combination is conservative: a single severe weakness (very thin evidence, a near-tie between hypotheses, a fragile core assumption, or a large coverage gap) is sufficient to cap the rating low, because confidence should reflect the weakest link in the reasoning, not the average. The exact weighting is itself a tunable parameter, refined empirically as calibration data accumulates rather than fixed by intuition.

## A9. Adversarial review and bias control (deep dive)

The red-team pass in Section A3.8 runs a fixed catalog of checks. Each check can downgrade confidence or block release and route the event back for collection.

**Confirmation.** Was contradicting evidence discounted or explained away rather than weighed? Was disconfirmation actually sought, or only support accumulated?

**Anchoring.** Did the judgment lock onto the first plausible hypothesis, with later evidence bent to fit it?

**Mirror-imaging.** Was the competitor's likely behavior inferred from how the operator would act, rather than from how that competitor actually behaves? This is among the most damaging errors in competitive analysis specifically.

**Vividness and availability.** Did a dramatic or recent item drive the conclusion beyond its diagnostic weight?

**Single-source dependency.** Does the conclusion collapse if one source is removed? If so, confidence is capped and the dependency is flagged.

**Single-hypothesis fixation.** Were genuine alternatives generated and tested, or was the matrix a formality around a predetermined answer?

**Deception.** Where deception is plausible, was the planted-information hypothesis given fair weight, or waved off?

**Ensemble disagreement.** Where the layer runs multiple model analysts (Section A11), material disagreement among them is itself a signal that confidence should be lower, and the disagreement is surfaced rather than averaged away.

The rule that makes this real: the red team must be able to stop a release. A challenge that can only annotate but never block is theater.

## A10. The assessment object (schema)

This is the structured product the layer emits and the contract every consumer and downstream system builds against.

```
assessment {
  id
  pir_ref                       // the decision this serves
  created_at
  bluf                          // one-sentence, decision-ready bottom line

  likelihood {
    term                        // ICD 203 lexicon term
    probability_band            // numeric band, always rendered with the term
  }

  confidence {
    level                       // high | moderate | low
    band                        // internal numeric band, for calibration
    drivers {
      evidence_grade
      independent_corroboration
      hypothesis_margin
      assumption_fragility
      question_coverage
    }
  }

  key_judgments[]

  evidence[] {
    content
    source_reliability          // A to F, about the source
    information_credibility     // 1 to 6, about the item
    source_type                 // primary | relaying ; subjective | objective
    origin_id                   // relays collapse to a shared origin
    provenance { url_or_handle, captured_at, capture_method }
    diagnostic_value            // discriminating power across hypotheses
    grade_rationale             // why it was graded this way
  }

  hypotheses[] {
    statement
    status                      // leading | rejected | live-alternative
    rationale                   // why leading, or why set aside
    relative_likelihood
  }

  assumptions[] {
    statement
    fragility                   // how much the judgment moves if this is wrong
  }

  gaps[]                        // emitted as new collection requirements

  indicators_watch[] {
    indicator                   // a specific future signal
    direction                   // confirms | breaks the leading judgment
    resolution_criterion        // what counts as resolved, for scoring
  }

  recommended_action            // framed as a decision input, not a strategy directive

  red_team {
    checks_run[]
    challenges_raised[]
    outcome                     // passed | confidence-downgraded | returned-for-collection
  }

  human_overrides[]             // analyst edits, captured as signal

  calibration {
    resolvable_claim
    status                      // open | proved_out | disproved
    brier_contribution          // populated on resolution
  }
}
```

## A11. Validation and calibration (deep dive)

This is the part no incumbent has, and it is what turns a clever demo into something a buyer can trust. It rests on the empirical forecasting tradition rather than the structured-technique tradition, and the two are fused here on purpose: the techniques give transparency and bias control, calibration proves the output is accurate.

**Score every resolvable judgment.** Each assessment carries a resolvable claim and a resolution criterion drawn from its watch list. When reality resolves it, the probabilistic forecast is scored with a Brier score, the standard measure of probabilistic accuracy, where lower is better. The Brier score decomposes into calibration (when the layer says seventy percent, does it happen about seventy percent of the time) and resolution (does the layer make decisive, differentiated calls rather than hugging fifty percent).

**Publish the calibration curve.** Over many resolved judgments, plot stated probability against observed frequency. A well-calibrated layer sits on the diagonal. This lets the product make a measured claim ("when this layer says high confidence, it has proved out at this rate") rather than an unfalsifiable marketing claim, which is the entire trust differentiator.

**The resolution problem is a design constraint, not an afterthought.** A judgment can only be scored if it was stated in a resolvable way, which is why the watch list requires explicit resolution criteria at synthesis time. Vague judgments are unscoreable and therefore untrustworthy by construction. The layer is biased toward claims specific enough to be proved wrong.

**Aggregate across model analysts.** Running several model analysts and aggregating their judgments improves accuracy, which is the empirical wisdom-of-crowds result from large forecasting tournaments, where aggregated forecasts beat individual ones and trained forecasters using systematic methods outperformed expert analysts with privileged access. A multi-agent design is therefore not a stylistic choice; it has measured accuracy benefits. Disagreement among the analysts is preserved as a confidence signal rather than averaged into false consensus.

**Tune confidence from outcomes.** Calibration data flows back into the confidence model in Section A8. If the layer is systematically overconfident in a given decision type or with a given class of source, the weighting is corrected from the data, not from intuition. Calibration is tracked per decision type and per source class, because the layer may be well-calibrated on pricing moves and poorly calibrated on, say, partnership rumors, and those should be corrected independently.

**The compounding asset.** The accumulating store of graded judgments, the outcomes they resolved to, and the human overrides that corrected them is the proprietary moat. Incumbents can copy the interface. The disciplined, scored, auditable judgment record is far harder to replicate, and it makes every subsequent assessment sharper.

## A12. Design rules and invariants

These are the hard rules the build is checked against. Each names the principle or source it inherits from, and the deviation from standard practice where one applies.

**R1. Decision-anchored collection.** Nothing is assessed except against a declared PIR. *From:* the direction phase of the intelligence cycle. *Deviation:* commercial tools are competitor-anchored; this is decision-anchored.

**R2. The unit of analysis is an event tied to a PIR, never a raw alert.** *From:* first principles. Clustering precedes all reasoning.

**R3. No judgment may skip grading, hypothesis testing, or adversarial review.** The pipeline order is enforced; the engine cannot emit an assessment that bypassed a stage. *From:* Heuer, that structure manages bias that willpower cannot.

**R4. Source reliability and information credibility are scored independently and may be off-diagonal.** *From:* the Admiralty code. *Deviation:* corrects the empirical collapse of the two axes onto the diagonal.

**R5. A high-reliability source making an uncorroborated, surprising claim is escalated as a weak signal, never silently downgraded.** *From:* the Irwin and Mandel critique. *Deviation:* corrects the corroboration bias that buries early warning.

**R6. Relays are collapsed to their origin; echo is not corroboration.** *From:* the primary-versus-relaying critique. Especially load-bearing for open-source and social-media inputs.

**R7. The hypothesis set must include the null hypothesis, and a deception hypothesis where deception is plausible.** *From:* ACH, step one, and deception handling.

**R8. Evidence is weighted by diagnosticity, not by volume or vividness.** Evidence consistent with all hypotheses is near-worthless. *From:* Heuer, diagnosticity.

**R9. The leading judgment is the hypothesis with the least diagnostic evidence against it, reached by disconfirmation.** *From:* Heuer.

**R10. Updating starts from base rates and is proportional to diagnostic weight: a lot, but not too much.** *From:* Tetlock.

**R11. More non-diagnostic information does not move the judgment, and a diagnostic gap, not a desire for volume, is the only trigger for more collection.** *From:* Heuer, that information past a threshold buys confidence, not accuracy.

**R12. Ignorance is reported as low confidence with named gaps, never laundered into a confident fifty-fifty.** *From:* first principles on honest uncertainty.

**R13. Likelihood and confidence are separate fields and never combined in one sentence.** *From:* ICD 203.

**R14. Likelihood uses the ICD 203 lexicon with the numeric band always rendered beside the term.** *From:* Kent and the empirical comprehension finding.

**R15. Confidence is computed from the explicit factor set and always expandable to its drivers; it is capped by its weakest link.** *From:* the analytic-confidence tradition.

**R16. The red team can block a release, not merely annotate it.** *From:* Devil's Advocacy and Premortem.

**R17. Every assessment carries a resolvable claim and a resolution criterion, and is scored against outcomes.** *From:* Tetlock and Brier scoring.

**R18. Where multiple model analysts run, their judgments are aggregated and their disagreement is preserved as a confidence signal.** *From:* the wisdom-of-crowds forecasting result.

**R19. Every grade, judgment, and confidence value carries its rationale and is auditable.** *From:* the critique that information-evaluation codes mask rather than expose uncertainty.

**R20. The layer states decision inputs, never business-strategy directives, and never replaces the decision-maker.** *From:* scope discipline.

## A13. Anti-patterns

The behaviors the layer must never exhibit, stated plainly so they can be tested for.

Shipping a single confident guess with no alternatives. Counting echo across many relays as corroboration. Letting absence of corroboration bury a high-reliability anomaly. Conflating likelihood and confidence. Asserting a confidence level without exposing its basis. Treating additional non-diagnostic volume as analytic progress. Skipping the red team on an event that looks obvious, since the obvious events are exactly where mirror-imaging and confirmation do their damage. Producing a judgment too vague to be proved wrong. Averaging away genuine disagreement among model analysts into false consensus. Recommending what the business should do rather than what is likely to be true.

## A14. Implementation notes

The pipeline maps cleanly onto a multi-agent architecture, where the stages of Section A3 become specialized roles operating on shared, explicit state.

The evidence-by-hypothesis matrix is held as explicit, inspectable state, not as something implied inside a single model call. This is what lets the system reason over more hypotheses and evidence than a human can, and it is what makes the reasoning auditable after the fact.

Distinct roles handle generation, grading, matrix construction and diagnosticity scoring, hypothesis testing, the assumptions and gap check, and the adversarial review, with the red-team role given genuine authority to downgrade or return an assessment. Several analyst roles can run in parallel and have their judgments aggregated, which is both the wisdom-of-crowds accuracy benefit and a natural source of the disagreement signal.

Outputs are produced as structured objects matching the Section A10 schema, so they are machine-consumable for routing and for the calibration store. Human overrides are captured as structured signal rather than discarded, because the corrections are training data for the confidence model and part of the compounding asset.

The calibration store is the system of record for outcomes and scores, and it is queried both to tune confidence and to generate the published calibration claims.

## A15. Build order

Build the reasoning core first, because it is the part nobody else has and the part that proves the entire thesis in a demo. That means the hypothesis-by-evidence matrix, diagnosticity scoring, disconfirmation-based testing, and the computed confidence model, running on one decision type, with graded inputs hand-fed or lightly mocked. A working version of just this is already differentiated.

Add the corrected source-and-information evaluation next, since clean grading is what feeds diagnosticity, and the relay-collapse and weak-signal handling are where the open-source domain expertise shows.

Add the adversarial review and the assumptions-and-gap loop after that, because they are what turn a clever demo into something a buyer trusts, and they generate the collection requirements that make the layer feel alive rather than static.

Add outcome logging and calibration last in sequence but treat it as essential, not optional, because the published calibration claim is the durable trust moat and the data it produces tunes everything upstream.

## A16. Lineage

The doctrine above inherits from a specific body of work. The structured-judgment tradition: Sherman Kent, who established intelligence analysis as a discipline and, in "Words of Estimative Probability" (1964), framed the problem of communicating uncertainty; Richards Heuer, whose "Psychology of Intelligence Analysis" (1999) supplies the cognitive-bias frame and Analysis of Competing Hypotheses; and Richards Heuer with Randolph Pherson, whose "Structured Analytic Techniques for Intelligence Analysis" codifies the techniques the pipeline automates. The source-evaluation tradition: the Admiralty or NATO code as formalized in AJP-2.1 and the STANAGs, read together with its critics, including Baker and colleagues on the non-independence of the two axes, and Irwin and Mandel on weak-signal suppression and the limits of information-evaluation schemes. The doctrinal standard for expressing judgment: Intelligence Community Directive 203, "Analytic Standards" (first issued 2007), and its companion ICD 206 on sourcing, together with the empirical literature showing that numeric ranges rendered beside verbal terms substantially improve comprehension. The empirical-calibration tradition: Philip Tetlock and the Good Judgment Project, and the use of Brier scoring and calibration curves to measure and improve forecasting accuracy. A growing body of recent work testing how language models handle estimative-probability language and probabilistic forecasting sits directly underneath the implementation choices here, and is the bridge from this doctrine to a working system.
