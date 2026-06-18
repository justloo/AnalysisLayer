"""Infer which material outcome evidence content points to (Precondition B).

ponytail: regex keyword judge for the mock backend only. Ceiling: any phrasing
outside these patterns scores as non-diagnostic. Upgrade path: delete this module
when JUDGE_CELL uses the real model on content.
"""
from __future__ import annotations

import re
from typing import Optional

_DECEPTION_OPERATION = re.compile(
    r"\b("
    r"deliberate(?:ly)? planted|disinformation campaign|deception operation|"
    r"planted (?:feint|leak|rumor|story)|active feint|strategic deception|"
    r"false (?:entry-tier |starter )?cut story|planted price-cut|"
    r"confirmed.{0,48}planted|feint.{0,32}masking"
    r")\b",
    re.I,
)

_FORWARD_LOOKING = re.compile(
    r"\b(job opening|job posting|posted a job|posted \d+ .{0,24}roles|hiring|recruit(?:ing|ment))\b",
    re.I,
)


def describes_deception_operation(content: str) -> bool:
    """True when content explicitly names a planted feint or deception operation."""
    return bool(_DECEPTION_OPERATION.search(content))


def is_forward_looking(content: str) -> bool:
    return bool(_FORWARD_LOOKING.search(content))


def feint_target_bearing(content: str) -> Optional[str]:
    """Material move named inside deception-operation intelligence."""
    c = content.lower()
    if re.search(
        r"\b(false.{0,40}cut|cut (?:story|rumor)|price-cut rumor|planted.{0,24}cut|"
        r"cut starter|entry-tier cut)\b",
        c,
    ):
        return "price_cut"
    if re.search(r"\b(false.{0,40}increase|planted.{0,24}increase|feint.{0,32}increase)\b", c):
        return "price_increase"
    return None


def infer_bearing(content: str) -> Optional[str]:
    """Infer which material outcome the content points to, from text alone."""
    c = content.lower()

    if any(
        p in c
        for p in (
            "new entrant",
            "generically observes",
            "industry analyst note generically",
            "without naming any source",
            "speculates, without",
        )
    ):
        return None

    if describes_deception_operation(c):
        return None

    if re.search(
        r"\b(no change|unchanged|has not changed|has shown no change|stable and competitive|"
        r"pricing as stable|committed to current pricing|remains committed)\b",
        c,
    ):
        return "no_change"
    if re.search(
        r"\b(price cut|cutting price|price reduction|lower price|cheaper|price drop|"
        r"dropping from \$|cut the entry|cut its|might cut|price-cut|"
        r"cut starter|will cut.{0,20}pricing|"
        r"\d+\s*percent discount|discounts on the starter|"
        r"lower the barrier to entry|barrier to entry|"
        r"briefed on the new price|"
        r"starter tier is about to change|starter tier change|starter.*price|"
        r"about to be cut|tier is about to be cut|entry tier.*cut|"
        r"revenue-operations|entry-tier conversion)\b",
        c,
    ):
        return "price_cut"
    if re.search(
        r"\b(price increase|raising price|higher price|price lift|going up|uplift|"
        r"list-price uplift|raising prices|wholesale cost is going up|"
        r"percent higher|list pricing.{0,24}higher)\b",
        c,
    ):
        return "price_increase"
    if re.search(
        r"\b(cached.{0,30}pricing page|pricing page draft).{0,80}"
        r"(higher|uplift|instead of the current|raising|129|going up)\b",
        c,
    ):
        return "price_increase"
    if re.search(
        r"\b(cached.{0,30}pricing page|pricing page draft).{0,80}"
        r"(drop|lower|dropping|39|cheaper)\b",
        c,
    ):
        return "price_cut"
    if re.search(
        r"\b(repackag|restructur|tier restruct|bundle change|monetization change|"
        r"enterprise-grade feature|product manager,?\s+enterprise)\b",
        c,
    ):
        return "repackaging"
    return None
