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

    ``margin`` is ``best Negative passage distance - worst positive hit distance``, measured at
    the returned cutoff. It can differ from the candidate gap whose centre selected that cutoff,
    because centring may pull in farther positive hits.
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


def lock_cutoff(results: Sequence[QuestionResult], k: int = CUTOFF_K) -> CutoffLock:
    """Lock the relevance cutoff using the authored bars.

    ``results`` is supplied by the caller: one ``QuestionResult`` per golden entry, carrying the
    candidate Passages and their cosine distances. This core does not embed or query; the local
    runner (#21) builds those results from the database.

    A cutoff qualifies when recall@k on positive questions is at least 95% and at least 90% of
    Negative questions report no match. Among the qualifying cutoffs, the widest margin between
    the worst positive hit and the best Negative-question passage wins (when margins tie, the
    first, lowest candidate is kept), and the lock is placed at that margin's centre. If the
    centred cutoff loses a bar when re-scored, the uncentred candidate is kept instead. When no
    cutoff meets both bars, the result says so instead of passing.
    """
    missing = _missing_expectations(results)
    if missing is not None:
        return _failed_cutoff_lock(f"Cannot lock a cutoff: {missing}.")
    if not _negative_passages(results):
        return _failed_cutoff_lock(
            "Cannot lock a cutoff: no Negative question returned a Passage, so there is no "
            "negative distance to separate from the positive hits."
        )

    best_cutoff: float | None = None
    best_report: ScoringReport | None = None
    best_margin: float | None = None
    best_recall = 0.0
    best_no_match = 0.0

    for candidate_report in sweep_cutoffs(results, k=k):
        candidate = candidate_report.cutoff
        best_recall = max(best_recall, candidate_report.recall)
        best_no_match = max(best_no_match, candidate_report.no_match_rate)
        if not _meets_bars(candidate_report):
            continue

        worst_positive, best_negative = _margin_bounds(results, k=k, cutoff=candidate)
        if worst_positive is None or best_negative is None:
            continue

        margin = best_negative - worst_positive
        centered = _clamp_cutoff((worst_positive + best_negative) / 2)
        centered_report = score(results, k=k, cutoff=centered)
        if not _meets_bars(centered_report):
            centered = candidate
            centered_report = candidate_report

        if best_margin is None or margin > best_margin:
            best_margin = margin
            best_cutoff = centered
            best_report = centered_report

    if best_cutoff is None or best_report is None or best_margin is None:
        if best_recall < RECALL_BAR:
            reason = (
                f"No cutoff reaches recall@{k} >= 95% for the authored positives. "
                "A human must choose an explicit fallback."
            )
        elif best_no_match < NO_MATCH_BAR:
            reason = (
                f"No cutoff keeps Negative no_match >= 90% while reaching recall@{k} >= 95%. "
                "A human must choose an explicit fallback."
            )
        else:
            reason = (
                f"No cutoff satisfies recall@{k} >= 95% and Negative no_match >= 90% together. "
                "The bars conflict, so a human must choose an explicit fallback."
            )
        return _failed_cutoff_lock(reason)

    final_worst_positive, final_best_negative = _margin_bounds(results, k=k, cutoff=best_cutoff)
    final_margin = (
        final_best_negative - final_worst_positive
        if final_worst_positive is not None and final_best_negative is not None
        else best_margin
    )

    return CutoffLock(
        qualifies=True,
        cutoff=best_cutoff,
        report=best_report,
        margin=final_margin,
        reason=None,
    )


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


def _negative_passages(results: Sequence[QuestionResult]) -> list[float]:
    return [
        passage.distance for result in results if result.is_negative for passage in result.passages
    ]


def _candidate_cutoffs(results: Sequence[QuestionResult]) -> tuple[float, ...]:
    distances = {passage.distance for result in results for passage in result.passages}
    bounds = sorted({COSINE_DISTANCE_FLOOR, COSINE_DISTANCE_CEILING, *distances})
    return tuple((lower + upper) / 2 for lower, upper in pairwise(bounds))


def _margin_bounds(
    results: Sequence[QuestionResult], *, k: int, cutoff: float
) -> tuple[float | None, float | None]:
    """Return the worst selected positive hit and the best Negative-question passage."""
    negative_passages = _negative_passages(results)
    best_negative = min(negative_passages) if negative_passages else None

    worst_positive: float | None = None
    for result in results:
        if result.is_negative:
            continue
        expected = result.expected_document
        selected = select_passages(result.passages, k=k, cutoff=cutoff)
        relevant = relevant_passages(selected, expected)
        if not relevant:
            continue
        hit = max(passage.distance for passage in relevant)
        worst_positive = hit if worst_positive is None else max(worst_positive, hit)

    return worst_positive, best_negative


def _meets_bars(report: ScoringReport) -> bool:
    return report.recall >= RECALL_BAR and report.no_match_rate >= NO_MATCH_BAR


def _clamp_cutoff(cutoff: float) -> float:
    return max(COSINE_DISTANCE_FLOOR, min(cutoff, COSINE_DISTANCE_CEILING))
