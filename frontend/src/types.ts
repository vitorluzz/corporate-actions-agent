// Types mirroring the backend data contract (app/domain/schemas.py).

export interface Confidence {
  p_correct: number;
  p_uncertain: number;
  p_error: number;
}

export interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  coord_system: string;
}

export interface Evidence {
  source: string;
  quote: string | null;
  page: number | null;
  bbox: BBox | null;
  char_span: [number, number] | null;
  match_score: number | null;
}

export interface ExtractedField {
  name: string;
  value: string | null;
  confidence: Confidence;
  evidence: Evidence | null;
  grounded: boolean;
  rationale: string;
}

export interface GuardrailResult {
  name: string;
  status: "PASS" | "WARN" | "FAIL" | "NA";
  severity: string;
  message: string;
  fields: string[];
}

export interface GoldenMatch {
  status: string;
  matched_on: string[];
  discrepancies: { field: string; extracted: string | null; reference: string | null; note: string }[];
  explanation: string;
  golden_emissor: string | null;
  golden_isin: string | null;
  golden_ticker: string | null;
}

export interface DQScore {
  score: number;
  components: Record<string, number>;
}

export interface EventTypeDistribution {
  distribution: Record<string, number>;
  argmax: string;
  entropy: number;
  confidence: number;
  samples: number;
}

export interface Routing {
  decision: "AUTO_APPROVE" | "HUMAN_REVIEW" | "REJECT";
  reasons: string[];
  required_human_actions: string[];
}

export interface DocumentResult {
  document: {
    id: string;
    source_file: string;
    pages: number;
    doc_class: string;
    extraction_method: string;
    model: string;
    run_id: string;
    doc_hash: string;
  };
  record: Record<string, string | null>;
  event_type: EventTypeDistribution;
  fields: ExtractedField[];
  validation: {
    golden_match: GoldenMatch;
    coherence_checks: GuardrailResult[];
    dq_score: DQScore;
  };
  routing: Routing;
  audit: {
    created_at: string;
    sampling: { n: number; temperature: number };
    tool_calls: { tool: string; result_summary: string }[];
    versions: Record<string, string>;
  };
  human_status?: string | null;
}

export interface DocumentListItem {
  id: string;
  source_file: string;
  doc_class: string;
  event_type: string;
  decision: Routing["decision"];
  human_status: string | null;
  dq_score: number;
}

export interface RunSummary {
  run_id: string;
  total: number;
  auto_approved: number;
  review: number;
  rejected: number;
  auto_rate: number;
  avg_confidence: number;
  type_mix: Record<string, number>;
  flag_reasons_histogram: Record<string, number>;
}

export interface AuditEvent {
  id: number;
  ts: string;
  actor: string;
  action: string;
  detail: Record<string, unknown>;
}

export type ProjectStatus = "DRAFT" | "ANALYZING" | "REVIEW" | "COMPLETED";

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  operator: string | null;
  created_at: string;
  total: number;
  decided: number;
  pending: number;
}

export interface ProjectFile {
  name: string;
  size: number;
}

export interface ProjectProgress {
  total: number;
  decided: number;
  pending: number;
}

export interface ProjectSummary extends RunSummary {
  progress: ProjectProgress;
}

export interface ReportDoc {
  id: string;
  source_file: string;
  decision: string;
  human_status: string | null;
  event_type: string;
  dq_score: number;
  record: Record<string, string | null>;
  golden_match: string;
  reasons: string[];
  corrections: { field: string; old: string | null; new: string }[];
  decisions: { actor: string; action: string; ts: string }[];
}

export interface ProjectReport {
  project: {
    id: string;
    name: string;
    status: string;
    operator: string | null;
    created_at: string | null;
    completed_at: string | null;
  };
  summary: { total: number; auto_approved: number; approved: number; rejected: number; corrections: number };
  documents: ReportDoc[];
  generated_at: string;
}

export interface GraphNode {
  id: string;
  kind: "document" | "entity";
  label: string;
  // document-only
  entity?: string;
  issuer?: string;
  ticker?: string | null;
  isin?: string | null;
  event_type?: string;
  decision?: string;
  human_status?: string | null;
  dq_score?: number;
  golden_status?: string;
  // entity-only
  segment?: string | null;
  known?: boolean;
}

export type GraphEdgeType =
  | "belongs_to"
  | "same_event_type"
  | "same_security"
  | "possible_duplicate";

export interface GraphEdge {
  source: string;
  target: string;
  type: GraphEdgeType;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
