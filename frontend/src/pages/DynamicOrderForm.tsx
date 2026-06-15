import { useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

const STATUS_LABELS = {
  ai: { label: "AI Generated", color: "#f59e0b" },
  human: { label: "Human Confirmed", color: "#10b981" },
  missing: { label: "Missing", color: "#ef4444" },
};

export default function DynamicOrderForm({ projectId }: { projectId: string }) {
  const [version, setVersion] = useState<any>(null);
  const [edits, setEdits] = useState<Record<string, any>>({});
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [isStub, setIsStub] = useState(false);

  useEffect(() => {
    apiFetch(`/api/projects/${projectId}/dynamic-forms/current`)
      .then(v => {
        setVersion(v);
        setIsStub(v.fields?._stub === true);
      })
      .catch(console.error);
  }, [projectId]);

  const getFieldStatus = (fieldName: string) => {
    if (!version) return "missing";
    if (version.human_confirmed_fields?.includes(fieldName)) return "human";
    if (version.ai_generated_fields?.includes(fieldName)) return "ai";
    if (version.missing_fields?.includes(fieldName)) return "missing";
    return "ai";
  };

  const handleSave = async () => {
    const resp = await apiFetch(`/api/dynamic-forms/${version.form_id}`, {
      method: "PATCH",
      body: JSON.stringify({ field_updates: edits, confirmed_fields: confirmed }),
    });
    setVersion(resp);
    setEdits({});
    setConfirmed([]);
  };

  if (!version) return <div>No form found for this project.</div>;

  const fields = version.fields || {};
  const displayFields = Object.entries(fields).filter(
    ([k]) => !k.startsWith("_") && k !== "clarification_questions" && k !== "missing_fields"
  );

  return (
    <div>
      <h2>Dynamic Order Form — v{version.version_number}</h2>
      {isStub && (
        <div style={{ background: "#fef3c7", padding: 12, marginBottom: 16 }}>
          LLM not configured — all fields require manual input.
        </div>
      )}
      {displayFields.map(([fieldName, value]) => {
        const status = getFieldStatus(fieldName);
        const s = STATUS_LABELS[status as keyof typeof STATUS_LABELS];
        return (
          <div key={fieldName} style={{ marginBottom: 12 }}>
            <label>
              <strong>{fieldName}</strong>
              <span style={{ marginLeft: 8, color: s.color, fontSize: 12 }}>{s.label}</span>
            </label>
            <input
              style={{ display: "block", width: "100%" }}
              value={edits[fieldName] ?? (value as string) ?? ""}
              onChange={e => setEdits(prev => ({ ...prev, [fieldName]: e.target.value }))}
            />
            <label>
              <input
                type="checkbox"
                checked={confirmed.includes(fieldName)}
                onChange={e => {
                  if (e.target.checked) setConfirmed(prev => [...prev, fieldName]);
                  else setConfirmed(prev => prev.filter(f => f !== fieldName));
                }}
              />
              Confirm
            </label>
          </div>
        );
      })}
      <button onClick={handleSave}>Save & Confirm Fields</button>
      {version.missing_fields?.length > 0 && (
        <div style={{ marginTop: 16, color: "#ef4444" }}>
          <strong>Missing required fields:</strong>
          <ul>{version.missing_fields.map((f: string) => <li key={f}>{f}</li>)}</ul>
        </div>
      )}
      {fields.clarification_questions?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong>Clarification questions:</strong>
          <ul>{fields.clarification_questions.map((q: string, i: number) => <li key={i}>{q}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
