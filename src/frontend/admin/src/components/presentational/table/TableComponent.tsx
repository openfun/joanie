import * as React from "react";
import { useState } from "react";
import { DataGrid, GridColDef, GridRowSelectionModel } from "@mui/x-data-grid";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import { Delete, SearchOutlined } from "@mui/icons-material";
import { useIntl } from "react-intl";
import { useDebouncedCallback } from "use-debounce";
import { DataGridProps } from "@mui/x-data-grid/models/props/DataGridProps";
import { GridValidRowModel } from "@mui/x-data-grid/models/gridRows";
import { TableDefaultActions } from "@/components/presentational/table/TableDefaultActions";
import { tableTranslations } from "@/components/presentational/table/translations";
import { DEFAULT_PAGE_SIZE } from "@/utils/constants";

interface Props<T extends GridValidRowModel> extends DataGridProps<T> {
  rows: T[];
  columns: GridColDef[];
  enableEdit?: boolean;
  onEditClick?: (row: T) => void;
  onUseAsTemplateClick?: (row: T) => void;
  onRemoveClick?: (row: T) => void;
  getEntityName?: (row: T) => string;
  onSelectRows?: (ids: GridRowSelectionModel) => void;
  onSearch?: (term: string) => void;
  multiSelectActions?: React.ReactElement;
  loading?: boolean;
  columnBuffer?: number;
  topActions?: React.ReactElement;
}

export function TableComponent<T extends GridValidRowModel>({
  enableEdit = true,
  paginationMode = "server",
  ...props
}: Props<T>) {
  const intl = useIntl();
  const [selectedRows, setSelectedRow] = useState<GridRowSelectionModel>([]);

  const getColumns = (): GridColDef[] => {
    const columns = [...props.columns];
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
          return (
            <TableDefaultActions
              entityName={entityName}
              onDelete={
                props.onRemoveClick && (() => props.onRemoveClick?.(params.row))
              }
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

  return (
    <>
      <Box padding={3}>
        {props.onSearch && (
          <TextField
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
        {props.topActions}
      </Box>
      <Box position="relative">
        {selectedRows.length > 0 && (
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
            <Box>
              <IconButton size="small" color="primary">
                <Delete sx={{ fontSize: "20px" }} />
              </IconButton>
            </Box>
          </Box>
        )}

        <DataGrid
          {...props}
          paginationMode={paginationMode}
          getRowHeight={() => "auto"}
          sx={{
            border: "none",
            borderRadius: 0,
            ".MuiDataGrid-columnSeparator": {
              display: "none",
            },
            ".MuiDataGrid-columnHeader:focus, .MuiDataGrid-cell": {
              outline: "none !important",
            },
            ".MuiDataGrid-columnHeaders": {
              border: 0,
              backgroundColor: "rgb(244, 246, 248)",
            },
          }}
          rows={props.rows}
          columns={getColumns()}
          columnBuffer={props?.columnBuffer ?? 3}
          loading={props.loading}
          slots={{
            loadingOverlay: LoaderCircular,
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
          onRowSelectionModelChange={(ids) => {
            setSelectedRow(ids);
            props.onSelectRows?.(ids);
          }}
          checkboxSelection={false}
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
