import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

const ROLES = [
  "BUYER","INTERMEDIARY","TRADING_COMPANY","MANUFACTURER",
  "FABRIC_SUPPLIER","TRIM_SUPPLIER","PACKAGING_SUPPLIER",
  "LOGISTICS_PROVIDER","FINANCE_SERVICE_PROVIDER","QC_INSPECTOR","PLATFORM_ADMIN"
];

export default function ParticipantDetail({ participantId }: { participantId: string }) {
  const [participant, setParticipant] = useState<any>(null);
  const [selectedRole, setSelectedRole] = useState(ROLES[0]);
  const [tab, setTab] = useState<"info" | "quality">("info");

  useEffect(() => {
    apiFetch(`/api/participants/${participantId}`).then(setParticipant).catch(console.error);
  }, [participantId]);

  const handleAssignRole = async () => {
    await apiFetch(`/api/participants/${participantId}/roles`, {
      method: "POST",
      body: JSON.stringify({ role_name: selectedRole }),
    });
  };

  if (!participant) return <div>Loading...</div>;

  return (
    <div>
      <h2>{participant.name}</h2>
      <p>Country: {participant.country}</p>
      <p>Email: {participant.contact_email}</p>
      <p>Completeness: {(participant.profile_completeness_score * 100).toFixed(0)}%</p>

      <div>
        <button onClick={() => setTab("info")}>Info</button>
        <button onClick={() => setTab("quality")}>Quality Ledger</button>
      </div>

      {tab === "info" && (
        <div>
          <h3>Assign Role</h3>
          <select value={selectedRole} onChange={e => setSelectedRole(e.target.value)}>
            {ROLES.map(r => <option key={r}>{r}</option>)}
          </select>
          <button onClick={handleAssignRole}>Assign</button>
        </div>
      )}

      {tab === "quality" && (
        <div>
          <h3>Quality Ledger</h3>
          <p>No records yet. (Populated in Iter 6)</p>
        </div>
      )}
    </div>
  );
}
