import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from app.eval.metrics import (
    QuestionResult,
    ScoringReport,
    relevant_passages,
    score,
    select_passages,
)

RECALL_BAR = 0.95
NO_MATCH_BAR = 0.90
CUTOFF_K = 5
MIN_SWEEP_K = 1
MAX_SWEEP_K = 10
# Cosine distance for normalized embeddings is bounded to [0, 2]. Candidate cutoffs are
# midpoints between observed distances inside this range, so every distinct retrieval outcome
# is evaluated exactly once.
COSINE_DISTANCE_FLOOR = 0.0
COSINE_DISTANCE_CEILING = 2.0


@dataclass(frozen=True)
class CutoffLock:
    """The outcome of sweeping the relevance cutoff at ``k = 5``.

    ``margin`` is ``D - P``: the distance between the negative bound and the recall bound.
    """

    qualifies: bool
    cutoff: float | None
    report: ScoringReport | None
    margin: float | None
    reason: str | None


@dataclass(frozen=True)
class TopKLock:
    """The outcome of sweeping top-k at a locked cutoff."""

    qualifies: bool
    k: int | None
    cutoff: float
    report: ScoringReport | None
    reason: str | None


def sweep_cutoffs(
    results: Sequence[QuestionResult], k: int = CUTOFF_K
) -> tuple[ScoringReport, ...]:
    """Score every distinct retrieval outcome at the given k."""
    return tuple(score(results, k=k, cutoff=cutoff) for cutoff in _candidate_cutoffs(results))


def positive_distance(result: QuestionResult, k: int) -> float:
    """Distance of the nearest expected-Document passage when it ranks within the top k,
    using the same ordering as the scorer, or math.inf when it does not."""
    top_k = select_passages(result.passages, k=k, cutoff=COSINE_DISTANCE_CEILING)
    relevant = relevant_passages(top_k, result.expected_document)
    return min((passage.distance for passage in relevant), default=math.inf)


def negative_distance(result: QuestionResult) -> float:
    """Distance of the nearest passage for a Negative question, or math.inf when none."""
    below_ceiling = select_passages(result.passages, k=1, cutoff=COSINE_DISTANCE_CEILING)
    return below_ceiling[0].distance if below_ceiling else math.inf


def required_count(bar: float, total: int) -> int:
    """Smallest count whose rate meets the bar, using the same comparison as the scorer."""
    return next(count for count in range(total + 1) if count / total >= bar)


def margin_bounds(results: Sequence[QuestionResult], k: int) -> tuple[float, float]:
    """The recall bound P and the negative bound D at this k.

    P is the distance a cutoff must exceed to recall enough positives to meet RECALL_BAR.
    D is the nearest Negative-question distance that NO_MATCH_BAR does not allow to leak.
    Callers must have checked that both positives and Negative questions exist.
    """
    positives = sorted(positive_distance(r, k) for r in results if not r.is_negative)
    negatives = sorted(negative_distance(r) for r in results if r.is_negative)
    p_bound = positives[required_count(RECALL_BAR, len(positives)) - 1]
    allowed_leaks = len(negatives) - required_count(NO_MATCH_BAR, len(negatives))
    d_bound = negatives[allowed_leaks]
    return p_bound, d_bound


