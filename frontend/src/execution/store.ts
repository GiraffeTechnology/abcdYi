export type RecordData = Record<string, unknown>;
export type ReadTransport = (path: string, options: { method: "GET"; signal: AbortSignal }) => Promise<unknown>;
export type Resource = { loading: boolean; data?: unknown; error?: string; httpStatus?: number };
export type Snapshot = { resources: Record<string, Resource>; access?: string };
export const object = (value: unknown): RecordData => value !== null && typeof value === "object" && !Array.isArray(value) ? value as RecordData : {};
export const rows = (value: unknown): RecordData[] => Array.isArray(value) ? value.map(object) : [];
export const display = (value: unknown): string => value === null || value === undefined || value === "" ? "Not supplied" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);

// One lifetime per selected order/session. The host retains authentication; no storage is used.
export class ExecutionStore {
  private controllers = new Set<AbortController>();
  private active = new Map<string, AbortController>();
  private versions = new Map<string, number>();
  private disposed = false;
  private lifetime = 0;
  private snapshot: Snapshot = { resources: {} };
  constructor(private readonly get: ReadTransport, private readonly notify: (state: Snapshot) => void, private readonly timeoutMs = 15000) {}
  private publish() { if (!this.disposed) this.notify({ ...this.snapshot, resources: { ...this.snapshot.resources } }); }
  activate() { this.disposed = false; this.lifetime++; this.snapshot = { resources: {} }; }
  async read(key: string, path: string, accept: (value: unknown) => boolean = () => true) {
    if (this.disposed || this.snapshot.access) return;
    const version = (this.versions.get(key) ?? 0) + 1;
    const lifetime = this.lifetime;
    this.versions.set(key, version);
    this.active.get(key)?.abort();
    const controller = new AbortController();
    this.active.set(key, controller);
    this.controllers.add(controller);
    this.snapshot.resources[key] = { loading: true };
    this.publish();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let onAbort: (() => void) | undefined;
    try {
      const aborted = new Promise<never>((_, reject) => { onAbort = () => reject(controller.signal.reason); controller.signal.addEventListener("abort", onAbort, { once: true }); });
      timer = setTimeout(() => controller.abort(new Error("timeout")), this.timeoutMs);
      const data = await Promise.race([this.get(path, { method: "GET", signal: controller.signal }), aborted]);
      if (this.disposed || lifetime !== this.lifetime || this.snapshot.access || this.versions.get(key) !== version) return;
      if (!accept(data)) throw new Error("contract");
      this.snapshot.resources[key] = { loading: false, data };
    } catch (error) {
      if (this.disposed || lifetime !== this.lifetime || this.snapshot.access || this.versions.get(key) !== version) return;
      const status = object(error).status;
      if (status === 401 || status === 403) {
        this.snapshot = { resources: {}, access: status === 401 ? "Session expired. Sign in again through the host application." : "Access denied. Contact the authorized project owner." };
        this.controllers.forEach(c => c.abort());
      } else {
        const httpErrors: Record<number, string> = {
          404: "Record not found or not available to this session.",
          409: "The server reported a conflict. Refresh the current record.",
          422: "The server rejected this record reference.",
          429: "Too many requests. Retry after the server rate limit clears.",
          503: "Service unavailable. Retry when the service recovers.",
        };
        this.snapshot.resources[key] = { loading: false, httpStatus: typeof status === "number" ? status : undefined,
          error: error instanceof Error && error.message === "contract" ? "Response does not match this order or the expected API shape." : error instanceof Error && error.message === "timeout" ? "Request timed out." : typeof status === "number" && httpErrors[status] ? httpErrors[status] : "Request failed. Retry when the service is available." };
      }
    } finally {
      clearTimeout(timer);
      if (onAbort) controller.signal.removeEventListener("abort", onAbort);
      this.controllers.delete(controller);
      if (this.active.get(key) === controller) this.active.delete(key);
      if (lifetime === this.lifetime) this.publish();
    }
  }
  dispose() { this.disposed = true; this.controllers.forEach(c => c.abort()); this.controllers.clear(); this.active.clear(); this.snapshot = { resources: {} }; }
}

export function shipmentIds(events: unknown, explicit?: string): string[] {
  return [...new Set([...(explicit ? [explicit] : []), ...rows(events).flatMap(e => {
    const id = object(e.payload).shipment_id;
    return typeof id === "string" && id ? [id] : [];
  })])];
}
