"""Deterministic, offline extraction stub.

Not a per-file mock — a genuine label-anchored heuristic parser for B3/CVM
"avisos aos acionistas", whose fields appear as ``label`` / ``value`` pairs. It
anchors values to their labels (so it won't grab an unrelated ``R$ 50.000,00``
tax threshold as the per-share value), captures gross/net + IRRF for JCP, and
records "A definir" payment dates as present-but-undefined.

This lets the whole pipeline run, be tested, and produce a real ``outputs/``
batch with zero API calls. For scanned docs (no text layer) it honestly returns
INCERTO -> human review, since OCR/vision is the LLM provider's job.
"""

from __future__ import annotations

import re

from app.domain.enums import EventType
from app.llm.base import ExtractionInput, RawExtraction, RawField

ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
TICKER_RE = re.compile(r"\b([A-Z]{4}\d{1,2})\b")
CNPJ_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")
MONEY_RE = re.compile(r"R\$\s*[\d.]+,\d{2,}")
DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b")
PERCENT_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%")
RATIO_RE = re.compile(r"\d+\s*(?::|para)\s*\d+", re.IGNORECASE)

EVENT_KEYWORDS: list[tuple[EventType, tuple[str, ...]]] = [
    (EventType.JCP, ("juros sobre o capital", "juros sobre capital", "jcp")),
    (EventType.BONIFICACAO, ("bonificação", "bonificacao")),
    (EventType.GRUPAMENTO, ("grupamento", "agrupamento")),
    (EventType.DESDOBRAMENTO, ("desdobramento", "split")),
    (EventType.SUBSCRICAO, ("subscrição", "subscricao")),
    (EventType.DIVIDENDO, ("dividendo", "dividendos")),
    (EventType.RENDIMENTO, ("rendimento",)),
    (EventType.PROVENTOS, ("proventos",)),
]

DATE_LABELS: dict[str, tuple[str, ...]] = {
    "data_aprovacao": ("data de aprova", "aprovacao (rca)", "aprovação (rca)"),
    "data_com": ("data-base", "data base", "data com"),
    "data_ex": ('data "ex', "data ex", "ex-dividend", "ex-jcp", "ex jcp"),
    "data_pagamento": ("data de pagamento",),
}


def _norm(s: str) -> str:
    return s.replace("\u201c", '"').replace("\u201d", '"').lower()


def _classify(text: str) -> tuple[EventType, str]:
    low = _norm(text)
    for etype, kws in EVENT_KEYWORDS:
        for kw in kws:
            if kw in low:
                return etype, f"palavra-chave '{kw}'"
    return EventType.INCERTO, "nenhuma palavra-chave de tipo reconhecida"


def _value_after(
    lines: list[str],
    label_variants: tuple[str, ...],
    pattern: re.Pattern,
    max_skip: int = 4,
    max_label_len: int = 55,
) -> tuple[str | None, int | None]:
    """Find the value following a label.

    Uses the LAST label occurrence on a SHORT line, so prose sentences that
    mention a label (with dates written out in full) don't shadow the structured
    "label / value" block at the bottom of the aviso.
    """
    low = [_norm(ln) for ln in lines]
    label_idx: int | None = None
    for i, ln in enumerate(low):
        if len(lines[i].strip()) <= max_label_len and any(lbl in ln for lbl in label_variants):
            label_idx = i
    if label_idx is None:
        return None, None
    for j in range(label_idx + 1, min(label_idx + 1 + max_skip, len(lines))):
        m = pattern.search(lines[j])
        if m:
            return m.group(0), j
    return None, label_idx  # label present but no value (e.g. "A definir")


class StubClient:
    name = "stub"
    model = "heuristic-label-parser-v1"

    def extract(
        self, inp: ExtractionInput, *, temperature: float, sample_index: int
    ) -> RawExtraction:
        text = inp.text or ""
        if not text.strip():
            return RawExtraction(
                event_type=EventType.INCERTO,
                event_type_rationale="sem camada de texto (provável escaneado)",
                fields=[],
            )

        lines = list(text.splitlines())
        fields: list[RawField] = []

        # --- event type (prefer the "Tipo de evento" value line) -----------
        type_value, _ = _value_after(lines, ("tipo de evento",), re.compile(r"\S.*"))
        etype, reason = _classify(type_value or text)
        if type_value:
            fields.append(RawField(name="tipo_evento", value=type_value.strip(),
                                   quote=type_value.strip(), confidence=0.9, rationale=reason))

        # --- identity ------------------------------------------------------
        for name, pat, conf in (("isin", ISIN_RE, 0.95), ("ticker", TICKER_RE, 0.9),
                                ("cnpj", CNPJ_RE, 0.92)):
            m = pat.search(text)
            if m:
                fields.append(RawField(name=name, value=m.group(1), quote=m.group(0),
                                       confidence=conf, rationale=f"padrão {name}"))

        first_line = next((ln.strip() for ln in lines if ln.strip()), None)
        if first_line:
            fields.append(RawField(name="emissor", value=first_line[:90], quote=first_line[:120],
                                   confidence=0.65, rationale="primeira linha (cabeçalho)"))

        # --- dates by label ------------------------------------------------
        for fname, labels in DATE_LABELS.items():
            val, line_idx = _value_after(lines, labels, DATE_RE)
            if val:
                fields.append(RawField(name=fname, value=val, quote=val, page=1,
                                       confidence=0.85, rationale=f"data rotulada ({fname})"))
            elif line_idx is not None:
                fields.append(RawField(name=fname, value=None, page=1, confidence=0.3,
                                       rationale="rótulo presente, data não definida (ex.: 'A definir')"))

        # --- values --------------------------------------------------------
        bruto, _ = _value_after(lines, ("valor bruto",), MONEY_RE)
        liquido, _ = _value_after(lines, ("valor líquido", "valor liquido"), MONEY_RE)
        irrf, _ = _value_after(
            lines, ("irrf", "imposto de renda retido", "imposto de renda na"), PERCENT_RE
        )
        if bruto:
            target = "valor_bruto" if (liquido or etype is EventType.JCP) else "valor"
            fields.append(RawField(name=target, value=bruto, quote=bruto, confidence=0.85,
                                   rationale="valor bruto rotulado"))
        if liquido:
            fields.append(RawField(name="valor_liquido", value=liquido, quote=liquido,
                                   confidence=0.85, rationale="valor líquido rotulado"))
        if irrf:
            fields.append(RawField(name="irrf", value=irrf, quote=irrf, confidence=0.85,
                                   rationale="alíquota IRRF rotulada"))

        if etype.is_share_ratio_event:
            m = RATIO_RE.search(text) or PERCENT_RE.search(text)
            if m:
                fields.append(RawField(name="proporcao", value=m.group(0), quote=m.group(0),
                                       confidence=0.7, rationale="proporção/razão de ações"))

        fields.append(RawField(name="moeda", value="BRL", confidence=0.8,
                               quote="R$" if "r$" in text.lower() else None,
                               rationale="moeda BRL (R$)"))

        return RawExtraction(event_type=etype, event_type_rationale=reason, fields=fields)
