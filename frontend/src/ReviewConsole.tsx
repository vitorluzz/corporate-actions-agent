import { useEffect, useMemo, useState } from "react";
import { api, type ReviewBody } from "./api";
import {
  AuditTrail,
  Dashboard,
  DecisionBadge,
  EventTypeBar,
  FieldCard,
  GoldenPanel,
  GuardrailList,
  useDraft,
} from "./components";
import {
  IconArrowRight,
  IconCheckCircle,
  IconDocument,
  IconDownload,
  IconFlag,
  IconScan,
  IconXCircle,
} from "./icons";
import type {
  AuditEvent,
  DocumentListItem,
  DocumentResult,
  Project,
  ProjectSummary,
} from "./types";

export default function AnalysisPanel({
  project,
  operator,
  onCompleted,
}: {
  project: Project;
  operator: string;
  onCompleted: () => void;
}) {
  const pid = project.id;
  const [docs, setDocs] = useState<DocumentListItem[]>([]);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentResult | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { draft, onChange, reset, resetField } = useDraft();

  async function loadList() {
    try {
      const [d, s] = await Promise.all([
        api.projectDocuments(pid),
        api.projectSummary(pid).catch(() => null),
      ]);
      setDocs(d);
      setSummary(s);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  async function loadDoc(id: string) {
    setSelected(id);
    reset();
    const [r, a] = await Promise.all([api.document(id), api.audit(id)]);
    setResult(r);
    setAudit(a);
  }

  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid]);

  async function submit(decision: ReviewBody["decision"]) {
    if (!selected || !result) return;
    setNotice(null);
    setBusy(true);
    try {
      const corrections: Record<string, string> = {};
      for (const [k, v] of Object.entries(draft)) {
        const original = result.record[k] ?? "";
        if (v !== String(original)) corrections[k] = v;
      }
      await api.review(selected, { actor: operator, decision, field_corrections: corrections, note: "" });
      await Promise.all([loadDoc(selected), loadList()]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function finalize() {
    if (pending > 0) {
      setNotice(
        `Ainda há ${pending} documento(s) pendente(s). Aprove ou rejeite todos os documentos da fila antes de finalizar a análise.`,
      );
      return;
    }
    setNotice(null);
    setBusy(true);
    try {
      await api.completeProject(pid);
      onCompleted();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const total = summary?.progress.total ?? docs.length;
  const pending =
    summary?.progress.pending ??
    docs.filter((d) => d.decision !== "AUTO_APPROVE" && !d.human_status).length;
  const decided = total - pending;
  const flagged = useMemo(() => docs.filter((d) => d.decision !== "AUTO_APPROVE"), [docs]);
  const changedCount = result
    ? result.fields.filter((f) => draft[f.name] !== undefined && draft[f.name] !== (f.value ?? "")).length
    : 0;

  if (docs.length === 0) {
    return (
      <div className="empty">
        Nenhum documento analisado ainda. Vá para a aba <strong>Arquivos</strong>, suba os PDFs e
        clique em <strong>Realizar análise</strong>.
      </div>
    );
  }

  return (
    <>
      {error && <div className="error">{error}</div>}
      {notice && (
        <div className="banner notice-banner" role="alert">
          <IconFlag size={15} /> {notice}
        </div>
      )}

      <div className="panel-bar">
        <span className="progress-pill">
          <span className="progress-track">
            <span className="progress-fill" style={{ width: `${total ? (decided / total) * 100 : 0}%` }} />
          </span>
          {decided}/{total} decididos
        </span>
        <button
          className="btn primary"
          onClick={finalize}
          disabled={busy || total === 0}
          title={pending > 0 ? `Aprove os ${pending} documento(s) pendente(s) antes de finalizar` : "Concluir e gerar a documentação"}
        >
          Finalizar análise <IconArrowRight size={16} />
        </button>
      </div>

      {summary && <Dashboard summary={summary} />}

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-h">Fila ({flagged.length} p/ revisão de {docs.length})</div>
          {docs.map((d) => (
            <button
              key={d.id}
              className={`doc-item ${selected === d.id ? "active" : ""}`}
              onClick={() => loadDoc(d.id)}
            >
              <div className="doc-item-top">
                <span className="doc-file">{d.source_file}</span>
                <DecisionBadge decision={d.human_status === "APPROVED" ? "AUTO_APPROVE" : d.decision} />
              </div>
              <div className="doc-item-meta">
                <span>{d.event_type}</span>
                <span className="muted2">DQ {d.dq_score.toFixed(2)}</span>
                {d.human_status && <span className="pill ok sm">{d.human_status}</span>}
              </div>
            </button>
          ))}
        </aside>

        <main className="review">
          {!result ? (
            <div className="empty">Selecione um documento na fila para ver o conteúdo e a análise.</div>
          ) : (
            <>
              <div className="review-h">
                <div>
                  <h2>{result.document.source_file}</h2>
                  <span className="muted">
                    {result.document.doc_class} · {result.document.extraction_method} · modelo{" "}
                    {result.document.model} · hash {result.document.doc_hash}
                  </span>
                </div>
                <div className="review-h-actions">
                  <DecisionBadge decision={result.routing.decision} />
                  {(result.human_status === "APPROVED" ||
                    (result.routing.decision === "AUTO_APPROVE" && !result.human_status)) && (
                    <button
                      className="btn sm"
                      title="Baixar certificado de análise (PDF)"
                      onClick={() =>
                        api.certificatePdf(
                          result.document.id,
                          `CAA_certificado_${result.document.source_file.replace(/\.pdf$/i, "")}.pdf`,
                        )
                      }
                    >
                      <IconDownload size={15} /> Certificado (PDF)
                    </button>
                  )}
                </div>
              </div>

              <div className="review-grid">
                <div className="pdf-pane bracket-frame">
                  <span className="bracket tl" />
                  <span className="bracket tr" />
                  <span className="bracket bl" />
                  <span className="bracket br" />
                  <img
                    className="pdf-img"
                    src={api.pageImageUrl(result.document.id)}
                    alt={`Documento ${result.document.source_file}`}
                  />
                </div>

                <div className="fields-pane">
                  {result.document.doc_class === "SCANNED" && (
                    <div className="scan-notice">
                      <span className="scan-icon"><IconScan size={22} /></span>
                      <div>
                        <strong>Documento escaneado (imagem)</strong>
                        <p>
                          Este arquivo não possui camada de texto. A leitura foi feita por{" "}
                          <strong>
                            {result.document.extraction_method === "tesseract_ocr"
                              ? "OCR (Tesseract)"
                              : result.document.extraction_method.includes("vision")
                                ? "visão computacional (Gemini Vision)"
                                : "leitura automática"}
                          </strong>
                          .{" "}
                          {result.fields.filter((f) => f.value).length > 1
                            ? "Os campos foram extraídos por OCR e podem conter ruído de leitura — confira cada valor contra a imagem ao lado."
                            : "A leitura automática não recuperou texto suficiente — leia pela imagem e valide/preencha manualmente."}
                        </p>
                      </div>
                    </div>
                  )}
                  {result.routing.reasons.length > 0 && (
                    <div className="card reasons">
                      <div className="card-h"><IconFlag size={15} /> Por que precisa de atenção</div>
                      <ul>{result.routing.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
                      {result.routing.required_human_actions.length > 0 && (
                        <>
                          <div className="card-h">Ações requeridas</div>
                          <ul className="actions">
                            {result.routing.required_human_actions.map((a, i) => <li key={i}>{a}</li>)}
                          </ul>
                        </>
                      )}
                    </div>
                  )}

                  <EventTypeBar et={result.event_type} />

                  <div className="card">
                    <div className="card-h">
                      <IconDocument size={15} /> Campos extraídos
                      <span className="muted"> · DQ {result.validation.dq_score.score.toFixed(2)} · edite qualquer valor incorreto e salve/aprove</span>
                    </div>
                    <div className="fields-grid">
                      {result.fields.map((f) => (
                        <FieldCard key={f.name} f={f} draft={draft[f.name]} onChange={onChange} onReset={resetField} />
                      ))}
                    </div>
                  </div>

                  <GoldenPanel gm={result.validation.golden_match} />
                  <GuardrailList guards={result.validation.coherence_checks} />
                  <AuditTrail events={audit} />

                  <div className="review-actions">
                    {changedCount > 0 && (
                      <span className="changed-note">
                        {changedCount} campo{changedCount === 1 ? "" : "s"} alterado{changedCount === 1 ? "" : "s"} — salve ou aprove para revalidar
                      </span>
                    )}
                    <button className="btn ghost" onClick={() => submit("save")} disabled={busy || changedCount === 0}>
                      Salvar correções
                    </button>
                    <button className="btn bad" onClick={() => submit("reject")} disabled={busy}>
                      <IconXCircle size={16} /> Rejeitar
                    </button>
                    <button className="btn ok" onClick={() => submit("approve")} disabled={busy}>
                      <IconCheckCircle size={16} /> Aprovar registro
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </>
  );
}
