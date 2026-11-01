"""How much a feature moves the score once rating gap, colour and time control are taken out."""

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from statistics import fmean, stdev

MIN_GROUP = 30
Z_95 = 1.96


@dataclass(frozen=True)
class Outcome:
    score: float
    expected: float
    stratum: str
    features: Mapping[str, bool]


@dataclass(frozen=True)
class Association:
    feature: str
    games_with: int
    games_without: int
    score_with: float
    score_without: float
    effect: float  # score points per game above or below what the ratings predict, against not having the feature
    margin: float  # half the 95% confidence interval
    p_value: float
    q_value: float = 1.0


def expected_score(rating: float, opponent_rating: float) -> float:
    return 1 / (1 + 10 ** ((opponent_rating - rating) / 400))


def adjusted_residuals(outcomes: Sequence[Outcome]) -> list[float]:
    """Score above the rating prediction, centred within each stratum."""
    by_stratum: defaultdict[str, list[float]] = defaultdict(list)
    for outcome in outcomes:
        by_stratum[outcome.stratum].append(outcome.score - outcome.expected)
    means = {stratum: fmean(values) for stratum, values in by_stratum.items()}
    return [outcome.score - outcome.expected - means[outcome.stratum] for outcome in outcomes]


def _p_value(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2))


def compare(outcomes: Sequence[Outcome], residuals: Sequence[float], feature: str) -> Association | None:
    """None when either group is too small to mean anything. Games without the feature measured are left out."""
    with_feature = [i for i, outcome in enumerate(outcomes) if outcome.features.get(feature) is True]
    without = [i for i, outcome in enumerate(outcomes) if outcome.features.get(feature) is False]
    if len(with_feature) < MIN_GROUP or len(without) < MIN_GROUP:
        return None
    residuals_with = [residuals[i] for i in with_feature]
    residuals_without = [residuals[i] for i in without]
    effect = fmean(residuals_with) - fmean(residuals_without)
    error = math.hypot(
        stdev(residuals_with) / math.sqrt(len(with_feature)), stdev(residuals_without) / math.sqrt(len(without))
    )
    return Association(
        feature=feature,
        games_with=len(with_feature),
        games_without=len(without),
        score_with=fmean(outcomes[i].score for i in with_feature),
        score_without=fmean(outcomes[i].score for i in without),
        effect=effect,
        margin=Z_95 * error,
        p_value=_p_value(effect / error) if error else 1.0,
    )


def with_q_values(associations: Iterable[Association]) -> list[Association]:
    """Benjamini-Hochberg, so that testing many habits does not manufacture findings."""
    ordered = sorted(associations, key=lambda association: association.p_value)
    adjusted: list[Association] = []
    smallest = 1.0
    for rank, association in reversed(list(enumerate(ordered, start=1))):
        smallest = min(smallest, association.p_value * len(ordered) / rank)
        adjusted.append(replace(association, q_value=smallest))
    return sorted(adjusted, key=lambda association: association.effect)


def associate(outcomes: Sequence[Outcome]) -> list[Association]:
    residuals = adjusted_residuals(outcomes)
    features = sorted({feature for outcome in outcomes for feature in outcome.features})
    found = (compare(outcomes, residuals, feature) for feature in features)
    return with_q_values(association for association in found if association is not None)
