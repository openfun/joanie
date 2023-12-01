import { useState } from "react";
import { GridPaginationModel } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { keepPreviousData } from "@tanstack/react-query";
import { Resource, ResourcesQuery, useResources } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { DEFAULT_PAGE_SIZE, DEFAULT_SEARCH_DEBOUNCE } from "@/utils/constants";

interface Props<T extends Resource, TFilters extends ResourcesQuery> {
  initialItemsPerPage?: number;
  initialPage?: number;
  useResource: ReturnType<typeof useResources<T>>;
  filters?: TFilters;
}

export const usePaginatedTableResource = <
  T extends Resource,
  TFilters extends ResourcesQuery = ResourcesQuery,
>({
  initialItemsPerPage = DEFAULT_PAGE_SIZE,
  initialPage = 0,
  useResource,
  filters,
}: Props<T, TFilters>) => {
  const [query, setQuery] = useState<Maybe<string>>();
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialItemsPerPage);

  const resource = useResource(
    {
      query,
      page: currentPage + 1,
      ...filters,
    },
    { placeholderData: keepPreviousData },
  );

  const debouncedSetQuery = useDebouncedCallback((term: string) => {
    setQuery(term);
    setCurrentPage(0);
  }, DEFAULT_SEARCH_DEBOUNCE);

  return {
    ...resource,
    tableProps: {
      onSearch: debouncedSetQuery,
      loading: resource.states.fetching ?? false,
      rowCount: resource?.meta?.pagination?.count ?? 0,
      onPaginationModelChange: (pagination: GridPaginationModel) => {
        setCurrentPage(pagination.page);
        setPageSize(pagination.pageSize);
      },
      paginationModel: {
        pageSize,
        page: currentPage,
      },
      rows: resource.items ?? [],
    },
  };
};
