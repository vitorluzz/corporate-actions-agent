import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { DecisionBadge } from "./components";
import type { Project, ProjectFile, ProjectReport } from "./types";

export type Tab = "files" | "analysis" | "graph" | "documentation";

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Rascunho",
  ANALYZING: "Em análise",
  REVIEW: "Em revisão",
  COMPLETED: "Concluído",
};
const STATUS_CLS: Record<string, string> = {
  DRAFT: "muted2",
  ANALYZING: "warn",
  REVIEW: "warn",
  COMPLETED: "ok",
};

export function ProjectStatus({ status }: { status: string }) {
  return <span className={`pill ${STATUS_CLS[status] ?? "muted2"}`}>{STATUS_LABEL[status] ?? status}</span>;
}

// --------------------------------------------------------------------------- //
// Shared project header: back · name (rename) · status · delete · tabs
// --------------------------------------------------------------------------- //
export function ProjectHeader({
  project,
  tab,
  onTab,
  onBack,
  onRename,
  onDelete,
}: {
  project: Project;
  tab: Tab;
  onTab: (t: Tab) => void;
  onBack: () => void;
  onRename: (name: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(project.name);
  useEffect(() => setName(project.name), [project.name]);

  function save() {
    const v = name.trim();
    if (v && v !== project.name) onRename(v);
    setEditing(false);
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <button className="btn ghost back" onClick={onBack}>← Projetos</button>
          CAA{" "}
          {editing ? (
            <span className="rename">
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") save();
                  if (e.key === "Escape") {
                    setName(project.name);
                    setEditing(false);
                  }
                }}
              />
              <button className="btn sm ok" onClick={save}>salvar</button>
              <button className="btn sm ghost" onClick={() => { setName(project.name); setEditing(false); }}>
                cancelar
              </button>
            </span>
          ) : (
            <span className="brand-sub">· {project.name} <ProjectStatus status={project.status} /></span>
          )}
        </div>
        <div className="topbar-actions">
          {!editing && (
            <button className="btn ghost" onClick={() => setEditing(true)} title="Renomear projeto">
              ✎ Renomear
            </button>
          )}
          <button className="btn ghost danger" onClick={onDelete} title="Excluir projeto">
            🗑 Excluir
          </button>
        </div>
      </header>

      <nav className="tabs">
        <button className={`tab ${tab === "files" ? "active" : ""}`} onClick={() => onTab("files")}>
          Arquivos
        </button>
        <button className={`tab ${tab === "analysis" ? "active" : ""}`} onClick={() => onTab("analysis")}>
          Análise
        </button>
        <button className={`tab ${tab === "graph" ? "active" : ""}`} onClick={() => onTab("graph")}>
          Rastreabilidade
        </button>
        <button
          className={`tab ${tab === "documentation" ? "active" : ""}`}
          onClick={() => onTab("documentation")}
        >
          Documentação
        </button>
      </nav>
    </>
  );
}

