import Pagination from "@mui/material/Pagination";
import { TablePaginationProps } from "@mui/material/TablePagination";
import {
  gridFilteredTopLevelRowCountSelector,
  gridPageSizeSelector,
  GridPagination,
  useGridApiContext,
  useGridRootProps,
  useGridSelector,
} from "@mui/x-data-grid";
import * as React from "react";

const getPageCount = (rowCount: number, pageSize: number): number => {
  if (pageSize > 0 && rowCount > 0) {
    return Math.ceil(rowCount / pageSize);
  }

  return 0;
};

export function CustomTablePagination(props: any) {
  return <GridPagination ActionsComponent={TablePagination} {...props} />;
}

function TablePagination({
  page,
  onPageChange,
  className,
}: Pick<TablePaginationProps, "page" | "onPageChange" | "className">) {
  const apiRef = useGridApiContext();
  const rootProps = useGridRootProps();

  const pageSize = useGridSelector(apiRef, gridPageSizeSelector);
  const visibleTopLevelRowCount = useGridSelector(
    apiRef,
    gridFilteredTopLevelRowCountSelector,
  );
  const pageCount = getPageCount(
    rootProps.rowCount ?? visibleTopLevelRowCount,
    pageSize,
  );

  return (
    <Pagination
      data-testid="table-pagination"
      color="primary"
      disabled={rootProps.loading}
      className={className}
      count={pageCount}
      page={page + 1}
      onChange={(event, newPage) => {
        onPageChange(event as any, newPage - 1);
      }}
    />
  );
}
