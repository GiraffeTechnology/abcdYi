import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

export default function ProjectDetail({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [tab, setTab] = useState<"overview" | "inquiry" | "form" | "timeline">("overview");

  useEffect(() => {
    apiFetch(`/api/projects/${projectId}`).then(setProject).catch(console.error);
  }, [projectId]);

  const loadTimeline = async () => {
    const events = await apiFetch(`/api/projects/${projectId}/timeline`);
    setTimeline(events);
    setTab("timeline");
  };

  if (!project) return <div>Loading...</div>;

  return (
    <div>
      <h2>{project.title}</h2>
      <p>Status: {project.status}</p>

      <div>
        <button onClick={() => setTab("overview")}>Overview</button>
        <button onClick={() => setTab("inquiry")}>Inquiry</button>
        <button onClick={() => setTab("form")}>Dynamic Form</button>
        <button onClick={loadTimeline}>Timeline</button>
      </div>

      {tab === "overview" && (
        <div>
          <p>Project ID: {project.id}</p>
          <p>Created: {new Date(project.created_at).toLocaleString()}</p>
        </div>
      )}

      {tab === "inquiry" && (
        <div>
          <a href={`/projects/${projectId}/inquiry`}>Go to Buyer Inquiry Intake</a>
        </div>
      )}

      {tab === "form" && (
        <div>
          <a href={`/projects/${projectId}/form`}>Go to Dynamic Order Form</a>
        </div>
      )}

      {tab === "timeline" && (
        <div>
          <h3>Timeline</h3>
          {timeline.map((e, i) => (
            <div key={i} style={{ borderBottom: "1px solid #eee", padding: 8 }}>
              <strong>{e.event_type}</strong>
              <span style={{ marginLeft: 16, color: "#666" }}>{e.occurred_at}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
