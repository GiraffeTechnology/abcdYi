import assert from 'node:assert/strict';
import test from 'node:test';
import { bindExecutionHost } from '../src/execution/host-source-adapter.js';

// Synthetic adapter-only fixtures. No backend, browser, credentials or business writes.
const ORDER_A = '00000000-0000-4000-8000-000000000001';
const ORDER_B = '00000000-0000-4000-8000-000000000002';
const SHIPMENT = '00000000-0000-4000-8000-000000000003';
const request = async () => { throw new Error('Synthetic transport must not be invoked.'); };
const invalidated = (generation, reason = 'context-changing') => ({ generation, reason, context: null });
const ready = (generation, orderId = ORDER_A, extra = {}) => ({
  generation,
  reason: 'ready',
  context: { sessionKey: 'synthetic-session', orderId, request, ...extra },
});

function harness(initial = invalidated(0, 'signed-out')) {
  let listener;
  const state = {
    visibleOrder: null,
    updates: [],
    errors: [],
    clears: 0,
    unmounts: 0,
    removals: 0,
    snapshots: 0,
    failUpdate: false,
    failClear: false,
    failRemove: false,
    failDiagnostic: false,
  };
  const source = {
    snapshot() { state.snapshots++; return initial; },
    subscribe(next) {
      listener = next;
      next(initial);
      return () => {
        state.removals++;
        if (state.failRemove) throw new Error('Synthetic unsubscribe detail.');
      };
    },
  };
  const view = {
    update(context) {
      if (state.failUpdate) throw new Error('Synthetic view detail.');
      state.updates.push(context);
      state.visibleOrder = context.orderId;
    },
    logout() {
      if (state.failClear) throw new Error('Synthetic clear detail.');
      state.clears++;
      state.visibleOrder = null;
    },
    unmount() { state.unmounts++; state.visibleOrder = null; },
  };
  const bind = () => bindExecutionHost({
    container: {},
    mountExecutionHost: () => view,
    hostSource: source,
    onError(error) {
      state.errors.push({ name: error.name, message: error.message, code: error.code });
      if (state.failDiagnostic) throw new Error('Synthetic diagnostic detail.');
    },
  });
  // Retain a queued callback deliberately, including after unsubscribe, to control
  // late-delivery interleavings without timers or a real source implementation.
  return { state, source, view, bind, deliver: event => listener(event) };
}

test('synchronous initial ready snapshot renders once and preserves the original request', () => {
  const h = harness(ready(1, ORDER_A, { shipmentId: SHIPMENT, unrelated: 'synthetic-extra' }));
  const binding = h.bind();
  assert.equal(h.state.visibleOrder, ORDER_A);
  assert.equal(h.state.updates.length, 1);
  assert.equal(h.state.snapshots, 0);
  assert.equal(h.state.updates[0].request, request);
  assert.deepEqual(Object.keys(h.state.updates[0]).sort(), ['orderId', 'request', 'sessionKey', 'shipmentId']);
  binding.dispose();
});

test('same-generation invalidation and activation allow a new order while older callbacks cannot restore data', () => {
  const h = harness(ready(1));
  const binding = h.bind();
  h.deliver(invalidated(2));
  assert.equal(h.state.visibleOrder, null);
  h.deliver(ready(2, ORDER_B));
  assert.equal(h.state.visibleOrder, ORDER_B);
  const updates = h.state.updates.length;
  h.deliver(ready(1));
  h.deliver(invalidated(1, 'signed-out'));
  assert.equal(h.state.visibleOrder, ORDER_B);
  assert.equal(h.state.updates.length, updates);
  h.deliver(invalidated(3, 'signed-out'));
  assert.equal(h.state.visibleOrder, null);
  h.deliver(ready(2));
  assert.equal(h.state.visibleOrder, null);
  binding.dispose();
});

