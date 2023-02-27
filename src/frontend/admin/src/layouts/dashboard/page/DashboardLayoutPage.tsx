import * as React from "react";
import { PropsWithChildren, ReactElement } from "react";
import { Container } from "@mui/material";
import { DashboardLayoutHeaderActions } from "@/layouts/dashboard/header/actions/DashboardLayoutHeaderActions";

interface Props {
  headerActions?: ReactElement;
  stretch?: boolean;
}

export function DashboardLayoutPage({
  stretch = false,
  ...props
}: PropsWithChildren<Props>) {
  return (
    <Container maxWidth={stretch ? false : "lg"}>
      <DashboardLayoutHeaderActions>
        {props.headerActions}
      </DashboardLayoutHeaderActions>
      {props.children}
    </Container>
  );
}
