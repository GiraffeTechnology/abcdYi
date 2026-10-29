/**
 * Consume the proposed ExecutionHostSource without owning host authentication,
 * routing, order association, or business writes. Inject the existing R6 mount.
 */
export function bindExecutionHost({ container, mountExecutionHost, hostSource, onError } = {}) {
  if (!container || typeof mountExecutionHost !== 'function'
      || !hostSource || typeof hostSource.snapshot !== 'function'
      || typeof hostSource.subscribe !== 'function'
      || (onError !== undefined && typeof onError !== 'function')) {
    throw new TypeError('An execution container, mount function and host source are required.');
  }

  const view = mountExecutionHost(container);
  if (!view || !['update', 'logout', 'unmount'].every(key => typeof view[key] === 'function')) {
    if (view && typeof view.unmount === 'function') view.unmount();
    throw new TypeError('The execution mount must return update, logout and unmount.');
  }

  let disposed = false;
  let generation = -1;
  let unsubscribe = null;

  // Do not expose host events, session objects, credentials or error payloads.
  function report(code) {
    if (!onError) return;
    const error = new Error('The execution host binding could not apply the current context.');
    error.name = 'ExecutionHostBindingError';
    error.code = code;
    try { onError(error); } catch { /* Diagnostics must not interrupt invalidation. */ }
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    const remove = unsubscribe;
    unsubscribe = null;
    try {
      if (remove) remove();
    } catch {
      report('UNSUBSCRIBE_FAILED');
    } finally {
      try { view.unmount(); } catch { report('UNMOUNT_FAILED'); }
    }
  }

  function clear() {
    try {
      view.logout();
    } catch {
      // A failed clear must never leave this binding accepting another order.
      dispose();
      report('CLEAR_FAILED');
    }
  }

  function unavailable(code) {
    clear();
    report(code);
  }

  function receive(event) {
    if (disposed) return;
    try {
      if (!event || !Number.isSafeInteger(event.generation) || event.generation < 0) {
        unavailable('INVALID_EVENT');
        return;
      }
      // Invalidation and activation may share a generation. Only older events
      // are discarded; a ready event must follow its same-generation null event.
      if (event.generation < generation) return;
      generation = event.generation;

      if (event.reason === 'disposed') {
        clear();
        dispose();
        return;
      }
      if (event.context === null) {
        if (event.reason !== 'signed-out' && event.reason !== 'context-changing') {
          unavailable('INVALID_EVENT');
          return;
        }
        clear();
        return;
      }

      const context = event.context;
      if ((event.reason !== 'ready' && event.reason !== 'association-unavailable')
          || !context || typeof context.sessionKey !== 'string' || !context.sessionKey.trim()
          || typeof context.request !== 'function'
          || (context.orderId !== null
              && (typeof context.orderId !== 'string' || !context.orderId.trim()))
          || (context.shipmentId !== undefined
              && (typeof context.shipmentId !== 'string' || !context.shipmentId.trim()))
          || (event.reason === 'association-unavailable' && context.orderId !== null)) {
        unavailable('INVALID_CONTEXT');
        return;
      }

      // Copy only the agreed fields. The request remains the host's original
      // Response-level function; do not parse/rebuild it or invent routing.
      const next = {
        sessionKey: context.sessionKey,
        orderId: context.orderId,
        request: context.request,
      };
      if (context.orderId !== null && context.shipmentId !== undefined) {
        next.shipmentId = context.shipmentId;
      }
      view.update(next);
    } catch {
      unavailable('UPDATE_FAILED');
    }
  }

  try {
    // subscribe supplies its first snapshot synchronously. Calling snapshot()
    // here as well would replay the current lifetime and duplicate its reads.
    const remove = hostSource.subscribe(receive);
    if (typeof remove !== 'function') {
      dispose();
      throw new TypeError('The host subscription must return an unsubscribe function.');
    }
    if (disposed) {
      // A disposed snapshot or failed clear may arrive before subscribe returns.
      try { remove(); } catch { report('UNSUBSCRIBE_FAILED'); }
    } else {
      unsubscribe = remove;
    }
  } catch (error) {
    dispose();
    throw error;
  }

  return Object.freeze({ dispose });
}
