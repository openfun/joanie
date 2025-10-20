import * as React from "react";
import { ReactNode } from "react";
import { FormattedMessage, defineMessages, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import { useRouter } from "next/router";
import { useTheme } from "@mui/material/styles";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { BatchOrder } from "@/services/api/models/BatchOrder";

const messages = defineMessages({
  sectionTitle: {
    id: "components.templates.batchOrders.view.sectionTitle",
    defaultMessage: "Batch Order informations",
    description: "Title for the batch order information section",
  },
  sectionAlert: {
    id: "components.templates.batchOrders.view.sectionAlert",
    defaultMessage:
      "In this view, you can see the details of a batch order, such as the company, seats, and status.",
    description: "Informative text for the batch order view",
  },
  organization: {
    id: "components.templates.batchOrders.view.organization",
    defaultMessage: "Organization",
    description: "Label for organization",
  },
  product: {
    id: "components.templates.batchOrders.view.product",
    defaultMessage: "Product",
    description: "Label for product",
  },
  course: {
    id: "components.templates.batchOrders.view.course",
    defaultMessage: "Course",
    description: "Label for course",
  },
  owner: {
    id: "components.templates.batchOrders.view.owner",
    defaultMessage: "Owner",
    description: "Label for owner",
  },
  companyName: {
    id: "components.templates.batchOrders.view.companyName",
    defaultMessage: "Company name",
    description: "Label for company name",
  },
  nbSeats: {
    id: "components.templates.batchOrders.view.nbSeats",
    defaultMessage: "Number of seats",
    description: "Label for number of seats",
  },
  state: {
    id: "components.templates.batchOrders.view.state",
    defaultMessage: "State",
    description: "Label for state",
  },
  total: {
    id: "components.templates.batchOrders.view.total",
    defaultMessage: "Total",
    description: "Label for total",
  },
});

export type Props = {
  batchOrder: BatchOrder;
};

export function BatchOrderView({ batchOrder }: Props) {
  const intl = useIntl();
  const router = useRouter();
  const theme = useTheme();
  const copyToClipboard = useCopyToClipboard();

  const getViewIcon = (url: string): ReactNode => {
    return (
      <Tooltip title={intl.formatMessage(commonTranslations.clickToView)}>
        <IconButton onClick={() => router.push(url)}>
          <RemoveRedEyeIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    );
  };

  return (
    <SimpleCard>
      <Box
        padding={8}
        sx={{
          ".MuiOutlinedInput-input.Mui-disabled": {
            textFillColor: theme.palette.text.primary,
          },
        }}
      >
        <Grid container spacing={2}>
          <Grid size={12}>
            <Typography variant="h6">
              <FormattedMessage {...messages.sectionTitle} />
            </Typography>
          </Grid>
          <Grid size={12}>
            <Alert severity="info">
              <FormattedMessage {...messages.sectionAlert} />
            </Alert>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                ...(batchOrder.organization
                  ? {
                      endAdornment: getViewIcon(
                        PATH_ADMIN.organizations.edit(
                          batchOrder.organization.id,
                        ),
                      ),
                    }
                  : {}),
              }}
              label={intl.formatMessage(messages.organization)}
              value={batchOrder.organization?.title ?? ""}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: getViewIcon(
                  PATH_ADMIN.products.edit(batchOrder.offering.product.id),
                ),
              }}
              label={intl.formatMessage(messages.product)}
              value={batchOrder.offering.product.title}
            />
          </Grid>

          <Grid size={12}>
            {batchOrder.offering.course && (
              <TextField
                fullWidth={true}
                disabled={true}
                InputProps={{
                  endAdornment: getViewIcon(
                    PATH_ADMIN.courses.edit(batchOrder.offering.course.id),
                  ),
                }}
                label={intl.formatMessage(messages.course)}
                value={batchOrder.offering.course.title}
              />
            )}
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.owner)}
              helperText={
                <Tooltip
                  title={intl.formatMessage(commonTranslations.clickToCopy)}
                  onClick={() => copyToClipboard(batchOrder.owner.email)}
                >
                  <Typography sx={{ cursor: "pointer" }} variant="caption">
                    {batchOrder.owner.email}
                  </Typography>
                </Tooltip>
              }
              value={batchOrder.owner.full_name ?? batchOrder.owner.username}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.companyName)}
              value={batchOrder.company_name}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.nbSeats)}
              value={batchOrder.nb_seats}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(messages.state)}
              value={batchOrder.state}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: batchOrder.total_currency,
              }}
              label={intl.formatMessage(messages.total)}
              value={batchOrder.total}
            />
          </Grid>
        </Grid>
      </Box>
    </SimpleCard>
  );
}
