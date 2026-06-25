import type {
  ApprovalRequest,
  ApprovalResponse,
  QuoteGuidanceRequest,
  QuoteGuidanceResponse,
  RejectionRequest,
  SkillConfig,
} from "./types";

export class GPMApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(config: SkillConfig) {
    this.baseUrl = config.gpmApiBaseUrl.replace(/\/$/, "");
    this.timeoutMs = config.timeoutMs ?? 30_000;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`GPM API error ${res.status}: ${text.slice(0, 200)}`);
      }
      return res.json() as Promise<T>;
    } finally {
      clearTimeout(timer);
    }
  }

  async healthz(): Promise<{ status: string }> {
    return this.request("GET", "/api/gpm/healthz");
  }

  async createQuoteGuidance(req: QuoteGuidanceRequest): Promise<QuoteGuidanceResponse> {
    return this.request("POST", "/api/gpm/quote-guidance", req);
  }

  async getQuoteGuidance(packetId: string): Promise<QuoteGuidanceResponse> {
    return this.request("GET", `/api/gpm/quote-guidance/${packetId}`);
  }

  async approveQuoteGuidance(
    packetId: string,
    req: ApprovalRequest,
  ): Promise<ApprovalResponse> {
    return this.request("POST", `/api/gpm/quote-guidance/${packetId}/approve`, {
      ...req,
      approval_status: "approved",
    });
  }

  async rejectQuoteGuidance(
    packetId: string,
    req: RejectionRequest,
  ): Promise<ApprovalResponse> {
    return this.request("POST", `/api/gpm/quote-guidance/${packetId}/reject`, {
      ...req,
      approval_status: "rejected",
    });
  }
}
