"""FR-10, Likelihood expression (PRD A3.10, A7).

State how probable the leading judgment is using the ICD 203 lexicon, with the
numeric band always rendered beside the term (R14). Likelihood is a separate
quantity from confidence and lives in its own field; the two are never combined
in one sentence (R13). This node maps the computed posterior of the leading
hypothesis to a lexicon term.
"""
from __future__ import annotations

from analysis_layer.schema.assessment import Band, Likelihood, LikelihoodTerm
from analysis_layer.schema.state import AnalysisState

# The ICD 203 lexicon with its numeric bands (PRD A7), ordered low to high.
ICD203_BANDS = [
    (LikelihoodTerm.almost_no_chance, Band(low=0.01, high=0.05)),
    (LikelihoodTerm.very_unlikely, Band(low=0.05, high=0.20)),
    (LikelihoodTerm.unlikely, Band(low=0.20, high=0.45)),
    (LikelihoodTerm.roughly_even_chance, Band(low=0.45, high=0.55)),
    (LikelihoodTerm.likely, Band(low=0.55, high=0.80)),
    (LikelihoodTerm.very_likely, Band(low=0.80, high=0.95)),
    (LikelihoodTerm.almost_certain, Band(low=0.95, high=0.99)),
]


def term_for_probability(p: float) -> Likelihood:
    p = max(0.0, min(1.0, p))
    for term, band in ICD203_BANDS:
        if p <= band.high:
            return Likelihood(term=term, probability_band=band)
    return Likelihood(term=LikelihoodTerm.almost_certain, probability_band=ICD203_BANDS[-1][1])


def express_likelihood(state: AnalysisState) -> AnalysisState:
    leading = state.leading_hypothesis_id
    p = state.posteriors.get(leading, 0.5) if leading else 0.5
    state.likelihood = term_for_probability(p)
    return state
