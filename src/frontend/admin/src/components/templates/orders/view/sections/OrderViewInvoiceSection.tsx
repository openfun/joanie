import * as React from "react";
import { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";
import AccordionDetails from "@mui/material/AccordionDetails";
import Grid from "@mui/material/Grid2";
import TextField from "@mui/material/TextField";
import Stack from "@mui/material/Stack";
import { FormattedMessage, useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import {
  invoiceStatusMessages,
  invoiceTypesMessages,
  orderViewMessages,
} from "@/components/templates/orders/view/translations";
import { Order } from "@/services/api/models/Order";
import { OrderViewInvoiceChildrenRow } from "@/components/templates/orders/view/sections/OrderViewInvoiceChildrenRow";
import { formatShortDate } from "@/utils/dates";

type Props = {
  order?: Order;
};
export function OrderViewInvoiceSection({ order }: Props) {
  const intl = useIntl();
  const [showInvoice, setShowInvoice] = useState(false);

  if (!order?.main_invoice) {
    return undefined;
  }

  return (
    <Grid container spacing={2}>
      <Grid size={12} mt={2}>
        <Accordion
          expanded={showInvoice}
          sx={{ boxShadow: "none", background: "none" }}
          onChange={(_event, expanded) => setShowInvoice(expanded)}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ px: 0, display: "flex", alignItems: "center" }}
            aria-controls="panel1a-content"
            id="panel1a-header"
          >
            <Typography variant="h6">
              <FormattedMessage
                {...orderViewMessages.invoiceDetailsSectionTitle}
              />
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Alert severity="info">
                  <FormattedMessage
                    {...orderViewMessages.invoiceDetailsSectionAlert}
                  />
                </Alert>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.invoiceType)}
                  value={intl.formatMessage(
                    invoiceTypesMessages[order.main_invoice.type],
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 12, md: 4 }}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  InputProps={{
                    endAdornment: order.total_currency,
                  }}
                  label={intl.formatMessage(orderViewMessages.total)}
                  value={order.main_invoice.total}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.invoiceState)}
                  value={intl.formatMessage(
                    invoiceStatusMessages[order.main_invoice.state],
                  )}
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.billingAddress)}
                  value={order.main_invoice.recipient_address}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.invoiceCreatedOn)}
                  value={formatShortDate(order.main_invoice.created_on)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.invoiceUpdatedOn)}
                  value={formatShortDate(order.main_invoice.updated_on)}
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  fullWidth={true}
                  disabled={true}
                  label={intl.formatMessage(orderViewMessages.invoiceBalance)}
                  InputProps={{
                    endAdornment: order.total_currency,
                  }}
                  value={order.main_invoice.balance}
                />
              </Grid>

              {order.certificate && (
                <Grid size={12}>
                  <TextField
                    fullWidth={true}
                    disabled={true}
                    label={intl.formatMessage(orderViewMessages.certificate)}
                    value={order.certificate.definition_title}
                  />
                </Grid>
              )}
              {order.main_invoice?.children.length > 0 && (
                <Grid size={12}>
                  <Stack gap={2}>
                    <Typography variant="subtitle2">
                      <FormattedMessage {...orderViewMessages.subInvoiceList} />
                    </Typography>
                    {order.main_invoice.children.map((child) => (
                      <OrderViewInvoiceChildrenRow
                        key={order.id}
                        child={child}
                      />
                    ))}
                  </Stack>
                </Grid>
              )}
            </Grid>
          </AccordionDetails>
        </Accordion>
      </Grid>
    </Grid>
  );
}
