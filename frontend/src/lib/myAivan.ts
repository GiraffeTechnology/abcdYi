/** Use only the operator-configured MyAivan entry; never infer a host or port. */
export function myAivanEntryUrl(configuredUrl?: string): string | null {
  if (!configuredUrl?.trim()) return null;
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
