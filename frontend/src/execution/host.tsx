import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import { ExecutionWorkspace } from "./ExecutionWorkspace";
import { createExecutionReadTransport } from "./transport";

// The embedding host owns login, tenant selection and the selected persisted order.
// This boundary accepts its existing authenticated request, never credentials.
export type ExecutionHostContext = {
  sessionKey: string;
  orderId: string | null;
  shipmentId?: string;
  request: (path: string, options: { method: "GET"; signal: AbortSignal }) => Promise<Response>;
};

export function mountExecutionHost(container: HTMLElement) {
  const root = createRoot(container);
  let generation = 0;
  let closed = false;
  const assertOpen = () => { if (closed) throw new Error("Execution host has been unmounted."); };
  const signedOut = () => <p role="status">Signed out. No execution records are retained.</p>;
  flushSync(() => root.render(signedOut()));
  return {
    update(context: ExecutionHostContext) {
      assertOpen();
      if (!context.sessionKey.trim()) throw new Error("An authenticated host session key is required.");
      const get = createExecutionReadTransport(context.request);
      // Every host update creates a new lifetime, including transport/backend changes.
      // flushSync removes prior records before control returns to logout/session code.
      const key = `${++generation}:${context.sessionKey}`;
      flushSync(() => root.render(<ExecutionWorkspace key={key} sessionKey={key} authenticated orderId={context.orderId} shipmentId={context.shipmentId} get={get} />));
    },
    logout() { assertOpen(); generation++; flushSync(() => root.render(signedOut())); },
    unmount() { if (!closed) { closed = true; root.unmount(); } },
  };
}
