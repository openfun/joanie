import * as React from "react";
import { ReactElement, ReactNode } from "react";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Unstable_Grid2";
import TextField from "@mui/material/TextField";
import { FormattedMessage, useIntl } from "react-intl";
import { orderViewMessages } from "@/components/templates/orders/view/translations";
import { Order } from "@/services/api/models/Order";
import { PATH_ADMIN } from "@/utils/routes/path";
import { formatShortDate } from "@/utils/dates";

type Props = {
  order?: Order;
  getViewIcon: (url: string) => ReactNode;
  getSignedIcon: (
    date?: string | boolean | null,
    withMargin?: boolean,
  ) => ReactElement;
};
export function OrderViewContractSection({
  order,
  getViewIcon,
  getSignedIcon,
}: Props) {
  const intl = useIntl();

  if (!order?.contract) {
    return null;
  }

  return (
    <Grid container spacing={2}>
      <Grid xs={12} mt={2}>
        <Typography variant="h6">
          <FormattedMessage
            {...orderViewMessages.contractDetailsSectionTitle}
          />
        </Typography>
      </Grid>
      <Grid xs={12} sm={6}>
        <TextField
          data-testid="order-view-contract-name"
          fullWidth={true}
          disabled={true}
          InputProps={{
            endAdornment: getViewIcon(
              PATH_ADMIN.contract_definition.edit(order.contract.id),
            ),
          }}
          label={intl.formatMessage(orderViewMessages.contract)}
          value={order.contract.definition_title}
        />
      </Grid>

      <Grid xs={12} sm={6}>
        <TextField
          data-testid="order-view-contract-submitted-for-signature"
          fullWidth={true}
          disabled={true}
          label={intl.formatMessage(orderViewMessages.submittedForSignatureOn)}
          value={
            order.contract.submitted_for_signature_on
              ? formatShortDate(order.contract.submitted_for_signature_on)
              : ""
          }
        />
      </Grid>
      <Grid xs={12} sm={6}>
        <TextField
          data-testid="order-view-contract-student-signed-on"
          fullWidth={true}
          disabled={true}
          InputProps={{
            endAdornment: getSignedIcon(order.contract.student_signed_on),
          }}
          label={intl.formatMessage(orderViewMessages.studentSignedOn)}
          value={
            order.contract.student_signed_on
              ? formatShortDate(order.contract.student_signed_on)
              : ""
          }
        />
      </Grid>
      <Grid xs={12} sm={6}>
        <TextField
          fullWidth={true}
          disabled={true}
          data-testid="order-view-contract-organization-signed-on"
          InputProps={{
            endAdornment: getSignedIcon(order.contract.organization_signed_on),
          }}
          label={intl.formatMessage(orderViewMessages.organizationSignedOn)}
          value={
            order.contract.organization_signed_on
              ? formatShortDate(order.contract.organization_signed_on)
              : ""
          }
        />
      </Grid>
    </Grid>
  );
}
