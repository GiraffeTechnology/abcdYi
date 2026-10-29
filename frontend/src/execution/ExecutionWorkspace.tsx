import { useEffect, useMemo, useState } from "react";
import { display, ExecutionStore, object, ReadTransport, rows, Snapshot } from "./store";
import { eventsResponse, orderResponse, productionResponse, qcResponse, referenceId, shipmentResponse, suppliedShipmentReferences } from "./contracts";
import "./execution.css";

export type ExecutionWorkspaceProps = { orderId: string | null; sessionKey: string; authenticated: boolean; get: ReadTransport; shipmentId?: string };
export function ExecutionWorkspace(props: ExecutionWorkspaceProps) {
  if (!props.authenticated) return <p role="status">Signed out. No execution records are retained.</p>;
  if (!props.orderId) return <p role="status">Select a confirmed order in the host application.</p>;
  if (!referenceId(props.orderId)) return <p role="alert">Invalid order reference. Select an order supplied by the host application.</p>;
  return <SelectedOrder key={JSON.stringify([props.sessionKey, props.orderId])} {...props} orderId={props.orderId} />;
}
function SelectedOrder(props: ExecutionWorkspaceProps & { orderId: string }) {
  const [refreshGeneration, setRefreshGeneration] = useState(0);
  const [filter, setFilter] = useState("");
  return <OrderEvidence key={refreshGeneration} {...props} filter={filter} setFilter={setFilter} onRefresh={() => setRefreshGeneration(value => value + 1)} />;
}
function OrderEvidence({ orderId, get, shipmentId, filter, setFilter, onRefresh }: ExecutionWorkspaceProps & { orderId: string; filter: string; setFilter: (value: string) => void; onRefresh: () => void }) {
  const [state, setState] = useState<Snapshot>({ resources: {} });
  const store = useMemo(() => new ExecutionStore(get, setState), [get]);
  const base = `/api/orders/${encodeURIComponent(orderId)}`;
  useEffect(() => { store.activate(); void store.read("order", base, v => orderResponse(v, orderId)); return () => store.dispose(); }, [store, base, orderId]);
  const order = object(state.resources.order?.data);
  const authorized = order.id === orderId;
  useEffect(() => {
    if (!authorized) return;
    void store.read("production", `${base}/production-monitoring`, productionResponse);
    void store.read("qc", `${base}/qc-records`, v => qcResponse(v, orderId));
    void store.read("events", `/api/execution-graph/orders/${encodeURIComponent(orderId)}`, v => eventsResponse(v, orderId));
  }, [authorized, store, base, orderId]);
  const events = rows(state.resources.events?.data).slice().sort((a, b) => {
    const left = Date.parse(display(a.occurred_at)), right = Date.parse(display(b.occurred_at));
    return Number.isFinite(left) && Number.isFinite(right) ? left - right : 0;
  });
  const eventTypes = [...new Set(events.map(e => display(e.event_type)))];
  const effectiveFilter = eventTypes.includes(filter) ? filter : "";
  const eventTypesKey = JSON.stringify(eventTypes);
  useEffect(() => {
    if (state.resources.events?.data !== undefined && filter && !eventTypes.includes(filter)) setFilter("");
  }, [state.resources.events?.data, filter, eventTypesKey]);
  const references = suppliedShipmentReferences(state.resources.events?.data, shipmentId);
  const ids = references.ids;
  const idsKey = JSON.stringify(ids);
  useEffect(() => { if (authorized) ids.forEach(id => { void store.read(`shipment:${id}`, `/api/shipments/${encodeURIComponent(id)}`, v => shipmentResponse(v, orderId, id)); }); }, [store, authorized, idsKey, orderId]);
  const panel = (key: string, title: string, path: string, content: React.ReactNode, accept?: (v: unknown) => boolean) => {
    const resource = state.resources[key];
    return <section aria-label={title}><h2>{title}</h2>{resource?.loading ? <p role="status">Loading {title.toLowerCase()}…</p> : resource?.error ? <><p role="alert">{resource.error}</p><button onClick={() => void store.read(key, path, accept)}>Retry {title.toLowerCase()}</button></> : resource?.data !== undefined ? content : <p>Not loaded.</p>}</section>;
  };
  if (state.access) return <p role="alert">{state.access}</p>;
  const production = object(state.resources.production?.data);
  return <main className="execution-workspace"><header><h1>Apparel fulfillment evidence</h1><p>Read-only records for order {orderId}</p><button onClick={onRefresh}>Refresh from API</button></header>
    {panel("order", "Order summary", base, <><dl>{["order_number", "status", "project_id", "approved_option_id", "locked_form_version_id", "confirmed_at", "buyer_signed_off_at"].map(k => <div key={k}><dt>{k.replace(/_/g, " ")}</dt><dd>{display(order[k])}</dd></div>)}</dl><p>{order.buyer_signed_off_at ? "Buyer sign-off recorded by API." : "Buyer sign-off not recorded. Carrier delivery does not constitute buyer acceptance."}</p></>, v => orderResponse(v, orderId))}
    {authorized && <>
      {panel("production", "Production", `${base}/production-monitoring`, <><RecordTable records={rows(production.milestones)} columns={["milestone_type", "status", "planned_date", "predicted_date", "actual_date", "notes"]} /><Details title="Latest monitoring packet (returned analysis, not recalculated)" data={production.monitoring_packet} /></>, productionResponse)}
      {panel("qc", "QC history", `${base}/qc-records`, <><p>All returned records remain visible, including failures and required rework. Only returned evidence metadata is displayed; media review and QC decisions are outside this read-only view.</p><RecordTable records={rows(state.resources.qc?.data)} columns={["id", "result", "rework_required", "responsible_participant_id", "inspected_at", "created_at"]} />{rows(state.resources.qc?.data).map(r => <div key={display(r.id)}>{["photo_evidence_metadata", "inspection_report_metadata"].filter(k => r[k] != null).map(k => <Details key={k} title={`QC ${display(r.id)}: ${k.replace(/_/g, " ")}`} data={r[k]} />)}</div>)}</>, v => qcResponse(v, orderId))}
      <section aria-label="Logistics"><h2>Logistics</h2>{references.invalidCount > 0 && <p role="alert">Some supplied shipment references do not match the API UUID format. No request is made for those references.</p>}{!ids.length && <p>No shipment reference returned. No shipment scan or unverified order-list request is performed.</p>}{ids.map(id => <div key={id}>{panel(`shipment:${id}`, `Shipment ${id}`, `/api/shipments/${encodeURIComponent(id)}`, <><RecordTable records={[object(state.resources[`shipment:${id}`]?.data)]} columns={["carrier", "tracking_number", "trade_term", "origin", "destination", "estimated_departure_date", "estimated_arrival_date", "actual_departure_date", "actual_arrival_date"]} /><RecordTable records={rows(object(state.resources[`shipment:${id}`]?.data).tracking_events)} columns={["event_type", "location", "description", "occurred_at"]} /><Details title="Returned logistics risk flags" data={object(state.resources[`shipment:${id}`]?.data).logistics_risk_flags} /><p>Delivery events are not buyer sign-off.</p></>, v => shipmentResponse(v, orderId, id))}</div>)}</section>
      {panel("events", "Fulfillment history", `/api/execution-graph/orders/${encodeURIComponent(orderId)}`, <><label>Event type <select value={effectiveFilter} onChange={e => setFilter(e.target.value)}><option value="">All events</option>{eventTypes.map(t => <option key={t}>{t}</option>)}</select></label>{events.filter(e => !effectiveFilter || display(e.event_type) === effectiveFilter).map((e, i) => <article key={display(e.id) + i}><h3>{display(e.event_type)}</h3><p>{display(e.occurred_at)} · Actor: {display(e.triggered_by_user_id)} · Event: {display(e.id)}</p><Details title="Event payload, source, version and correction references (as supplied)" data={e.payload} /></article>)}{!events.length && <p>No execution events returned.</p>}</>, v => eventsResponse(v, orderId))}
    </>}
  </main>;
}
function RecordTable({ records, columns }: { records: ReturnType<typeof rows>; columns: string[] }) {
  if (!records.length) return <p>No records returned.</p>;
  return <div className="execution-scroll" tabIndex={0} aria-label="Scrollable evidence table"><table><thead><tr>{columns.map(c => <th key={c} scope="col">{c.replace(/_/g, " ")}</th>)}</tr></thead><tbody>{records.map((r, i) => <tr key={i}>{columns.map(c => <td key={c}>{display(r[c])}</td>)}</tr>)}</tbody></table></div>;
}
function Details({ title, data }: { title: string; data: unknown }) { return <details><summary>{title}</summary><pre>{display(data)}</pre></details>; }
