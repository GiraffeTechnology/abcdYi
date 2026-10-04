const EXPLICIT_PORT = /^[a-z][a-z0-9+.-]*:\/\/[^/?#]*:(\d+)(?:[/?#]|$)/i;
// TCP 443 is owned by SSH on CTYun hosts and is never a web entry.
const RESERVED_PORT = 443;

/** Use only the operator-configured MyAivan entry; never infer a host or port. */
export function myAivanEntryUrl(configuredUrl?: string): string | null {
  if (!configuredUrl?.trim()) return null;
  const port = EXPLICIT_PORT.exec(configuredUrl.trim())?.[1];
  if (!port || Number(port) === RESERVED_PORT) return null;
  try {
    const url = new URL(configuredUrl.trim());
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    // Login belongs to MyAivan. Do not carry credentials or business data in URLs.
    if (url.username || url.password || url.search || url.hash) return null;
    return url.href;
  } catch {
    return null;
  }
}
