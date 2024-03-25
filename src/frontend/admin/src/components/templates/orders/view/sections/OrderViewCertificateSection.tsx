import * as React from "react";
import { ReactNode } from "react";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Unstable_Grid2";
import TextField from "@mui/material/TextField";
import { FormattedMessage, useIntl } from "react-intl";
import { orderViewMessages } from "@/components/templates/orders/view/translations";
import { Order } from "@/services/api/models/Order";
import { PATH_ADMIN } from "@/utils/routes/path";

type Props = {
  order?: Order;
  getViewIcon: (url: string) => ReactNode;
};

export function OrderViewCertificateSection({ order, getViewIcon }: Props) {
  const intl = useIntl();

  if (!order?.certificate) {
    return null;
  }

  return (
    <Grid container spacing={2}>
      <Grid xs={12} mt={2}>
        <Typography variant="h6">
          <FormattedMessage
            {...orderViewMessages.certificateDetailsSectionTitle}
          />
        </Typography>
      </Grid>
      <Grid xs={12} sm={6}>
        <TextField
          data-testid="order-view-certificate-name"
          fullWidth={true}
          disabled={true}
          InputProps={{
            endAdornment: order.product.certificate_definition
              ? getViewIcon(
                  PATH_ADMIN.certificates.edit(
                    order.product.certificate_definition,
                  ),
                )
              : undefined,
          }}
          label={intl.formatMessage(
            orderViewMessages.certificateDefinitionTemplate,
          )}
          value={order.certificate?.definition_title}
        />
      </Grid>

      <Grid xs={12} sm={6}>
        <TextField
          data-testid="order-view-certificate-date"
          fullWidth={true}
          disabled={true}
          label={intl.formatMessage(
            orderViewMessages.certificateDefinitionDate,
          )}
          value={
            order.certificate.issued_on
              ? new Date(order.certificate.issued_on).toLocaleDateString()
              : ""
          }
        />
      </Grid>
    </Grid>
  );
}
