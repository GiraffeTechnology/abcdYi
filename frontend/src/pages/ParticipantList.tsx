import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

interface Participant {
  id: string;
  name: string;
  country: string | null;
  contact_email: string | null;
  is_active: boolean;
  profile_completeness_score: number;
}

export default function ParticipantList({ onSelect }: { onSelect: (id: string) => void }) {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    apiFetch("/api/participants").then(setParticipants).catch(console.error);
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiFetch("/api/participants", {
      method: "POST",
      body: JSON.stringify({ name, country, contact_email: email }),
    });
    const updated = await apiFetch("/api/participants");
    setParticipants(updated);
    setShowModal(false);
    setName(""); setCountry(""); setEmail("");
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>Participants</h2>
        <button onClick={() => setShowModal(true)}>Add Participant</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Name</th><th>Country</th><th>Email</th><th>Score</th><th>Active</th>
          </tr>
        </thead>
        <tbody>
          {participants.map(p => (
            <tr key={p.id} onClick={() => onSelect(p.id)} style={{ cursor: "pointer" }}>
              <td>{p.name}</td>
              <td>{p.country}</td>
              <td>{p.contact_email}</td>
              <td>{(p.profile_completeness_score * 100).toFixed(0)}%</td>
              <td>{p.is_active ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {showModal && (
        <div>
          <h3>Add Participant</h3>
          <form onSubmit={handleAdd}>
            <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} required />
            <input placeholder="Country" value={country} onChange={e => setCountry(e.target.value)} />
            <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
            <button type="submit">Create</button>
            <button type="button" onClick={() => setShowModal(false)}>Cancel</button>
          </form>
        </div>
      )}
    </div>
  );
}
