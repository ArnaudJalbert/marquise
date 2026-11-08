export const CATALOGUE_TIME_FILTERS = [
  { value: "matinee", label: "Matinée", start: 0, end: 17 },
  { value: "evening", label: "Evening", start: 17, end: 21 },
  { value: "late", label: "Late", start: 21, end: 24 },
] as const;

export type CatalogueTimeFilterValue =
  (typeof CATALOGUE_TIME_FILTERS)[number]["value"];

export function isCatalogueTimeFilterValue(
  value: string,
): value is CatalogueTimeFilterValue {
  return CATALOGUE_TIME_FILTERS.some((filter) => filter.value === value);
}

export function getCatalogueTimeFilter(value: CatalogueTimeFilterValue) {
  return CATALOGUE_TIME_FILTERS.find((filter) => filter.value === value)!;
}

export function matchesCatalogueTimeFilter(
  time: string,
  value: CatalogueTimeFilterValue,
): boolean {
  const hour = Number(time.slice(0, 2));
  const { start, end } = getCatalogueTimeFilter(value);
  return hour >= start && hour < end;
}
