import { object, RecordData } from "./store.js";

const record = (value: unknown): value is RecordData => value !== null && typeof value === "object" && !Array.isArray(value);
export const referenceId = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
const text = (value: unknown) => typeof value === "string" && value.length > 0;
const optionalText = (value: unknown) => value == null || typeof value === "string";
const date = (value: unknown) => {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return false;
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/.exec(value);
  if (!parts) return false;
  const [, year, month, day, hour, minute, second = "0"] = parts;
  const y = Number(year), m = Number(month), d = Number(day);
  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  // Date.parse can normalize impossible dates and 24:00 into another day.
  // Validate the supplied calendar fields without changing its timezone or value.
  return y >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= days[m - 1]
    && Number(hour) < 24 && Number(minute) < 60 && Number(second) < 60;
};
const optionalDate = (value: unknown) => value == null || date(value);
const optionalId = (value: unknown) => value == null || referenceId(value);

// Validate the wire types that this view relies on, not business-state enums.
// New fields and unknown status/event names are retained without interpretation.
export function orderResponse(value: unknown, orderId: string) {
  if (!record(value)) return false;
  return value.id === orderId && referenceId(value.id) && referenceId(value.project_id) && text(value.status)
    && date(value.created_at) && optionalText(value.order_number)
    && [value.approved_option_id, value.locked_form_version_id, value.buyer_participant_id].every(optionalId)
    && [value.confirmed_at, value.buyer_signed_off_at].every(optionalDate);
}
export function productionResponse(value: unknown) {
  if (!record(value) || !Array.isArray(value.milestones)) return false;
  if (!value.milestones.every(m => record(m) && referenceId(m.id) && text(m.milestone_type) && text(m.status)
    && [m.planned_date, m.predicted_date, m.actual_date].every(optionalDate) && optionalText(m.notes))) return false;
  const packet = value.monitoring_packet;
  return packet == null || (record(packet) && referenceId(packet.id) && text(packet.delay_risk_level)
    && optionalText(packet.recommended_action) && (packet.expedite_alert_required == null || typeof packet.expedite_alert_required === "boolean")
    && (packet.delayed_milestones == null || Array.isArray(packet.delayed_milestones)));
}
export function qcResponse(value: unknown, orderId: string) {
  return Array.isArray(value) && value.every(r => record(r) && referenceId(r.id) && r.order_id === orderId
    && text(r.result) && typeof r.rework_required === "boolean" && optionalId(r.responsible_participant_id)
    && optionalDate(r.inspected_at) && date(r.created_at));
}
export function eventsResponse(value: unknown, orderId: string) {
  return Array.isArray(value) && value.every(e => record(e) && referenceId(e.id) && e.order_id === orderId
    && referenceId(e.tenant_id) && optionalId(e.project_id) && optionalId(e.participant_id)
    && optionalId(e.triggered_by_user_id) && text(e.event_type) && record(e.payload) && date(e.occurred_at));
}
export function shipmentResponse(value: unknown, orderId: string, shipmentId: string) {
  if (!record(value) || value.id !== shipmentId || value.order_id !== orderId || !referenceId(value.id)) return false;
  return [value.estimated_departure_date, value.estimated_arrival_date, value.actual_departure_date, value.actual_arrival_date].every(optionalDate)
    && [value.carrier, value.tracking_number, value.trade_term, value.origin, value.destination].every(optionalText)
    && date(value.created_at) && Array.isArray(value.tracking_events)
    && value.tracking_events.every(e => record(e) && referenceId(e.id) && text(e.event_type) && date(e.occurred_at)
      && optionalText(e.location) && optionalText(e.description));
}
export function suppliedShipmentReferences(events: unknown, explicit?: string) {
  const values: unknown[] = [...(explicit === undefined ? [] : [explicit]), ...(Array.isArray(events) ? events.flatMap(e => {
    const payload = object(object(e).payload);
    return payload.shipment_id == null ? [] : [payload.shipment_id];
  }) : [])];
  return { ids: [...new Set(values.filter(referenceId))], invalidCount: values.filter(v => !referenceId(v)).length };
}
