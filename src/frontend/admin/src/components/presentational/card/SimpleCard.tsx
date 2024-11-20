import * as React from "react";
import { PropsWithChildren } from "react";
import Paper, { PaperProps } from "@mui/material/Paper";

export function SimpleCard({
  sx,
  children,
  ...props
}: PropsWithChildren<PaperProps>) {
  return (
    <Paper
      data-testid="simpleCard"
      elevation={0}
      sx={{
        ...sx,
        borderRadius: 4,
        overflow: "hidden",
      }}
      {...props}
    >
      {children}
    </Paper>
  );
}