def lock_cutoff(results: Sequence[QuestionResult], k: int = CUTOFF_K) -> CutoffLock:
    """Lock the relevance cutoff using the authored bars.

    ``results`` is supplied by the caller: one ``QuestionResult`` per golden entry, carrying the
    candidate Passages and their cosine distances. This core does not embed or query; the local
    runner (#21) builds those results from the database.

    ``select_passages`` sorts by distance and keeps passages with ``distance < cutoff``, then
    takes the first k. A cutoff only removes passages farther than every passage it keeps. So a
    positive question is recalled at cutoff ``c`` exactly when its nearest expected-Document
    passage ranks within the top k with no cutoff, and that distance is below ``c``. A Negative
    question reports no match at ``c`` exactly when its nearest passage has distance ``>= c``.
    Recall and no_match are therefore simple counts over one distance per question, and the
    qualifying cutoffs form the interval ``(P, D]`` defined by ``margin_bounds``.

    The lock sits at the midpoint of that interval, rounded to 3 decimals or else 4, and both
    bars are re-scored at the returned value. When no cutoff meets both bars, the result says so
    instead of passing.
    """
    missing = _missing_expectations(results)
    if missing is not None:
        return _failed_cutoff_lock(f"Cannot lock a cutoff: {missing}.")

    p_bound, d_bound = margin_bounds(results, k)
    positive_count = sum(1 for result in results if not result.is_negative)
    unranked = sum(
        1
        for result in results
        if not result.is_negative and math.isinf(positive_distance(result, k))
    )
    if math.isinf(p_bound):
        return _failed_cutoff_lock(
            f"No cutoff reaches recall@{k} >= 95% for the authored positives: {unranked} of "
            f"{positive_count} positives do not rank their expected Document in the top {k}, "
            "so this is a ranking failure, not a cutoff failure. A human must choose an "
            "explicit fallback."
        )
    if p_bound >= d_bound:
        return _failed_cutoff_lock(
            f"No cutoff keeps Negative no_match >= 90% while reaching recall@{k} >= 95%: "
            f"recall bound P={p_bound:.4f} is not below negative bound D={d_bound:.4f} "
            f"(overlap {p_bound - d_bound:.4f}). The bars conflict, so a human must choose an "
            "explicit fallback."
        )

    mid = (p_bound + min(d_bound, COSINE_DISTANCE_CEILING)) / 2
    cutoff: float | None = None
    for decimals in (3, 4):
        value = round(mid, decimals)
        if p_bound < value <= d_bound and value < COSINE_DISTANCE_CEILING:
            cutoff = value
            break
    if cutoff is None:
        return _failed_cutoff_lock(
            f"No cutoff keeps Negative no_match >= 90% while reaching recall@{k} >= 95% at "
            f"4-decimal precision: the qualifying interval ({p_bound:.6f}, {d_bound:.6f}] is "
            "too narrow to place a 4-decimal cutoff inside it. The bars conflict, so a human "
            "must choose an explicit fallback."
        )

    margin = d_bound - p_bound
    report = score(results, k=k, cutoff=cutoff)
    if not _meets_bars(report):
        raise AssertionError(
            f"closed-form lock is wrong: P={p_bound}, D={d_bound}, cutoff={cutoff}"
        )
    return CutoffLock(qualifies=True, cutoff=cutoff, report=report, margin=margin, reason=None)


def lock_top_k(results: Sequence[QuestionResult], cutoff: float) -> TopKLock:
    """Lock the smallest k whose recall reaches 95% at the locked cutoff.

    The recall and no_match bars are re-verified at the final ``(cutoff, k)`` pair. If no k in
    the supported range reaches the recall bar, the result reports the failure.
    """
    missing = _missing_expectations(results)
    if missing is not None:
        return _failed_top_k_lock(cutoff, f"Cannot lock top-k: {missing}.")

    for k in range(MIN_SWEEP_K, MAX_SWEEP_K + 1):
        report = score(results, k=k, cutoff=cutoff)
        if report.recall < RECALL_BAR:
            continue

        if report.no_match_rate < NO_MATCH_BAR:
            return TopKLock(
                qualifies=False,
                k=None,
                cutoff=cutoff,
                report=report,
                reason=(
                    f"At k={k}, recall is {report.recall:.0%} but Negative no_match is "
                    f"{report.no_match_rate:.0%}; the bars conflict at the final pair."
                ),
            )
        return TopKLock(qualifies=True, k=k, cutoff=cutoff, report=report, reason=None)

    return _failed_top_k_lock(
        cutoff,
        f"No k in {MIN_SWEEP_K}..{MAX_SWEEP_K} reaches recall >= 95% at cutoff {cutoff}. "
        "A human must choose an explicit fallback.",
    )


def _failed_cutoff_lock(reason: str) -> CutoffLock:
    return CutoffLock(
        qualifies=False,
        cutoff=None,
        report=None,
        margin=None,
        reason=reason,
    )


def _failed_top_k_lock(cutoff: float, reason: str) -> TopKLock:
    return TopKLock(
        qualifies=False,
        k=None,
        cutoff=cutoff,
        report=None,
        reason=reason,
    )


def _missing_expectations(results: Sequence[QuestionResult]) -> str | None:
    if not any(not result.is_negative for result in results):
        return "the golden set has no positive questions, so recall cannot be measured"
    if not any(result.is_negative for result in results):
        return "the golden set has no Negative questions, so the no_match bar cannot be verified"
    return None


def _candidate_cutoffs(results: Sequence[QuestionResult]) -> tuple[float, ...]:
    distances = {passage.distance for result in results for passage in result.passages}
    bounds = sorted({COSINE_DISTANCE_FLOOR, COSINE_DISTANCE_CEILING, *distances})
    return tuple((lower + upper) / 2 for lower, upper in pairwise(bounds))


def _meets_bars(report: ScoringReport) -> bool:
    return report.recall >= RECALL_BAR and report.no_match_rate >= NO_MATCH_BAR
