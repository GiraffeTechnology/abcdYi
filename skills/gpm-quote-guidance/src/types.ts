export interface QuoteGuidanceRequest {
  tenant_id?: string;
  project_id?: string;
  rfq_id?: string;
  supplier_response_id?: string;
  evidence_ids?: string[];
  include_private_data?: boolean;
  operator_id?: string;
  runtime_mode?: string;
  request_context?: Record<string, unknown>;
}

export interface GPMQuoteGuidancePacket {
  packet_id: string;
  tenant_id: string | null;
  project_id: string | null;
  rfq_id: string | null;
  supplier_response_id: string | null;
  context_bundle_id: string | null;
  evidence_ids: string[];
  supplier_quote_position: string;
  recommendation: string;
  benchmark_range: Record<string, unknown>;
  negotiation_points: string[];
  buyer_quote_options: Record<string, unknown>[];
  runtime_profile: string;
  runtime_mode: string;
  context_retriever: string;
  data_mode: string;
  human_approval_required: true;
  operator_action_required: boolean;
  approval_status: "pending" | "approved" | "rejected" | "expired" | "superseded";
  audit_ref: string | null;
  created_at: string;
}

export interface QuoteGuidanceResponse {
  status: string;
  packet: GPMQuoteGuidancePacket;
  human_approval_required: true;
  operator_action_required: boolean;
}

export interface ApprovalRequest {
  operator_id: string;
  approval_note?: string;
  selected_option_id?: string;
}

export interface RejectionRequest {
  operator_id: string;
  approval_note?: string;
}

export interface ApprovalResponse {
  status: string;
  approval_record: {
    packet_id: string;
    operator_id: string;
    approval_status: string;
    approval_note: string;
    recorded_at: string;
    dispatched: false;
    dispatch_note: string;
  };
  dispatched: false;
  dispatch_note: string;
}

export interface SkillConfig {
  gpmApiBaseUrl: string;
  timeoutMs?: number;
}
