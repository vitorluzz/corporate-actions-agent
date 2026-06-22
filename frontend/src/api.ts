import type {
  AuditEvent,
  DocumentListItem,
  DocumentResult,
  GraphData,
  Project,
  ProjectFile,
  ProjectReport,
  ProjectSummary,
  RunSummary,
} from "./types";

const API = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await errText(res));
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await errText(res));
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errText(res));
  return res.json() as Promise<T>;
}

async function errText(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return (j as any).detail ?? `${res.status} ${res.statusText}`;
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

/** Fetch a binary endpoint and trigger a browser download with the given filename. */
async function downloadBlob(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(await errText(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export interface ReviewBody {
  actor: string;
  decision: "approve" | "reject" | "save";
  field_corrections: Record<string, string>;
  note: string;
}

export const api = {
  apiBase: API,
  // per-document (work with project-scoped ids)
  document: (id: string) => get<DocumentResult>(`/documents/${id}`),
  audit: (id: string) => get<AuditEvent[]>(`/documents/${id}/audit`),
  pageImageUrl: (id: string) => `${API}/documents/${id}/page.png`,
  review: (id: string, body: ReviewBody) =>
    post<DocumentResult>(`/documents/${id}/review`, body),

  // projects
  createProject: (name: string, operator: string) =>
    post<Project>("/projects", { name, operator }),
  projects: () => get<Project[]>("/projects"),
  project: (pid: string) => get<Project>(`/projects/${pid}`),
  renameProject: (pid: string, name: string) => patch<Project>(`/projects/${pid}`, { name }),
  deleteProject: (pid: string) => del<{ deleted: string }>(`/projects/${pid}`),
  projectFiles: (pid: string) => get<{ files: ProjectFile[] }>(`/projects/${pid}/files`),
  loadSamples: (pid: string) => post<{ files: ProjectFile[] }>(`/projects/${pid}/files/samples`),
  deleteFile: (pid: string, name: string) =>
    del<{ files: ProjectFile[] }>(`/projects/${pid}/files/${encodeURIComponent(name)}`),
  uploadFiles: async (pid: string, files: File[]): Promise<{ files: ProjectFile[] }> => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    const res = await fetch(`${API}/projects/${pid}/files`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await errText(res));
    return res.json();
  },
  analyze: (pid: string) => post<RunSummary>(`/projects/${pid}/analyze`),
  projectDocuments: (pid: string) => get<DocumentListItem[]>(`/projects/${pid}/documents`),
  projectSummary: (pid: string) => get<ProjectSummary>(`/projects/${pid}/summary`),
  completeProject: (pid: string) => post<ProjectReport>(`/projects/${pid}/complete`),
  projectReport: (pid: string) => get<ProjectReport>(`/projects/${pid}/report`),
  projectGraph: (pid: string) => get<GraphData>(`/projects/${pid}/graph`),
  certificatePdf: (id: string, filename: string) =>
    downloadBlob(`/documents/${id}/certificate.pdf`, filename),
  projectReportPdf: (pid: string, filename: string) =>
    downloadBlob(`/projects/${pid}/report.pdf`, filename),
};
