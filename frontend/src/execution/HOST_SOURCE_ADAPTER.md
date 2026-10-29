# Execution host source adapter

`bindExecutionHost` connects the existing execution mount to an injected host
context source. It does not run on import. The host owns authentication, routing,
order association and loading the actual workspace assets.

```js
import { bindExecutionHost } from './host-source-adapter.js';

const binding = bindExecutionHost({
  container,
  mountExecutionHost,
  hostSource,
  onError: error => showBindingFailure(error.code),
});
// Before removing the container:
binding.dispose();
```

The embedding application supplies these objects. The example does not create a
session, select an order or establish a backend connection.

## Source contract

The source provides `snapshot()` and `subscribe(listener)`. Subscription registers
the listener, emits its current event synchronously and returns an unsubscribe
function. The adapter does not also call `snapshot()`, which would duplicate the
first lifetime. A source whose subscription throws must clean up its listener.

An event contains `{generation, reason, context}`. Generation is a nonnegative
safe integer; older generations are ignored. Same-generation invalidation followed
by activation is allowed. `signed-out` and `context-changing` carry `context:null`
and synchronously clear the view. `disposed` clears and releases the binding.

`ready` and `association-unavailable` carry a context with a nonempty `sessionKey`,
`orderId` as a nonempty string or null, the original response-level `request`
function, and an optional nonempty `shipmentId`. Association-unavailable requires
`orderId:null`. Shipment selection is forwarded only with an order. A provider
purchase-order ID or a case ID is not automatically a local execution order ID.

The adapter copies only these agreed fields. The existing R6 mount retains its
wire-shape, UUID and same-order checks. The injected request must return the
original Response and honor caller and host lifetime cancellation through body
consumption. Parsed API payloads are not a response-level transport.

## Failure and disposal

Malformed events, invalid context and update errors clear the view and emit stable
error codes without exposing the source event or private error payload. If clearing
fails, the binding unmounts and stops accepting events. Diagnostics cannot prevent
invalidation. Disposal closes the binding before unsubscribing and always attempts
unmount, even when unsubscribe fails. It is idempotent and handles a disposed event
emitted before the subscription returns its cleanup function.

## Verification boundary

This stage publishes existing standalone consumer source without changing the R6
workspace or any application entry. The adapter-specific command is:

```sh
node --test tests/execution.host-source.test.mjs
```

On 2026-10-18, the exact test, adapter and package source from commit
`0c234d64dc88e897f2e952aae35d0aa4212f0ced` ran in an authorized remote Linux
environment using Node `v24.18.0`: 10 passed, 0 failed, 0 skipped, exit code 0.
These are synthetic adapter unit tests with controlled event delivery, not a
browser, backend, database or actual authenticated host acceptance run. No local
or Windows tests were executed for this verification, and the existing workspace
suite was not rerun.

The tests cover the synchronous initial event, same-generation activation,
stale callbacks, unavailable associations, sanitized failures, failed clearing,
subscription setup failures and idempotent disposal. Exact-head CI remains
separate from the required authorized-server evidence and real integration.
The host must provide authenticated read routing and a verified same-tenant
order association before a selected order becomes available.
