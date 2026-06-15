import { useState } from "react";
import { apiFetch } from "../lib/apiClient";

export default function BuyerInquiryIntake({ projectId }: { projectId: string }) {
  const [rawText, setRawText] = useState("");
  const [inquiryId, setInquiryId] = useState<string | null>(null);
  const [formGenerated, setFormGenerated] = useState(false);
  const [error, setError] = useState("");

  const handleImport = async () => {
    setError("");
    try {
      const inquiry = await apiFetch(`/api/projects/${projectId}/buyer-inquiries`, {
        method: "POST",
        body: JSON.stringify({ raw_text: rawText }),
      });
      setInquiryId(inquiry.id);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleGenerateForm = async () => {
    if (!inquiryId) return;
    try {
      await apiFetch(`/api/projects/${projectId}/dynamic-forms`, {
        method: "POST",
        body: JSON.stringify({ inquiry_id: inquiryId }),
      });
      setFormGenerated(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h2>Buyer Inquiry Intake</h2>
      <textarea
        rows={10}
        style={{ width: "100%" }}
        placeholder="Paste buyer inquiry text here..."
        value={rawText}
        onChange={e => setRawText(e.target.value)}
      />
      <button onClick={handleImport} disabled={!rawText}>Import Inquiry</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {inquiryId && (
        <div>
          <p>Inquiry ID: {inquiryId}</p>
          {!formGenerated ? (
            <button onClick={handleGenerateForm}>Generate Dynamic Form</button>
          ) : (
            <p style={{ color: "green" }}>Dynamic form generated!</p>
          )}
        </div>
      )}
    </div>
  );
}
