import { useEffect, useState } from "react";
import { GridPaginationModel } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { keepPreviousData } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { Resource, ResourcesQuery, useResources } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { DEFAULT_PAGE_SIZE, DEFAULT_SEARCH_DEBOUNCE } from "@/utils/constants";

interface Props<T extends Resource, TFilters extends ResourcesQuery> {
  initialItemsPerPage?: number;
  initialPage?: number;
  useResource: ReturnType<typeof useResources<T>>;
  filters?: TFilters;
  changeUrlOnPageChange?: boolean;
}

export const usePaginatedTableResource = <
  T extends Resource,
  TFilters extends ResourcesQuery = ResourcesQuery,
>({
  initialItemsPerPage = DEFAULT_PAGE_SIZE,
  initialPage = 0,
  useResource,
  filters,
  changeUrlOnPageChange = false,
}: Props<T, TFilters>) => {
  const router = useRouter();
  const initialQueryPage = router.query.page
    ? +router.query.page - 1
    : initialPage;
  const [query, setQuery] = useState<Maybe<string>>();
  const [currentPage, setCurrentPage] = useState<number>(initialQueryPage);
  const [pageSize, setPageSize] = useState(initialItemsPerPage);
  const [listFilters, setListFilters] = useState<Maybe<TFilters>>(filters);

  const resource = useResource(
    {
      query,
      page: currentPage + 1,
      ...listFilters,
    },
    { placeholderData: keepPreviousData },
  );

  const debouncedSetQuery = useDebouncedCallback((term: string) => {
    setQuery(term);
    setCurrentPage(0);
  }, DEFAULT_SEARCH_DEBOUNCE);

  const onFilter = (newFilters: TFilters) => {
    setCurrentPage(0);
    setListFilters({ ...listFilters, ...newFilters });
  };

  useEffect(() => {
    if (!changeUrlOnPageChange) {
      return;
    }
    router.push({ query: { page: currentPage + 1 } }, undefined, {
      shallow: true,
    });
  }, [currentPage]);

  return {
    ...resource,
    filtersProps: {
      onSearch: debouncedSetQuery,
      onFilter,
      loading: resource.states.fetching ?? false,
    },
    tableProps: {
      onSearch: debouncedSetQuery,
      setFilter: setListFilters,
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