test('association-unavailable does not select an order or forward a shipment', () => {
  const h = harness();
  const binding = h.bind();
  h.deliver({ ...ready(1, null, { shipmentId: SHIPMENT }), reason: 'association-unavailable' });
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.updates.length, 1);
  assert.equal(h.state.updates[0].request, request);
  assert.equal('shipmentId' in h.state.updates[0], false);
  h.deliver({ ...ready(2), reason: 'association-unavailable' });
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.updates.length, 1);
  assert.equal(h.state.errors.at(-1).code, 'INVALID_CONTEXT');
  binding.dispose();
});

test('invalid events and malformed context clear previous records and expose only stable diagnostics', () => {
  const h = harness(ready(1));
  const binding = h.bind();
  h.deliver({ generation: 2, reason: 'ready', context: { orderId: ORDER_B, detail: 'synthetic-context-detail' } });
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.errors.at(-1).code, 'INVALID_CONTEXT');
  h.deliver(ready(3));
  h.deliver({ generation: -1, reason: 'ready', context: null });
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.errors.at(-1).code, 'INVALID_EVENT');
  assert.equal(JSON.stringify(h.state.errors).includes('synthetic-context-detail'), false);
  assert.ok(h.state.errors.every(error => error.name === 'ExecutionHostBindingError'));
  binding.dispose();
});

test('an update failure clears the previous order without exposing the thrown view detail', () => {
  const h = harness(ready(1));
  const binding = h.bind();
  h.state.failUpdate = true;
  h.deliver(ready(2, ORDER_B));
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.errors.at(-1).code, 'UPDATE_FAILED');
  assert.equal(JSON.stringify(h.state.errors).includes('Synthetic view detail'), false);
  binding.dispose();
});

test('a failed clear unmounts and prevents later orders even if diagnostics throw', () => {
  const h = harness(ready(1));
  const binding = h.bind();
  h.state.failClear = true;
  h.state.failDiagnostic = true;
  assert.doesNotThrow(() => h.deliver(invalidated(2, 'signed-out')));
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.removals, 1);
  const updates = h.state.updates.length;
  h.deliver(ready(3, ORDER_B));
  assert.equal(h.state.updates.length, updates);
  assert.equal(h.state.errors.at(-1).code, 'CLEAR_FAILED');
  binding.dispose();
  assert.equal(h.state.unmounts, 1);
});

test('a disposed first synchronous event releases the unsubscribe handle returned afterwards', () => {
  const h = harness({ generation: 0, reason: 'disposed', context: null });
  const binding = h.bind();
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.removals, 1);
  h.deliver(ready(1));
  assert.equal(h.state.updates.length, 0);
  binding.dispose();
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.removals, 1);
});

test('dispose remains idempotent and unmounts when unsubscribe throws', () => {
  const h = harness(ready(1));
  const binding = h.bind();
  h.state.failRemove = true;
  assert.doesNotThrow(() => binding.dispose());
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.removals, 1);
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.errors.at(-1).code, 'UNSUBSCRIBE_FAILED');
  h.deliver(ready(2, ORDER_B));
  assert.equal(h.state.updates.length, 1);
  binding.dispose();
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.removals, 1);
});

test('subscription setup failure unmounts the view and preserves the setup failure', () => {
  const h = harness();
  h.source.subscribe = () => { throw new Error('Synthetic subscription failure.'); };
  assert.throws(h.bind, /Synthetic subscription failure/);
  assert.equal(h.state.unmounts, 1);
  assert.equal(h.state.visibleOrder, null);
});

test('missing unsubscribe handle fails setup and ignores a queued late event', () => {
  const h = harness();
  let deliver;
  h.source.subscribe = listener => { deliver = listener; listener(ready(1)); };
  assert.throws(h.bind, /unsubscribe function/);
  assert.equal(h.state.visibleOrder, null);
  assert.equal(h.state.unmounts, 1);
  deliver(ready(2, ORDER_B));
  assert.equal(h.state.updates.length, 1);
  assert.equal(h.state.visibleOrder, null);
});
