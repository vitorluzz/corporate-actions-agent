import { useState } from "react";
import AnalysisPanel from "./ReviewConsole";
import { api } from "./api";
import GraphPanel from "./GraphPanel";
import { DocumentationPanel, FilesPanel, ProjectHeader, ProjectsView, type Tab } from "./views";
import type { Project } from "./types";

type View = "projects" | Tab;

function defaultTab(p: Project): Tab {
  if (p.status === "DRAFT") return "files";
  if (p.status === "COMPLETED") return "documentation";
  return "analysis";
}

export default function App() {
  const [operator, setOperator] = useState("operador");
  const [view, setView] = useState<View>("projects");
  const [project, setProject] = useState<Project | null>(null);

  function openProject(p: Project) {
    setProject(p);
    setView(defaultTab(p));
  }
  function toProjects() {
    setProject(null);
    setView("projects");
  }
  async function refresh() {
    if (!project) return;
    try {
      setProject(await api.project(project.id));
    } catch {
      /* ignore */
    }
  }
  async function rename(name: string) {
    if (!project) return;
    try {
      setProject(await api.renameProject(project.id, name));
    } catch {
      /* ignore */
    }
  }
  async function remove() {
    if (!project) return;
    if (!window.confirm(`Excluir o projeto "${project.name}"? Isso apaga os documentos e a análise.`)) return;
    try {
      await api.deleteProject(project.id);
      toProjects();
    } catch {
      /* ignore */
    }
  }

  if (view === "projects" || !project) {
    return <ProjectsView operator={operator} setOperator={setOperator} onOpen={openProject} />;
  }

  return (
    <div className="app">
      <ProjectHeader
        project={project}
        tab={view}
        onTab={setView}
        onBack={toProjects}
        onRename={rename}
        onDelete={remove}
      />
      {view === "files" && (
        <FilesPanel
          project={project}
          onAnalyzed={async () => {
            await refresh();
            setView("analysis");
          }}
        />
      )}
      {view === "analysis" && (
        <AnalysisPanel
          project={project}
          operator={operator}
          onCompleted={async () => {
            await refresh();
            setView("documentation");
          }}
        />
      )}
      {view === "graph" && <GraphPanel project={project} />}
      {view === "documentation" && <DocumentationPanel project={project} />}
    </div>
  );
}
