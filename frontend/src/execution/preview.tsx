import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { ExecutionWorkspace } from "./ExecutionWorkspace";
import { ReadTransport } from "./store";
import { createExecutionReadTransport } from "./transport";
declare global { interface Window { executionPreviewTransport?: ReadTransport } }
const responseTransport = createExecutionReadTransport((path, options) => fetch(path, options));
const get: ReadTransport = async (path, options) => {
  // Synthetic browser-test seam only; this preview is not the application entry.
  if (window.executionPreviewTransport) return window.executionPreviewTransport(path, options);
  return responseTransport(path, options);
};
function Preview() {
  const [orderId, setOrderId] = useState("00000000-0000-4000-8000-000000000001");
  const [authenticated, setAuthenticated] = useState(true);
  const [session, setSession] = useState(0);
  return <><p>Isolated component preview — synthetic fixtures only, not production acceptance.</p><nav aria-label="Synthetic preview controls"><button onClick={() => setOrderId("00000000-0000-4000-8000-000000000001")}>Select order A</button><button onClick={() => setOrderId("00000000-0000-4000-8000-000000000002")}>Select order B</button><button onClick={() => setAuthenticated(false)}>Sign out</button><button onClick={() => setAuthenticated(true)}>Sign in</button><button onClick={() => setSession(s => s + 1)}>Renew synthetic session</button></nav><ExecutionWorkspace orderId={orderId} sessionKey={authenticated ? `preview-session-${session}` : "signed-out"} authenticated={authenticated} get={get}/></>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><Preview/></React.StrictMode>);
