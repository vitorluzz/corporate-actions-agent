import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { GraphData, GraphEdgeType, GraphNode, Project } from "./types";

const EDGE_STYLE: Record<GraphEdgeType, { color: string; width: number; dash: string; label: string }> = {
  belongs_to: { color: "#3f4654", width: 1.3, dash: "", label: "Pertence ao emissor" },
  same_event_type: { color: "#60a5fa", width: 1.6, dash: "5 4", label: "Mesmo tipo de evento" },
  same_security: { color: "#2dd4bf", width: 2.2, dash: "", label: "Mesmo ativo (ISIN/ticker)" },
  possible_duplicate: { color: "#fb923c", width: 2.4, dash: "6 4", label: "Possível duplicidade" },
};
const EDGE_ORDER: GraphEdgeType[] = ["belongs_to", "same_event_type", "same_security", "possible_duplicate"];

function effDecision(n: GraphNode): string {
  if (n.human_status === "APPROVED") return "AUTO_APPROVE";
  if (n.human_status === "REJECTED") return "REJECT";
  return n.decision ?? "HUMAN_REVIEW";
}
function decisionColor(d: string): string {
  if (d === "AUTO_APPROVE") return "#34d399";
  if (d === "REJECT") return "#f87171";
  return "#fbbf24";
}
function decisionLabel(d: string): string {
  if (d === "AUTO_APPROVE") return "Auto-aprovado";
  if (d === "REJECT") return "Rejeitado";
  return "Revisão humana";
}

type Pos = { x: number; y: number };

/** Deterministic force-directed layout (repulsion + edge springs + gravity). */
function computeLayout(nodes: GraphNode[], edges: GraphData["edges"]): { pos: Pos[]; idx: Map<string, number> } {
  const N = nodes.length;
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const W = 920;
  const H = 620;
  const pos: Pos[] = nodes.map((n, i) => {
    const a = (i / Math.max(1, N)) * Math.PI * 2;
    const r = n.kind === "entity" ? 110 : 250;
    return {
      x: W / 2 + Math.cos(a) * r + ((i * 53) % 44) - 22,
      y: H / 2 + Math.sin(a) * r + ((i * 31) % 44) - 22,
    };
  });
  const ideal = (t: GraphEdgeType) => (t === "belongs_to" ? 92 : t === "possible_duplicate" ? 150 : 172);
  const REP = 9500;
  const ITERS = 340;
  for (let it = 0; it < ITERS; it++) {
    const disp: Pos[] = pos.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = pos[i].x - pos[j].x;
        const dy = pos[i].y - pos[j].y;
        const d2 = dx * dx + dy * dy || 0.01;
        const d = Math.sqrt(d2);
        const f = REP / d2;
        const ux = dx / d;
        const uy = dy / d;
        disp[i].x += ux * f;
        disp[i].y += uy * f;
        disp[j].x -= ux * f;
        disp[j].y -= uy * f;
      }
    }
    for (const e of edges) {
      const a = idx.get(e.source);
      const b = idx.get(e.target);
      if (a === undefined || b === undefined) continue;
      const dx = pos[b].x - pos[a].x;
      const dy = pos[b].y - pos[a].y;
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = (d - ideal(e.type)) * 0.06;
      const ux = dx / d;
      const uy = dy / d;
      disp[a].x += ux * f;
      disp[a].y += uy * f;
      disp[b].x -= ux * f;
      disp[b].y -= uy * f;
    }
    for (let i = 0; i < N; i++) {
      disp[i].x += (W / 2 - pos[i].x) * 0.012;
      disp[i].y += (H / 2 - pos[i].y) * 0.012;
    }
    const maxStep = 18 * (1 - it / ITERS) + 1;
    for (let i = 0; i < N; i++) {
      const dl = Math.sqrt(disp[i].x * disp[i].x + disp[i].y * disp[i].y) || 0.01;
      const s = Math.min(dl, maxStep);
      pos[i].x += (disp[i].x / dl) * s;
      pos[i].y += (disp[i].y / dl) * s;
    }
  }
  return { pos, idx };
}

