"""Branded PDF artifacts (WeasyPrint) — auditable certificates and project reports.

Generated server-side from the *persisted record* (same source of truth as the JSON),
so a PDF is an auditable artifact, not a screenshot. The visual language mirrors the
CAA design system (paper + ink-navy, monospaced data, status colors, corner brackets).

WeasyPrint is imported lazily so a missing native dependency degrades to a clear
HTTP 503 instead of breaking the whole API at import time.
"""

from __future__ import annotations

import base64
import html
from datetime import UTC, datetime
from typing import Any

from app.domain.schemas import DocumentResult

# --------------------------------------------------------------------------- #
# Shared CAA stylesheet (print)
# --------------------------------------------------------------------------- #
CAA_CSS = """
@page {
  size: A4;
  margin: 15mm 14mm 16mm;
  background: #f4efe4;
  @bottom-left { content: "CAA · Corporate Actions Agent"; font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; font-size: 7.5pt; color: #8a8f97; }
  @bottom-right { content: "Página " counter(page) " de " counter(pages); font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; font-size: 7.5pt; color: #8a8f97; }
}
* { box-sizing: border-box; }
body { font-family: "Inter","DejaVu Sans",sans-serif; color: #101c2c; font-size: 9.5pt; line-height: 1.5; margin: 0; }
.mono { font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; }
h1 { font-size: 17pt; margin: 0 0 2px; letter-spacing: -0.01em; }
h2 { font-size: 10pt; text-transform: uppercase; letter-spacing: 0.08em; margin: 16px 0 7px; padding-bottom: 4px; border-bottom: 1px solid rgba(16,28,44,0.20); }
.muted { color: #4a4f58; }
.sub { color: #4a4f58; font-size: 9.5pt; margin-bottom: 6px; }

.masthead { position: relative; display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; margin-bottom: 16px; background: #faf7f0; border: 1px solid rgba(16,28,44,0.20); border-radius: 8px; }
.masthead .logo { height: 30px; }
.wordmark { font-size: 16pt; font-weight: 700; letter-spacing: 0.18em; }

.bracket-frame { position: relative; }
.bracket { position: absolute; width: 12px; height: 12px; border: 0 solid #101c2c; }
.bracket.tl { top: 7px; left: 7px; border-top-width: 2px; border-left-width: 2px; }
.bracket.tr { top: 7px; right: 7px; border-top-width: 2px; border-right-width: 2px; }
.bracket.bl { bottom: 7px; left: 7px; border-bottom-width: 2px; border-left-width: 2px; }
.bracket.br { bottom: 7px; right: 7px; border-bottom-width: 2px; border-right-width: 2px; }

.seal { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; border-radius: 999px;
  font-weight: 700; font-size: 10pt; color: #fff; }
.seal.ok { background: #1e9e6b; }
.seal.warn { background: #e0a23e; }
.seal.bad { background: #c24b3d; }

.badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 8pt; font-weight: 700; color: #fff; white-space: nowrap; }
.badge.ok { background: #1e9e6b; } .badge.warn { background: #e0a23e; } .badge.bad { background: #c24b3d; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 5px; font-size: 7.5pt; font-weight: 700; font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; }
.pill.ok { background: rgba(30,158,107,0.14); color: #157551; }
.pill.warn { background: rgba(224,162,62,0.18); color: #946514; }
.pill.bad { background: rgba(194,75,61,0.14); color: #9a382c; }
.pill.na { background: rgba(74,79,88,0.12); color: #4a4f58; }

.cols { display: flex; gap: 14px; align-items: flex-start; }
.col-img { width: 38%; }
.col-data { width: 62%; }
.page-shot { position: relative; padding: 10px; background: #faf7f0; border: 1px solid rgba(16,28,44,0.55); border-radius: 8px; }
.page-shot img { width: 100%; display: block; }

.card { background: #faf7f0; border: 1px solid rgba(16,28,44,0.20); border-radius: 8px; padding: 11px 13px; margin-bottom: 10px; }
.card-h { font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 700; margin-bottom: 7px; }
.kv { display: flex; justify-content: space-between; gap: 10px; padding: 2.5px 0; border-bottom: 1px solid rgba(16,28,44,0.10); }
.kv:last-child { border-bottom: none; }
.kv .k { color: #4a4f58; font-size: 8.5pt; }
.kv .v { font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; font-size: 8.5pt; text-align: right; }

table.tbl { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
table.tbl th { text-align: left; text-transform: uppercase; letter-spacing: 0.05em; font-size: 7.5pt; color: #4a4f58;
  padding: 6px 7px; border-bottom: 1px solid rgba(16,28,44,0.30); }
table.tbl td { padding: 6px 7px; border-bottom: 1px solid rgba(16,28,44,0.14); vertical-align: top; }
table.tbl td.v { font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; }
.conf { font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; font-weight: 700; }
.conf.high { color: #157551; } .conf.med { color: #946514; } .conf.low { color: #9a382c; }
.quote { color: #4a4f58; font-style: italic; }

.stats { display: flex; gap: 10px; margin: 4px 0 8px; }
.stat { flex: 1; background: #faf7f0; border: 1px solid rgba(16,28,44,0.20); border-radius: 8px; padding: 10px 12px; }
.stat .n { font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; font-size: 17pt; font-weight: 700; }
.stat .l { font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.06em; color: #4a4f58; }
.stat.ok .n { color: #157551; } .stat.warn .n { color: #946514; } .stat.bad .n { color: #9a382c; }

.foot { margin-top: 16px; padding-top: 8px; border-top: 1px solid rgba(16,28,44,0.20); font-size: 7.5pt; color: #8a8f97;
  font-family: "IBM Plex Mono","DejaVu Sans Mono",monospace; display: flex; justify-content: space-between; gap: 12px; }
.reasons { margin: 0; padding-left: 16px; }
.reasons li { margin: 2px 0; }
.reasons.actions li { color: #946514; }
"""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _tier(p: float) -> str:
    return "high" if p >= 0.8 else "med" if p >= 0.55 else "low"


