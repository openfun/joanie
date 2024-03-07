export enum ExcludedFiltersEnum {
  PAGE = "page",
  ID = "id",
}

export const ExcludedFiltersValues = ["", undefined, null, "none", "None"];

export const getAvailableFilters = (query: any): string[] => {
  const excludeFilters = Object.values(ExcludedFiltersEnum);
  const allFiltersName = Object.keys(deleteUnusedFilters(query));
  if (allFiltersName.length === 0) {
    return [];
  }
  return allFiltersName.filter(
    (el) => !excludeFilters.includes(el as ExcludedFiltersEnum),
  );
};

export const deleteUnusedFilters = (filters?: any): typeof filters => {
  if (!filters) {
    return {};
  }

  const excludeFilters = Object.values(ExcludedFiltersEnum);
  const result = JSON.parse(JSON.stringify(filters));
  (Object.keys(result) as (keyof typeof result)[]).forEach((key) => {
    const val = result[key];
    if (
      ExcludedFiltersValues.includes(val) ||
      excludeFilters.includes(key as ExcludedFiltersEnum)
    ) {
      delete result[key];
    }
  });
  return result;
};
