"""Write the deliverables: per-document JSON + exceptions report + run summary."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.enums import RoutingDecision
from app.domain.schemas import DocumentResult, RunSummary


def _exceptions_markdown(results: list[DocumentResult], summary: RunSummary) -> str:
    flagged = [r for r in results if r.routing.decision is not RoutingDecision.AUTO_APPROVE]
    lines: list[str] = [
        "# Relatório de Exceções — Asset Servicing",
        "",
        f"**Run:** `{summary.run_id}`  ·  **Gerado:** {summary.created_at:%Y-%m-%d %H:%M UTC}",
        "",
        f"- Total de documentos: **{summary.total}**",
        f"- Auto-aprovados: **{summary.auto_approved}** ({summary.auto_rate:.0%})",
        f"- Para revisão humana: **{summary.review}**",
        f"- Rejeitados: **{summary.rejected}**",
        f"- Confiança média (campos): **{summary.avg_confidence:.0%}**",
        f"- Mix de tipos: {', '.join(f'{k}={v}' for k, v in summary.type_mix.items())}",
        "",
        f"## Documentos que requerem atuação humana ({len(flagged)})",
        "",
    ]
    for r in flagged:
        gm = r.validation.golden_match
        lines += [
            f"### {r.document.source_file} — `{r.routing.decision.value}`",
            f"- **Tipo:** {r.event_type.argmax.value} "
            f"(confiança {r.event_type.confidence:.0%}, entropia {r.event_type.entropy:.2f})",
            f"- **Identidade:** {gm.status.value} — {gm.explanation}",
            f"- **Data Quality:** {r.validation.dq_score.score:.2f} ({r.validation.dq_score.label.value})",
            "- **Motivos:**",
        ]
        lines += [f"  - {reason}" for reason in r.routing.reasons]
        if r.routing.required_human_actions:
            lines.append("- **Ações requeridas:**")
            lines += [f"  - {a}" for a in r.routing.required_human_actions]
        lines.append("")
    if not flagged:
        lines.append("_Nenhuma exceção — todos os documentos foram auto-aprovados._")
    return "\n".join(lines)


def _exceptions_json(results: list[DocumentResult]) -> list[dict]:
    return [
        {
            "document": r.document.source_file,
            "decision": r.routing.decision.value,
            "event_type": r.event_type.argmax.value,
            "golden_match": r.validation.golden_match.status.value,
            "dq_score": r.validation.dq_score.score,
            "reasons": r.routing.reasons,
            "required_human_actions": r.routing.required_human_actions,
        }
        for r in results
        if r.routing.decision is not RoutingDecision.AUTO_APPROVE
    ]


def write_outputs(
    results: list[DocumentResult], summary: RunSummary, outputs_dir: str | Path
) -> Path:
    outputs_dir = Path(outputs_dir)
    json_dir = outputs_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    for r in results:
        (json_dir / f"{r.document.id}.json").write_text(
            r.model_dump_json(indent=2), encoding="utf-8"
        )

    (outputs_dir / "run_summary.json").write_text(
        summary.model_dump_json(indent=2), encoding="utf-8"
    )
    (outputs_dir / "exceptions_report.md").write_text(
        _exceptions_markdown(results, summary), encoding="utf-8"
    )
    (outputs_dir / "exceptions_report.json").write_text(
        json.dumps(_exceptions_json(results), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return outputs_dir
