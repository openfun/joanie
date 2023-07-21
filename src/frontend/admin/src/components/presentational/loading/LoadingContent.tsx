import * as React from "react";
import { PropsWithChildren } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

type Props = {
  loading: boolean;
};
export function LoadingContent({
  children,
  loading,
}: PropsWithChildren<Props>) {
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center">
        <CircularProgress />
      </Box>
    );
  }
  return <div>{children}</div>;
}
