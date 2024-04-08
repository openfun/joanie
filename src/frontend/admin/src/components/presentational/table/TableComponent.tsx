import * as React from "react";
import { ReactElement, useState } from "react";
import { DataGrid, GridColDef, GridRowSelectionModel } from "@mui/x-data-grid";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { useIntl } from "react-intl";
import { useDebouncedCallback } from "use-debounce";
import { DataGridProps } from "@mui/x-data-grid/models/props/DataGridProps";
import { GridValidRowModel } from "@mui/x-data-grid/models/gridRows";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import SearchOutlined from "@mui/icons-material/SearchOutlined";
import {
  TableDefaultActions,
  TableDefaultMenuItem,
} from "@/components/presentational/table/TableDefaultActions";
import { tableTranslations } from "@/components/presentational/table/translations";
import { DEFAULT_PAGE_SIZE } from "@/utils/constants";
import { mergeArrayUnique } from "@/utils/array";
import { CustomTablePagination } from "@/components/presentational/table/TablePagination";

export type DefaultTableProps<T extends GridValidRowModel> = {
  enableSelect?: boolean;
  selectAllByDefault?: boolean;
  onSelectRows?: (ids: string[], items: T[]) => void;
  defaultSelectedRows?: string[];
  filters?: ReactElement;
  multiSelectActions?: ReactElement;
  topActions?: ReactElement;
  enableSearch?: boolean;
  enableDelete?: boolean;
  changeUrlOnPageChange?: boolean;
};

export type TableComponentProps<T extends GridValidRowModel> =
  DataGridProps<T> &
    DefaultTableProps<T> & {
      rows?: T[];
      columns?: GridColDef[];
      enableEdit?: boolean;
      onEditClick?: (row: T) => void;
      onUseAsTemplateClick?: (row: T) => void;
      onRemoveClick?: (row: T) => void;
      getEntityName?: (row: T) => string;
      onSearch?: (term: string) => void;
      multiSelectActions?: ReactElement;
      loading?: boolean;
      columnBuffer?: number;
      getOptions?: (row: T) => TableDefaultMenuItem[];
    };

export function TableComponent<T extends GridValidRowModel>({
  enableEdit = true,
  enableDelete = true,
  enableSelect = false,
  paginationMode = "server",
  enableSearch = true,
  ...props
}: TableComponentProps<T>) {
  const intl = useIntl();
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>(
    props.defaultSelectedRows ?? [],
  );
  const [selectedItems, setSelectedItems] = useState<T[]>([]);

  const rows = props.rows ?? [];

  const getColumns = (): GridColDef[] => {
    const columns = [...(props.columns ?? [])];
    if (enableEdit) {
      columns.push({
        field: "action",
        headerName: "",
        align: "right",

        headerAlign: "right",
        sortable: false,
        disableColumnMenu: true,
        filterable: false,
        resizable: false,
        renderCell: (params) => {
          const entityName = props.getEntityName?.(params.row) ?? undefined;
          const extendedOptions = props.getOptions?.(params.row) ?? [];
          const onDelete =
            enableDelete && props.onRemoveClick
              ? () => props.onRemoveClick?.(params.row)
              : undefined;

          return (
            <TableDefaultActions
              extendedOptions={extendedOptions}
              entityName={entityName}
              onDelete={onDelete}
              onUseAsTemplate={
                props.onUseAsTemplateClick &&
                (() => props.onUseAsTemplateClick?.(params.row))
              }
              onEdit={
                props.onEditClick && (() => props.onEditClick?.(params.row))
              }
            />
          );
        },
      });
    }
    return columns;
  };

  const onChangeSearchInput = useDebouncedCallback((term: string) => {
    props.onSearch?.(term);
  });

  const onSelectItems = (ids: string[]) => {
    if (ids.length === 0) {
      setSelectedItems([]);
      setSelectedRows(ids);
      props.onSelectRows?.(ids, []);
      return;
    }

    const keepPrevious = selectedItems.filter((item) => {
      return ids.some((id) => {
        return id === item.id;
      });
    });

    const newResult = rows.filter((row) => {
      return ids.some((id) => {
        return id === row.id;
      });
    });

    const items = mergeArrayUnique(
      keepPrevious,
      newResult,
      (first, second) => first.id === second.id,
    );

    setSelectedItems(items);
    setSelectedRows(ids);
    props.onSelectRows?.(ids, items);
  };

  return (
    <>
      <Box
        sx={{ marginTop: "0px !important" }}
        padding={enableSearch || props.topActions ? 2 : 0}
      >
        {props.topActions && (
          <Box mb={enableSearch ? 2 : 0}>{props.topActions}</Box>
        )}

        {props.filters}
        {enableSearch && props.onSearch && !props.filters && (
          <TextField
            margin="none"
            autoComplete="off"
            defaultValue=""
            onChange={(event) => onChangeSearchInput(event.target.value)}
            fullWidth
            placeholder="Search..."
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  {props.loading ? (
                    <CircularProgress size="19px" />
                  ) : (
                    <SearchOutlined />
                  )}
                </InputAdornment>
              ),
            }}
          />
        )}
      </Box>
      <Box position="relative">
        {props.multiSelectActions && selectedRows.length > 0 && (
          <Box
            display="flex"
            justifyContent="flex-end"
            alignItems="center"
            sx={{
              zIndex: 3,
              maxHeight: "56px",
              px: 2,
              height: "56px",
              position: "absolute",
              top: 0,
              right: 0,
              left: 50,
              backgroundColor: "rgb(244, 246, 248)",
            }}
          >
            {props.multiSelectActions}
          </Box>
        )}

        <DataGrid
          {...props}
          paginationMode={paginationMode}
          getRowHeight={() => {
            return 40;
          }}
          sx={{
            border: "none",
            borderRadius: 0,
            ".MuiDataGrid-columnSeparator": {
              display: "none",
            },
            ".MuiDataGrid-cell": {
              minHeight: "35px !important",
            },
            ".MuiDataGrid-columnHeader:focus, .MuiDataGrid-cell": {
              outline: "none !important",
            },
            ".MuiDataGrid-columnHeaders": {
              border: 0,
              backgroundColor: "rgb(244, 246, 248)",
            },
          }}
          rows={rows}
          columns={getColumns()}
          loading={props.loading}
          pagination={true}
          slots={{
            loadingOverlay: LoaderCircular,
            pagination: CustomTablePagination,
          }}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: DEFAULT_PAGE_SIZE,
              },
            },
          }}
          autoHeight={true}
          localeText={{
            noRowsLabel: intl.formatMessage(tableTranslations.noRows),
            footerRowSelected: (count) =>
              intl.formatMessage(tableTranslations.rowsSelected, { count }),
          }}
          pageSizeOptions={[DEFAULT_PAGE_SIZE]}
          checkboxSelection={enableSelect}
          onRowSelectionModelChange={(newRowSelectionModel) => {
            onSelectItems(newRowSelectionModel as string[]);
          }}
          keepNonExistentRowsSelected
          rowSelectionModel={selectedRows}
          disableRowSelectionOnClick
        />
      </Box>
    </>
  );
}

export function LoaderCircular() {
  return (
    <Box
      data-testid="circular-loader-container"
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <CircularProgress data-testid="circular-loader" />
    </Box>
  );
}
