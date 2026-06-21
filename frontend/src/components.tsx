import { useState } from "react";
import type {
  AuditEvent,
  DocumentResult,
  EventTypeDistribution,
  ExtractedField,
  GoldenMatch,
  GuardrailResult,
  Routing,
  RunSummary,
} from "./types";

export function confTier(p: number): "high" | "med" | "low" {
  if (p >= 0.8) return "high";
  if (p >= 0.55) return "med";
  return "low";
}

export function DecisionBadge({ decision }: { decision: Routing["decision"] | string }) {
  const cls =
    decision === "AUTO_APPROVE" ? "ok" : decision === "REJECT" ? "bad" : "warn";
  const label =
    decision === "AUTO_APPROVE" ? "Auto-aprovado" : decision === "REJECT" ? "Rejeitado" : "Revisão humana";
  return <span className={`badge ${cls}`}>{label}</span>;
}

export function ConfidenceBar({ p }: { p: number }) {
  const tier = confTier(p);
  return (
    <div className="confbar" title={`p_correct=${(p * 100).toFixed(0)}%`}>
      <div className={`confbar-fill ${tier}`} style={{ width: `${Math.round(p * 100)}%` }} />
      <span className="confbar-label">{Math.round(p * 100)}%</span>
    </div>
  );
}

export function EventTypeBar({ et }: { et: EventTypeDistribution }) {
  const entries = Object.entries(et.distribution).sort((a, b) => b[1] - a[1]);
  return (
    <div className="card">
      <div className="card-h">
        Tipo de evento — <strong>{et.argmax}</strong>
        <span className="muted"> · conf {(et.confidence * 100).toFixed(0)}% · entropia {et.entropy.toFixed(2)} · {et.samples} amostras</span>
      </div>
      <div className="dist">
        {entries.map(([t, p]) => (
          <div key={t} className="dist-row">
            <span className="dist-label">{t}</span>
            <div className="dist-track"><div className="dist-fill" style={{ width: `${Math.round(p * 100)}%` }} /></div>
            <span className="dist-pct">{Math.round(p * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const STATUS_CLS: Record<string, string> = { PASS: "ok", WARN: "warn", FAIL: "bad", NA: "muted2" };

export function GuardrailList({ guards }: { guards: GuardrailResult[] }) {
  return (
    <div className="card">
      <div className="card-h">Guardrails / Data Quality</div>
      <ul className="guards">
        {guards.map((g) => (
          <li key={g.name}>
            <span className={`pill ${STATUS_CLS[g.status]}`}>{g.status}</span>
            <span className="guard-name">{g.name}</span>
            <span className="guard-msg">{g.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function GoldenPanel({ gm }: { gm: GoldenMatch }) {
  const cls = gm.status === "EXACT" ? "ok" : gm.status === "NONE" || gm.status === "CONFLICT" ? "bad" : "warn";
  return (
    <div className="card">
      <div className="card-h">Base de referência (entity resolution)</div>
      <div>
        <span className={`pill ${cls}`}>{gm.status}</span>
        <span className="muted"> {gm.golden_ticker ? `→ ${gm.golden_emissor} (${gm.golden_ticker})` : ""}</span>
      </div>
      <p className="explain">{gm.explanation}</p>
      {gm.discrepancies.length > 0 && (
        <ul className="disc">
          {gm.discrepancies.map((d, i) => (
            <li key={i}>{d.field}: extraído <code>{d.extracted}</code> ≠ base <code>{d.reference}</code></li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function FieldCard({
  f,
  draft,
  onChange,
}: {
  f: ExtractedField;
  draft: string | undefined;
  onChange: (name: string, value: string) => void;
}) {
  const tier = confTier(f.confidence.p_correct);
  const ev = f.evidence;
  return (
    <div className={`field ${tier}`}>
      <div className="field-top">
        <span className="field-name">{f.name}</span>
        {f.grounded ? <span className="pill ok sm">ancorado</span> : <span className="pill bad sm">sem âncora</span>}
      </div>
      <input
        className="field-input"
        value={draft ?? f.value ?? ""}
        placeholder="—"
        onChange={(e) => onChange(f.name, e.target.value)}
      />
      <ConfidenceBar p={f.confidence.p_correct} />
      <div className="field-meta">
        {ev?.quote && <span className="quote" title={ev.quote}>“{ev.quote.slice(0, 80)}”</span>}
        {ev?.page != null && <span className="muted2"> · p.{ev.page}{ev.bbox ? " · bbox" : ""}</span>}
      </div>
      <div className="field-rationale">{f.rationale}</div>
    </div>
  );
}

export function AuditTrail({ events }: { events: AuditEvent[] }) {
  return (
    <div className="card">
      <div className="card-h">Trilha de auditoria (append-only)</div>
      <ol className="audit">
        {events.map((e) => (
          <li key={e.id}>
            <span className="audit-ts">{new Date(e.ts).toLocaleString("pt-BR")}</span>
            <span className="audit-actor">{e.actor}</span>
            <span className="audit-action">{e.action}</span>
            {e.detail && Object.keys(e.detail).length > 0 && (
              <code className="audit-detail">{JSON.stringify(e.detail)}</code>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function Dashboard({ summary }: { summary: RunSummary }) {
  const stat = (label: string, value: string | number, cls = "") => (
    <div className={`stat ${cls}`}>
      <div className="stat-v">{value}</div>
      <div className="stat-l">{label}</div>
    </div>
  );
  return (
    <div className="dash">
      {stat("Documentos", summary.total)}
      {stat("Auto-aprovados", `${summary.auto_approved} (${Math.round(summary.auto_rate * 100)}%)`, "ok")}
      {stat("Revisão humana", summary.review, "warn")}
      {stat("Rejeitados", summary.rejected, summary.rejected ? "bad" : "")}
      {stat("Confiança média", `${Math.round(summary.avg_confidence * 100)}%`)}
      <div className="stat wide">
        <div className="stat-l">Mix de tipos</div>
        <div className="chips">
          {Object.entries(summary.type_mix).map(([t, n]) => (
            <span key={t} className="chip">{t}: {n}</span>
          ))}
        </div>
      </div>
      {Object.keys(summary.flag_reasons_histogram).length > 0 && (
        <div className="stat wide">
          <div className="stat-l">Motivos de exceção (observabilidade)</div>
          <div className="chips">
            {Object.entries(summary.flag_reasons_histogram).map(([t, n]) => (
              <span key={t} className="chip warn">{t}: {n}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function useDraft() {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const onChange = (name: string, value: string) => setDraft((d) => ({ ...d, [name]: value }));
  const reset = () => setDraft({});
  return { draft, onChange, reset };
}

export type Result = DocumentResult;
