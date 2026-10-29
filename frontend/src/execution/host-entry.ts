import { mountExecutionHost } from "./host";

declare global { interface Window { executionHost: ReturnType<typeof mountExecutionHost> } }
window.executionHost = mountExecutionHost(document.getElementById("root")!);
