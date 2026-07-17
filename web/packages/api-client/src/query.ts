type QueryValue = string | number | Date | undefined;

/**
 * Serializes a flat params object into a query string, skipping any key
 * whose value is `undefined` so optional filters can simply be omitted.
 * `Date` values are serialized via `.toISOString()`.
 */
export function buildQuery(params: object): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params) as Array<[string, QueryValue]>) {
    if (value === undefined) continue;
    search.set(key, value instanceof Date ? value.toISOString() : String(value));
  }

  const qs = search.toString();
  return qs.length > 0 ? `?${qs}` : "";
}