export default function GraphPanel({ project }: { project: Project }) {
  const [data, setData] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<GraphEdgeType>>(new Set());
  const [active, setActive] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    api.projectGraph(project.id).then(setData).catch((e) => setError(String(e)));
  }, [project.id]);

  const layout = useMemo(() => {
    if (!data) return null;
    return computeLayout(data.nodes, data.edges);
  }, [data]);

  const visibleEdges = useMemo(
    () => (data ? data.edges.filter((e) => !hidden.has(e.type)) : []),
    [data, hidden]
  );

  const adjacency = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of visibleEdges) {
      if (!m.has(e.source)) m.set(e.source, new Set());
      if (!m.has(e.target)) m.set(e.target, new Set());
      m.get(e.source)!.add(e.target);
      m.get(e.target)!.add(e.source);
    }
    return m;
  }, [visibleEdges]);

  if (error) return <div className="error">{error}</div>;
  if (!data || !layout) return <div className="empty">Carregando rastreabilidade…</div>;
  if (data.nodes.length === 0)
    return (
      <div className="empty">
        Sem documentos analisados. Rode a análise na aba <strong>Arquivos</strong>.
      </div>
    );

  const { pos, idx } = layout;
  const docs = data.nodes.filter((n) => n.kind === "document");
  const entities = data.nodes.filter((n) => n.kind === "entity");

  // entity size scales with how many documents reference it
  const docCount = new Map<string, number>();
  for (const d of docs) if (d.entity) docCount.set(d.entity, (docCount.get(d.entity) ?? 0) + 1);

  const bounds = pos.reduce(
    (b, p) => ({
      minX: Math.min(b.minX, p.x),
      minY: Math.min(b.minY, p.y),
      maxX: Math.max(b.maxX, p.x),
      maxY: Math.max(b.maxY, p.y),
    }),
    { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
  );
  const pad = 60;
  const viewBox = `${bounds.minX - pad} ${bounds.minY - pad} ${bounds.maxX - bounds.minX + pad * 2} ${
    bounds.maxY - bounds.minY + pad * 2
  }`;

  const focus = hover ?? active;
  const neighbors = focus ? adjacency.get(focus) ?? new Set<string>() : null;
  const isLit = (id: string) => !focus || id === focus || (neighbors?.has(id) ?? false);
  const edgeLit = (s: string, t: string) => !focus || s === focus || t === focus;

  const selected = active ? data.nodes[idx.get(active) ?? -1] : null;

  function toggle(t: GraphEdgeType) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  const dupCount = data.edges.filter((e) => e.type === "possible_duplicate").length;

  return (
    <>
      <div className="panel-bar">
        <div className="muted">
          {docs.length} documento{docs.length === 1 ? "" : "s"} · {entities.length} emissor
          {entities.length === 1 ? "" : "es"} · {data.edges.length} relaç{data.edges.length === 1 ? "ão" : "ões"}
          {dupCount > 0 && (
            <span className="dup-warn"> · {dupCount} possível{dupCount === 1 ? "" : "is"} duplicidade{dupCount === 1 ? "" : "s"}</span>
          )}
        </div>
        <div className="legend">
          {EDGE_ORDER.map((t) => {
            const st = EDGE_STYLE[t];
            const off = hidden.has(t);
            return (
              <button key={t} className={`legend-chip ${off ? "off" : ""}`} onClick={() => toggle(t)} title="Mostrar/ocultar">
                <svg width="22" height="10">
                  <line x1="1" y1="5" x2="21" y2="5" stroke={st.color} strokeWidth={st.width} strokeDasharray={st.dash} />
                </svg>
                {st.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="graph-wrap">
        <svg className="graph-svg" viewBox={viewBox} preserveAspectRatio="xMidYMid meet" onClick={() => setActive(null)}>
          {visibleEdges.map((e, i) => {
            const a = idx.get(e.source);
            const b = idx.get(e.target);
            if (a === undefined || b === undefined) return null;
            const st = EDGE_STYLE[e.type];
            return (
              <line
                key={i}
                x1={pos[a].x}
                y1={pos[a].y}
                x2={pos[b].x}
                y2={pos[b].y}
                stroke={st.color}
                strokeWidth={st.width}
                strokeDasharray={st.dash}
                opacity={edgeLit(e.source, e.target) ? 0.9 : 0.12}
              >
                {e.label && <title>{e.label}</title>}
              </line>
            );
          })}

          {entities.map((n) => {
            const p = pos[idx.get(n.id)!];
            const cnt = docCount.get(n.id) ?? 1;
            const s = 13 + Math.min(10, cnt * 2);
            const lit = isLit(n.id);
            return (
              <g
                key={n.id}
                className="gnode"
                opacity={lit ? 1 : 0.2}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onClick={(ev) => {
                  ev.stopPropagation();
                  setActive(n.id === active ? null : n.id);
                }}
              >
                <rect
                  x={p.x - s}
                  y={p.y - s}
                  width={s * 2}
                  height={s * 2}
                  transform={`rotate(45 ${p.x} ${p.y})`}
                  fill={n.known ? "#312e81" : "#3a2a13"}
                  stroke={n.known ? "#818cf8" : "#d97706"}
                  strokeWidth={active === n.id ? 3 : 1.8}
                />
                <text x={p.x} y={p.y - s - 8} textAnchor="middle" className="glabel entity">
                  {n.label}
                </text>
              </g>
            );
          })}

          {docs.map((n) => {
            const p = pos[idx.get(n.id)!];
            const dec = effDecision(n);
            const lit = isLit(n.id);
            return (
              <g
                key={n.id}
                className="gnode"
                opacity={lit ? 1 : 0.2}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onClick={(ev) => {
                  ev.stopPropagation();
                  setActive(n.id === active ? null : n.id);
                }}
              >
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={14}
                  fill={decisionColor(dec)}
                  stroke={active === n.id ? "#e6edf6" : "#0d1117"}
                  strokeWidth={active === n.id ? 3 : 1.5}
                />
                <text x={p.x} y={p.y + 28} textAnchor="middle" className="glabel">
                  {n.ticker || n.label}
                </text>
              </g>
            );
          })}
        </svg>

        <aside className="graph-detail">
          {selected ? (
            <NodeDetail node={selected} count={docCount.get(selected.id)} />
          ) : (
            <div className="muted detail-hint">
              <p>
                Cada <strong>círculo</strong> é um documento (cor = decisão); cada <strong>losango</strong> é um emissor.
                As linhas mostram como os documentos se relacionam.
              </p>
              <p>Passe o mouse para destacar conexões · clique para ver os detalhes · clique na legenda para filtrar.</p>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function NodeDetail({ node, count }: { node: GraphNode; count?: number }) {
  if (node.kind === "entity") {
    return (
      <div className="detail-card">
        <span className="kind-tag entity">Emissor</span>
        <h3>{node.label}</h3>
        <Row k="Ticker" v={node.ticker ?? "—"} />
        <Row k="Segmento" v={node.segment ?? "—"} />
        <Row k="Na base golden" v={node.known ? "Sim" : "Não"} />
        <Row k="Documentos" v={String(count ?? 0)} />
      </div>
    );
  }
  const dec = effDecision(node);
  return (
    <div className="detail-card">
      <span className="kind-tag">Documento</span>
      <h3>{node.label}</h3>
      <div className="detail-badge" style={{ background: decisionColor(dec) }}>
        {decisionLabel(dec)}
      </div>
      <Row k="Emissor" v={node.issuer ?? "—"} />
      <Row k="Ticker" v={node.ticker ?? "—"} />
      <Row k="ISIN" v={node.isin ?? "—"} />
      <Row k="Tipo de evento" v={node.event_type ?? "—"} />
      <Row k="Golden match" v={node.golden_status ?? "—"} />
      <Row k="Data quality" v={node.dq_score !== undefined ? `${(node.dq_score * 100).toFixed(0)}%` : "—"} />
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="detail-row">
      <span className="detail-k">{k}</span>
      <span className="detail-v">{v}</span>
    </div>
  );
}
