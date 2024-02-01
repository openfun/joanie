import * as React from "react";
import { ReactNode } from "react";

import TextField from "@mui/material/TextField";
import { FormattedMessage, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Unstable_Grid2"; // Grid version 2
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import { useRouter } from "next/router";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import { Order } from "@/services/api/models/Order";
import {
  orderStatesMessages,
  orderViewMessages,
} from "@/components/templates/orders/view/translations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { OrderViewInvoiceSection } from "@/components/templates/orders/view/sections/OrderViewInvoiceSection";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

type Props = {
  order: Order;
};
export function OrderView({ order }: Props) {
  const intl = useIntl();
  const router = useRouter();
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
            textFillColor: "black",
          },
        }}
      >
        <Grid container spacing={2}>
          <Grid xs={12}>
            <Typography variant="h6">
              <FormattedMessage
                {...orderViewMessages.orderDetailsSectionTitle}
              />
            </Typography>
          </Grid>
          <Grid xs={12}>
            <Alert severity="info">
              <FormattedMessage
                {...orderViewMessages.orderDetailsSectionAlert}
              />
            </Alert>
          </Grid>
          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: getViewIcon(
                  PATH_ADMIN.organizations.edit(order.organization.id),
                ),
              }}
              label={intl.formatMessage(orderViewMessages.organization)}
              value={order.organization.title}
            />
          </Grid>
          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: getViewIcon(
                  PATH_ADMIN.products.edit(order.product.id),
                ),
              }}
              label={intl.formatMessage(orderViewMessages.product)}
              value={order.product.title}
            />
          </Grid>
          <Grid xs={12}>
            {order.course && !order.enrollment && (
              <TextField
                fullWidth={true}
                disabled={true}
                InputProps={{
                  endAdornment: getViewIcon(
                    PATH_ADMIN.courses.edit(order.course.id),
                  ),
                }}
                label={intl.formatMessage(orderViewMessages.course)}
                value={order.course.title}
              />
            )}
          </Grid>
          <Grid xs={12}>
            {order.enrollment && (
              <TextField
                fullWidth={true}
                disabled={true}
                multiline={true}
                label={intl.formatMessage(orderViewMessages.enrollment)}
                value={`${order.enrollment.course_run.title} (${
                  order.enrollment.course_run.state?.text
                })\n${intl.formatMessage(
                  orderViewMessages.enrollmentAt,
                )}: ${new Date(
                  order.enrollment.created_on,
                ).toLocaleDateString()}`}
              />
            )}
          </Grid>

          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(orderViewMessages.orderGroup)}
              value={order.order_group ? order.order_group.id : "-"}
            />
          </Grid>
          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(orderViewMessages.owner)}
              helperText={
                <Tooltip
                  title={intl.formatMessage(commonTranslations.clickToCopy)}
                  onClick={() => copyToClipboard(order.owner.email)}
                >
                  <Typography sx={{ cursor: "pointer" }} variant="caption">
                    {order.owner.email}
                  </Typography>
                </Tooltip>
              }
              value={order.owner.full_name ?? order.owner.username}
            />
          </Grid>
          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              label={intl.formatMessage(orderViewMessages.state)}
              value={intl.formatMessage(orderStatesMessages[order.state])}
            />
          </Grid>
          <Grid xs={12} sm={6}>
            <TextField
              fullWidth={true}
              disabled={true}
              InputProps={{
                endAdornment: order.total_currency,
              }}
              label={intl.formatMessage(orderViewMessages.price)}
              helperText={intl.formatMessage(orderViewMessages.taxIncluded)}
              value={order.total}
            />
          </Grid>
          <OrderViewInvoiceSection order={order} />
        </Grid>
      </Box>
    </SimpleCard>
  );
}
