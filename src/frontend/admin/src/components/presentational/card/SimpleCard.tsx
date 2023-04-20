import * as React from "react";
import { PropsWithChildren } from "react";
import { Paper } from "@mui/material";

export function SimpleCard(props: PropsWithChildren) {
  return (
    <Paper
      data-testid="simpleCard"
      elevation={0}
      sx={{
        borderRadius: 4,
        boxShadow:
          "rgb(145 158 171 / 20%) 0px 0px 2px 0px, rgb(145 158 171 / 12%) 0px 12px 24px -4px",
      }}
    >
      {props.children}
    </Paper>
  );
}