// --------------------------------------------------------------------------- //
// Projects landing
// --------------------------------------------------------------------------- //
export function ProjectsView({
  operator,
  setOperator,
  onOpen,
}: {
  operator: string;
  setOperator: (v: string) => void;
  onOpen: (p: Project) => void;
}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setProjects(await api.projects());
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const p = await api.createProject(name.trim(), operator);
      setName("");
      await load();
      onOpen(p);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function rename(p: Project) {
    const next = window.prompt("Novo nome do projeto:", p.name);
    if (next && next.trim() && next.trim() !== p.name) {
      await api.renameProject(p.id, next.trim());
      await load();
    }
  }

  async function remove(p: Project) {
    if (!window.confirm(`Excluir "${p.name}"? Isso apaga os documentos e a análise.`)) return;
    await api.deleteProject(p.id);
    await load();
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          CAA <span className="brand-sub">· Corporate Actions Agent</span>
        </div>
        <label className="actor">
          operador:
          <input value={operator} onChange={(e) => setOperator(e.target.value)} />
        </label>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="hero">
        <h1>Projetos de análise de eventos corporativos</h1>
        <p className="muted">
          Crie um projeto, suba os avisos (PDF), rode a análise e revise os registros — com trilha
          de auditoria e documentação final.
        </p>
        <div className="create-row">
          <input
            className="create-input"
            placeholder="Nome do novo projeto (ex.: Eventos B3 — Junho/2026)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
          <button className="btn ok" onClick={create} disabled={busy || !name.trim()}>
            + Novo projeto
          </button>
        </div>
      </section>

      <div className="projects-grid">
        {projects.length === 0 && <div className="empty">Nenhum projeto ainda. Crie o primeiro acima.</div>}
        {projects.map((p) => (
          <div key={p.id} className="project-card">
            <div className="project-card-main" onClick={() => onOpen(p)}>
              <div className="project-card-h">
                <span className="project-name">{p.name}</span>
                <ProjectStatus status={p.status} />
              </div>
              <div className="project-meta">
                <span className="muted2">{p.operator ? `por ${p.operator}` : ""}</span>
                <span className="muted2">
                  {p.total > 0 ? `${p.decided}/${p.total} decididos` : "sem documentos"}
                </span>
              </div>
              {p.total > 0 && (
                <div className="progress-track wide">
                  <div className="progress-fill" style={{ width: `${(p.decided / p.total) * 100}%` }} />
                </div>
              )}
            </div>
            <div className="project-card-actions">
              <button className="icon-btn" title="Renomear" onClick={() => rename(p)}>✎</button>
              <button className="icon-btn danger" title="Excluir" onClick={() => remove(p)}>🗑</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Files panel (upload + run analysis) — body only (header in shell)
// --------------------------------------------------------------------------- //
export function FilesPanel({
  project,
  onAnalyzed,
}: {
  project: Project;
  onAnalyzed: () => void;
}) {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const analyzed = project.total > 0;

  async function load() {
    try {
      setFiles((await api.projectFiles(project.id)).files);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  async function upload(list: FileList | File[] | null) {
    const arr = list ? Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".pdf")) : [];
    if (!arr.length) return;
    setBusy(true);
    try {
      setFiles((await api.uploadFiles(project.id, arr)).files);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadSamples() {
    setBusy(true);
    try {
      setFiles((await api.loadSamples(project.id)).files);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove(name: string) {
    try {
      setFiles((await api.deleteFile(project.id, name)).files);
    } catch (e) {
      setError(String(e));
    }
  }

  async function analyze() {
    setAnalyzing(true);
    setError(null);
    try {
      await api.analyze(project.id);
      onAnalyzed();
    } catch (e) {
      setError(String(e));
      setAnalyzing(false);
    }
  }

  return (
    <>
      {analyzing && (
        <div className="analyzing-overlay">
          <div className="spinner" />
          <div className="analyzing-title">Analisando os documentos…</div>
          <div className="muted">extração → guardrails → confiança → roteamento</div>
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {analyzed && (
        <div className="banner">
          Este projeto já foi analisado. Veja a aba <strong>Análise</strong>, ou rode novamente para
          reprocessar (as decisões humanas serão refeitas).
        </div>
      )}
      <div className="upload-wrap">
        <div
          className={`dropzone ${dragOver ? "over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            upload(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            multiple
            hidden
            onChange={(e) => upload(e.target.files)}
          />
          <div className="dropzone-icon">⬆</div>
          <div>
            <strong>Arraste PDFs aqui</strong> ou clique para selecionar
          </div>
          <button
            className="btn ghost"
            onClick={(e) => {
              e.stopPropagation();
              loadSamples();
            }}
            disabled={busy}
          >
            ou carregar os 8 avisos de exemplo
          </button>
        </div>

        <div className="filelist card">
          <div className="card-h">Arquivos do projeto ({files.length})</div>
          {files.length === 0 ? (
            <div className="muted">Nenhum arquivo. Suba 1 ou mais PDFs para analisar.</div>
          ) : (
            <ul className="files">
              {files.map((f) => (
                <li key={f.name}>
                  <span className="file-icon">📄</span>
                  <span className="file-name">{f.name}</span>
                  <span className="muted2">{(f.size / 1024).toFixed(0)} KB</span>
                  <button className="file-remove" onClick={() => remove(f.name)} title="remover">✕</button>
                </li>
              ))}
            </ul>
          )}
          <div className="upload-actions">
            <button className="btn ok lg" onClick={analyze} disabled={busy || analyzing || files.length === 0}>
              {analyzing
                ? "Analisando… (extração + guardrails + roteamento)"
                : analyzed
                  ? "Reanalisar →"
                  : "Realizar análise →"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// --------------------------------------------------------------------------- //
// Documentation panel — body only (loads the report for the project)
// --------------------------------------------------------------------------- //
const FIELD_ORDER = [
  "emissor", "isin", "ticker", "cnpj", "tipo_evento",
  "data_aprovacao", "data_com", "data_ex", "data_pagamento",
  "valor", "valor_bruto", "valor_liquido", "irrf_rate", "proporcao", "moeda",
];

export function DocumentationPanel({ project }: { project: Project }) {
  const [report, setReport] = useState<ProjectReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.projectReport(project.id).then(setReport).catch((e) => setError(String(e)));
  }, [project.id]);

  function download() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CAA_${report.project.name.replace(/\s+/g, "_")}_documentacao.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error) return <div className="error">{error}</div>;
  if (!report) return <div className="empty">Carregando documentação…</div>;
  if (report.summary.total === 0)
    return <div className="empty">Sem documentos. Rode a análise na aba <strong>Arquivos</strong>.</div>;

  const s = report.summary;
  const completed = report.project.status === "COMPLETED";
  return (
    <>
      <div className="panel-bar">
        <div className="muted">
          {completed ? (
            <>Concluído {report.project.completed_at ? new Date(report.project.completed_at).toLocaleString("pt-BR") : ""}</>
          ) : (
            <>Prévia — finalize na aba <strong>Análise</strong> para concluir o projeto.</>
          )}
        </div>
        <button className="btn" onClick={download}>⬇ Baixar (JSON)</button>
      </div>

      <section className="report-head card">
        <div>
          <h1>Documentação da análise</h1>
          <span className="muted">
            Projeto <strong>{report.project.name}</strong> · operador {report.project.operator ?? "—"}
          </span>
        </div>
        <ProjectStatus status={report.project.status} />
      </section>

      <div className="dash">
        <div className="stat"><div className="stat-v">{s.total}</div><div className="stat-l">Documentos</div></div>
        <div className="stat ok"><div className="stat-v">{s.approved}</div><div className="stat-l">Aprovados</div></div>
        <div className="stat warn"><div className="stat-v">{s.auto_approved}</div><div className="stat-l">Auto-aprovados</div></div>
        <div className="stat bad"><div className="stat-v">{s.rejected}</div><div className="stat-l">Rejeitados</div></div>
        <div className="stat"><div className="stat-v">{s.corrections}</div><div className="stat-l">Correções humanas</div></div>
      </div>

      <div className="report-docs">
        {report.documents.map((d) => (
          <div key={d.id} className="card report-doc">
            <div className="report-doc-h">
              <strong>{d.source_file}</strong>
              <DecisionBadge decision={d.human_status === "APPROVED" ? "AUTO_APPROVE" : d.decision} />
            </div>
            <div className="report-doc-meta muted">
              {d.event_type} · identidade {d.golden_match} · DQ {d.dq_score.toFixed(2)}
              {d.human_status ? ` · ${d.human_status}` : ""}
            </div>

            {d.corrections.length > 0 && (
              <div className="corrections">
                <div className="card-h">Correções do operador</div>
                {d.corrections.map((c, i) => (
                  <div key={i} className="correction">
                    <span className="field-name">{c.field}</span>
                    <span className="old">{c.old ?? "—"}</span>
                    <span>→</span>
                    <span className="new">{c.new}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="record-grid">
              {FIELD_ORDER.filter((k) => d.record[k] != null && d.record[k] !== "").map((k) => (
                <div key={k} className="record-cell">
                  <span className="record-key">{k}</span>
                  <span className="record-val">{String(d.record[k])}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