def _logo_data_uri() -> str | None:
    from app.config.settings import REPO_ROOT

    logo = REPO_ROOT / "frontend" / "assets" / "logo.png"
    if logo.exists():
        b64 = base64.b64encode(logo.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return None


def _brand_html() -> str:
    uri = _logo_data_uri()
    if uri:
        return f'<img class="logo" src="{uri}" alt="CAA" />'
    return '<div class="wordmark">CAA</div>'


def _png_data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _decision_kind_label(decision: str, human_status: str | None) -> tuple[str, str]:
    if human_status == "REJECTED" or decision == "REJECT":
        return "bad", "Rejeitado"
    if human_status == "APPROVED":
        return "ok", "Aprovado pelo operador"
    if decision == "AUTO_APPROVE":
        return "ok", "Auto-aprovado"
    return "warn", "Revisão humana"


def _decision_short(decision: str, human_status: str | None) -> tuple[str, str]:
    if human_status == "REJECTED" or decision == "REJECT":
        return "bad", "Rejeitado"
    if human_status == "APPROVED":
        return "ok", "Aprovado"
    if decision == "AUTO_APPROVE":
        return "ok", "Auto"
    return "warn", "Revisão"


def _render(html_body: str) -> bytes:
    """Lay out the HTML with WeasyPrint (lazy import → clear error if unavailable)."""
    try:
        from weasyprint import CSS, HTML
    except Exception as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(f"Geração de PDF indisponível (WeasyPrint/libs nativas ausentes): {exc}") from exc
    try:
        return HTML(string=html_body).write_pdf(stylesheets=[CSS(string=CAA_CSS)])
    except Exception as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(f"Falha ao renderizar PDF: {exc}") from exc


# --------------------------------------------------------------------------- #
# Per-document certificate
# --------------------------------------------------------------------------- #
def render_certificate_pdf(
    result: DocumentResult,
    audit_events: list[Any],
    page_png: bytes | None,
    project_name: str | None,
    human_status: str | None,
) -> bytes:
    doc = result.document
    rec = result.record
    val = result.validation
    et = result.event_type
    kind, seal_label = _decision_kind_label(result.routing.decision.value, human_status)

    # provenance + identity cards
    prov = [
        ("Documento", doc.source_file),
        ("Classe", f"{doc.doc_class.value} · {doc.extraction_method}"),
        ("Modelo", doc.model),
        ("doc_hash", doc.doc_hash),
        ("run_id", doc.run_id),
        ("prompt_hash", doc.prompt_hash),
    ]
    identity = [
        ("Emissor", rec.emissor),
        ("ISIN", rec.isin),
        ("Ticker", rec.ticker),
        ("CNPJ", rec.cnpj),
        ("Tipo de evento", et.argmax.value),
        ("Moeda", rec.moeda),
    ]
    gm = val.golden_match
    golden_kind = "ok" if gm.status.value == "EXACT" else "bad" if gm.status.value in ("NONE", "CONFLICT") else "warn"

    def kv(rows: list[tuple[str, Any]]) -> str:
        return "".join(f'<div class="kv"><span class="k">{_esc(k)}</span><span class="v">{_esc(v) or "—"}</span></div>' for k, v in rows)

    # fields table
    field_rows = ""
    for f in result.fields:
        pct = round(f.confidence.p_correct * 100)
        ev = ""
        if f.evidence and f.evidence.quote:
            q = f.evidence.quote[:70]
            page = f" · p.{f.evidence.page}" if f.evidence.page is not None else ""
            ev = f'<span class="quote">“{_esc(q)}”</span>{_esc(page)}'
        anchor = '<span class="pill ok">ancorado</span>' if f.grounded else '<span class="pill bad">sem âncora</span>'
        field_rows += (
            f"<tr><td>{_esc(f.name)}</td><td class='v'>{_esc(f.value) or '—'}</td>"
            f"<td><span class='conf {_tier(f.confidence.p_correct)}'>{pct}%</span></td>"
            f"<td>{ev or '—'} {anchor}</td></tr>"
        )

    # guardrails table
    guard_rows = ""
    for g in val.coherence_checks:
        pk = {"PASS": "ok", "WARN": "warn", "FAIL": "bad"}.get(g.status.value, "na")
        guard_rows += (
            f"<tr><td><span class='pill {pk}'>{_esc(g.status.value)}</span></td>"
            f"<td class='v'>{_esc(g.name)}</td><td>{_esc(g.message)}</td></tr>"
        )

    # decision events (who approved / when)
    decisions = [e for e in audit_events if str(e.action).startswith("decision:")]
    dec_html = ""
    for e in decisions:
        ts = datetime.fromisoformat(e.ts.isoformat()) if hasattr(e.ts, "isoformat") else e.ts
        dec_html += f"<div class='kv'><span class='k'>{_esc(e.actor)} · {_esc(e.action)}</span><span class='v'>{_esc(ts)}</span></div>"
    if not dec_html:
        dec_html = "<div class='muted'>Sem decisão humana registrada (auto-aprovado pela política determinística).</div>"

    reasons = result.routing.reasons
    reasons_html = (
        "<ul class='reasons'>" + "".join(f"<li>{_esc(r)}</li>" for r in reasons) + "</ul>"
        if reasons else "<div class='muted'>Nenhuma exceção registrada.</div>"
    )

    page_block = (
        f"<div class='page-shot bracket-frame'><span class='bracket tl'></span><span class='bracket tr'></span>"
        f"<span class='bracket bl'></span><span class='bracket br'></span>"
        f"<img src='{_png_data_uri(page_png)}' alt='página' /></div>"
        if page_png else "<div class='card muted'>Imagem da página indisponível.</div>"
    )

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8" /></head><body>
  <div class="masthead bracket-frame">
    <span class="bracket tl"></span><span class="bracket br"></span>
    {_brand_html()}
    <div class="seal {kind}">● {_esc(seal_label)}</div>
  </div>

  <h1>Certificado de análise</h1>
  <div class="sub">{_esc(doc.source_file)}{f" · projeto {_esc(project_name)}" if project_name else ""}</div>

  <div class="cols">
    <div class="col-img">{page_block}</div>
    <div class="col-data">
      <div class="card"><div class="card-h">Identidade</div>{kv(identity)}</div>
      <div class="card"><div class="card-h">Base de referência (entity resolution)</div>
        <div style="margin-bottom:6px"><span class="badge {golden_kind}">{_esc(gm.status.value)}</span>
        <span class="muted">{(" → " + _esc(gm.golden_emissor) + " (" + _esc(gm.golden_ticker) + ")") if gm.golden_ticker else ""}</span></div>
        <div class="muted" style="font-size:8.5pt">{_esc(gm.explanation)}</div>
      </div>
      <div class="card"><div class="card-h">Classificação &amp; qualidade</div>
        {kv([("Tipo (argmax)", et.argmax.value), ("Confiança do tipo", f"{round(et.confidence*100)}%"), ("Entropia", f"{et.entropy:.2f}"), ("Data Quality (DQ)", f"{val.dq_score.score:.2f}")])}
      </div>
    </div>
  </div>

  <h2>Procedência</h2>
  <div class="card">{kv(prov)}</div>

  <h2>Campos extraídos &amp; evidência</h2>
  <table class="tbl"><thead><tr><th>Campo</th><th>Valor</th><th>Confiança</th><th>Evidência</th></tr></thead>
  <tbody>{field_rows}</tbody></table>

  <h2>Guardrails &amp; coerência</h2>
  <table class="tbl"><thead><tr><th>Status</th><th>Regra</th><th>Mensagem</th></tr></thead>
  <tbody>{guard_rows}</tbody></table>

  <h2>Decisão &amp; auditoria</h2>
  {reasons_html}
  <div class="card" style="margin-top:8px">{dec_html}</div>

  <div class="foot"><span>doc_hash {_esc(doc.doc_hash)} · run {_esc(doc.run_id)}</span><span>Gerado {generated}</span></div>
</body></html>"""
    return _render(body)


# --------------------------------------------------------------------------- #
# Project report
# --------------------------------------------------------------------------- #
def render_project_report_pdf(report: dict) -> bytes:
    proj = report["project"]
    s = report["summary"]
    docs = report["documents"]
    completed = proj.get("status") == "COMPLETED"

    def stat(n: Any, label: str, cls: str = "") -> str:
        return f"<div class='stat {cls}'><div class='n'>{_esc(n)}</div><div class='l'>{_esc(label)}</div></div>"

    rows = ""
    for d in docs:
        kind, label = _decision_short(d["decision"], d.get("human_status"))
        corr = len(d.get("corrections") or [])
        rows += (
            f"<tr><td class='v'>{_esc(d['source_file'])}</td><td>{_esc(d['event_type'])}</td>"
            f"<td><span class='badge {kind}'>{_esc(label)}</span></td>"
            f"<td class='v'>{d['dq_score']:.2f}</td><td>{_esc(d['golden_match'])}</td>"
            f"<td class='v'>{corr or '—'}</td></tr>"
        )

    # corrections detail
    corr_blocks = ""
    for d in docs:
        cs = d.get("corrections") or []
        if not cs:
            continue
        items = "".join(
            f"<div class='kv'><span class='k'>{_esc(c.get('field'))}</span>"
            f"<span class='v'>{_esc(c.get('old')) or '—'} → {_esc(c.get('new'))}</span></div>"
            for c in cs
        )
        corr_blocks += f"<div class='card'><div class='card-h'>{_esc(d['source_file'])}</div>{items}</div>"
    corr_section = (
        f"<h2>Correções do operador</h2>{corr_blocks}" if corr_blocks else ""
    )

    status_label = {"COMPLETED": "Concluído", "REVIEW": "Em revisão", "ANALYZING": "Em análise", "DRAFT": "Rascunho"}.get(proj.get("status"), proj.get("status"))
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    when = proj.get("completed_at") if completed else None
    body = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8" /></head><body>
  <div class="masthead bracket-frame">
    <span class="bracket tl"></span><span class="bracket br"></span>
    {_brand_html()}
    <div class="seal {'ok' if completed else 'warn'}">● {_esc(status_label)}</div>
  </div>

  <h1>Relatório do projeto</h1>
  <div class="sub">{_esc(proj['name'])} · operador {_esc(proj.get('operator')) or '—'}
    {f" · concluído {_esc(when)}" if when else " · prévia (projeto ainda não finalizado)"}</div>

  <div class="stats">
    {stat(s['total'], 'Documentos')}
    {stat(s['approved'], 'Aprovados', 'ok')}
    {stat(s['auto_approved'], 'Auto-aprovados')}
    {stat(s['rejected'], 'Rejeitados', 'bad' if s['rejected'] else '')}
    {stat(s['corrections'], 'Correções')}
  </div>

  <h2>Documentos</h2>
  <table class="tbl"><thead><tr><th>Arquivo</th><th>Tipo</th><th>Decisão</th><th>DQ</th><th>Identidade</th><th>Correções</th></tr></thead>
  <tbody>{rows}</tbody></table>

  {corr_section}

  <div class="foot"><span>Projeto {_esc(proj['id'])}</span><span>Gerado {generated}</span></div>
</body></html>"""
    return _render(body)
