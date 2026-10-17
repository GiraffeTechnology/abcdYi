import { ReadTransport } from "./store";

export class ExecutionHttpError extends Error {
  constructor(readonly status: number) { super(`Execution API returned HTTP ${status}`); this.name = "ExecutionHttpError"; }
}

// The host supplies its authenticated response-level request function.
// This adapter stores no credentials and never reads an HTTP error body.
export function createExecutionReadTransport(request: (path: string, options: { method: "GET"; signal: AbortSignal }) => Promise<Response>): ReadTransport {
  return async (path, options) => {
    const response = await request(path, { method: "GET", signal: options.signal });
    if (!response.ok) throw new ExecutionHttpError(response.status);
    return response.json();
  };
}
