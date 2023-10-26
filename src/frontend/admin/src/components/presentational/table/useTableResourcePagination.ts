import { useState } from "react";
import { GridPaginationModel } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { Resource, useResources } from "@/hooks/useResources";
import { Maybe } from "@/types/utils";
import { DEFAULT_PER_PAGE_SIZE } from "@/utils/constants";

interface Props<T extends Resource> {
  initialItemsPerPage?: number;
  initialPage?: number;
  useResource: ReturnType<typeof useResources<T>>;
}

export const useTableResourcePagination = <T extends Resource>({
  initialItemsPerPage = DEFAULT_PER_PAGE_SIZE,
  initialPage = 0,
  useResource,
}: Props<T>) => {
  const [query, setQuery] = useState<Maybe<string>>();
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialItemsPerPage);

  const resource = useResource(
    {
      query,
      page: currentPage + 1,
    },
    { keepPreviousData: true },
  );

  const debouncedSetQuery = useDebouncedCallback((term: string) => {
    setQuery(term);
    setCurrentPage(0);
  }, 300);

  return {
    useResource: resource,
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
