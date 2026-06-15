import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

interface Project {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export default function ProjectList({ onSelect }: { onSelect: (id: string) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");

  useEffect(() => {
    apiFetch("/api/projects").then(setProjects).catch(console.error);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiFetch("/api/projects", { method: "POST", body: JSON.stringify({ title }) });
    const updated = await apiFetch("/api/projects");
    setProjects(updated);
    setShowModal(false);
    setTitle("");
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>Projects</h2>
        <button onClick={() => setShowModal(true)}>New Project</button>
      </div>
      <table>
        <thead>
          <tr><th>Title</th><th>Status</th><th>Created</th></tr>
        </thead>
        <tbody>
          {projects.map(p => (
            <tr key={p.id} onClick={() => onSelect(p.id)} style={{ cursor: "pointer" }}>
              <td>{p.title}</td>
              <td>{p.status}</td>
              <td>{new Date(p.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {showModal && (
        <div>
          <h3>New Project</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} required />
            <button type="submit">Create</button>
            <button type="button" onClick={() => setShowModal(false)}>Cancel</button>
          </form>
        </div>
      )}
    </div>
  );
}
