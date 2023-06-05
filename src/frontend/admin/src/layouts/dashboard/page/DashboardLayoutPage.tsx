import { PropsWithChildren, ReactElement } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { DashboardLayoutHeaderActions } from "@/layouts/dashboard/header/actions/DashboardLayoutHeaderActions";
import { CustomBreadcrumbs } from "@/components/presentational/breadrumbs/CustomBreadcrumbs";
import { BreadcrumbsLinkProps } from "@/components/presentational/breadrumbs/type";

interface Props {
  title?: string;
  actions?: ReactElement;
  headerActions?: ReactElement;
  stretch?: boolean;
  isLoading?: boolean;
  breadcrumbs?: BreadcrumbsLinkProps[];
}

export function DashboardLayoutPage({
  stretch = false,
  isLoading = false,
  breadcrumbs,
  ...props
}: PropsWithChildren<Props>) {
  return (
    <Container maxWidth={stretch ? false : "xl"}>
      <DashboardLayoutHeaderActions>
        {props.headerActions}
      </DashboardLayoutHeaderActions>
      <Box
        mb={4}
        display="flex"
        justifyContent="space-between"
        alignItems="center"
      >
        <Box>
          {!isLoading && props.title && (
            <Typography fontWeight="bold" variant="h4">
              {props.title}
            </Typography>
          )}
          {!isLoading && breadcrumbs && (
            <CustomBreadcrumbs links={breadcrumbs} />
          )}
        </Box>
        <Box>{props.actions}</Box>
      </Box>
      {!isLoading && props.children}
      {isLoading && (
        <Box
          height="80vh"
          display="flex"
          justifyContent="center"
          alignItems="center"
        >
          <CircularProgress />
        </Box>
      )}
    </Container>
  );
}
