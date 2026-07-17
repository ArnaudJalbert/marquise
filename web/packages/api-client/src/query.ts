type QueryValue = string | number | Date | string[] | undefined;

/**
 * Serializes a flat params object into a query string, skipping any key
 * whose value is `undefined` so optional filters can simply be omitted.
 * `Date` values are serialized via `.toISOString()`. `string[]` values are
 * serialized as repeated keys (`ids=a&ids=b`).
 */
export function buildQuery(params: object): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params) as Array<[string, QueryValue]>) {
    if (value === undefined) continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, item);
      continue;
    }
    search.set(key, value instanceof Date ? value.toISOString() : String(value));
  }

  const qs = search.toString();
  return qs.length > 0 ? `?${qs}` : "";
}
