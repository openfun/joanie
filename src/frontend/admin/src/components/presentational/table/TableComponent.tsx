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
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { TableDefaultActions } from "@/components/presentational/table/TableDefaultActions";
import { tableTranslations } from "@/components/presentational/table/translations";

interface Props<T> {
  rows: T[];
  columns: GridColDef[];
  enableEdit?: boolean;
  onEditClick?: (row: T) => void;
  onRemoveClick?: (row: T) => void;
  getEntityName?: (row: T) => string;
  onSelectRows?: (ids: GridRowSelectionModel) => void;
  onSearch?: (term: string) => void;
  multiSelectActions?: React.ReactElement;
  loading?: boolean;
  columnBuffer?: number;
}

export function TableComponent<T>({ enableEdit = true, ...props }: Props<T>) {
  const intl = useIntl();
  const [pageSize, setPageSize] = useState(25);
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
              onDelete={() => props.onRemoveClick?.(params.row)}
              onEdit={() => props.onEditClick?.(params.row)}
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
    <SimpleCard>
      <Box padding={3}>
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
          initialState={{
            pagination: {
              paginationModel: {
                pageSize,
              },
            },
          }}
          autoHeight={true}
          localeText={{
            noRowsLabel: intl.formatMessage(tableTranslations.noRows),
            footerRowSelected: (count) =>
              intl.formatMessage(tableTranslations.rowsSelected, { count }),
          }}
          onPaginationModelChange={(size) => setPageSize(size.pageSize)}
          pageSizeOptions={[5, 10, 25, 50, 75]}
          onRowSelectionModelChange={(ids) => {
            setSelectedRow(ids);
            props.onSelectRows?.(ids);
          }}
          checkboxSelection={false}
          disableRowSelectionOnClick
        />
      </Box>
    </SimpleCard>
  );
}
