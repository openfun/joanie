import * as React from "react";
import { ReactNode } from "react";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export interface ListRow {
  id?: string;
}

export interface ListDummyRow {
  dummyId?: string;
}

type Props<Row extends ListRow, DummyRow extends ListDummyRow> = {
  rows: Row[];
  dummyRows?: DummyRow[];
  dummyRowsPosition?: "top" | "bottom";
  renderRow: (row: Row, index: number) => ReactNode;
  renderDummyRow?: (dummyRow: DummyRow, index: number) => ReactNode;
  emptyListMessage: string;
};
export function CustomList<Row extends ListRow, DummyRow extends ListDummyRow>({
  rows,
  renderRow,
  dummyRows = [],
  renderDummyRow,
  emptyListMessage,
  dummyRowsPosition = "bottom",
}: Props<Row, DummyRow>) {
  return (
    <Stack padding={3} gap={2}>
      {dummyRowsPosition === "top" &&
        renderDummyRow &&
        dummyRows.map(renderDummyRow)}

      {rows.map(renderRow)}

      {dummyRowsPosition === "bottom" &&
        renderDummyRow &&
        dummyRows.map(renderDummyRow)}

      {rows.length === 0 && dummyRows.length === 0 && (
        <Box display="flex" alignItems="center" justifyContent="center">
          <Typography width="100%" align="center" variant="caption">
            {emptyListMessage}
          </Typography>
        </Box>
      )}
    </Stack>
  );
}
