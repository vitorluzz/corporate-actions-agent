"""Self-consistency aggregation.

Sampling the extractor N times yields, from the *same* samples, both the
event-type vote distribution (with entropy → P(Incerto)) and per-field agreement
(how stable each value is across samples). This is the probabilistic-classification
pillar, made provider-agnostic (no dependency on logprobs).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from app.domain.enums import EventType
from app.domain.schemas import EventTypeDistribution
from app.llm.base import RawExtraction, RawField


def normalized_entropy(probs: list[float]) -> float:
    """Shannon entropy normalized to [0,1] by the number of observed outcomes."""
    ps = [p for p in probs if p > 0]
    if len(ps) <= 1:
        return 0.0
    h = -sum(p * math.log(p) for p in ps)
    return h / math.log(len(ps))


def _norm_value(v: str | None) -> str:
    return (v or "").strip().casefold()


@dataclass
class FieldConsensus:
    name: str
    value: str | None
    agreement: float       # fraction of samples agreeing on the modal value
    self_report: float     # mean self-reported confidence for the modal value
    quote: str | None
    page: int | None
    n_present: int


@dataclass
class Consensus:
    event_type: EventTypeDistribution
    fields: list[FieldConsensus]


def aggregate(samples: list[RawExtraction]) -> Consensus:
    n = len(samples)
    if n == 0:
        return Consensus(EventTypeDistribution(argmax=EventType.INCERTO, entropy=1.0), [])

    votes = Counter(s.event_type for s in samples)
    distribution = {t: c / n for t, c in votes.items()}
    entropy = normalized_entropy(list(distribution.values()))
    argmax = votes.most_common(1)[0][0]
    etd = EventTypeDistribution(
        distribution=distribution,
        argmax=argmax,
        entropy=round(entropy, 4),
        confidence=round(1.0 - entropy, 4),
        samples=n,
    )

    names = {f.name for s in samples for f in s.fields}
    fields: list[FieldConsensus] = []
    for name in sorted(names):
        present: list[RawField] = [
            f for s in samples if (f := s.field(name)) and f.value not in (None, "")
        ]
        if not present:
            fields.append(FieldConsensus(name, None, 0.0, 0.0, None, None, 0))
            continue
        counts = Counter(_norm_value(f.value) for f in present)
        mode_norm, mode_count = counts.most_common(1)[0]
        agreement = mode_count / n
        reps = [f for f in present if _norm_value(f.value) == mode_norm]
        self_report = sum(f.confidence for f in reps) / len(reps)
        rep = reps[0]
        fields.append(
            FieldConsensus(
                name=name,
                value=rep.value,
                agreement=round(agreement, 4),
                self_report=round(self_report, 4),
                quote=rep.quote,
                page=rep.page,
                n_present=len(present),
            )
        )
    return Consensus(event_type=etd, fields=fields)
