import * as React from "react";
import { ReactElement, ReactNode } from "react";

import TextField from "@mui/material/TextField";
import { FormattedMessage, useIntl } from "react-intl";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import { useRouter } from "next/router";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import { HighlightOff, TaskAlt } from "@mui/icons-material";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import Chip, { ChipOwnProps } from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import { Order, PaymentStatesEnum } from "@/services/api/models/Order";
import {
  orderStatesMessages,
  orderViewMessages,
} from "@/components/templates/orders/view/translations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { OrderViewInvoiceSection } from "@/components/templates/orders/view/sections/OrderViewInvoiceSection";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { OrderViewContractSection } from "@/components/templates/orders/view/sections/OrderViewContractSection";
import { OrderViewCertificateSection } from "@/components/templates/orders/view/sections/OrderViewCertificateSection";
import CreditCard from "@/components/presentational/credit-card/CreditCard";
import { formatShortDate } from "@/utils/dates";

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

  const getSignedIcon = (
    date?: string | boolean | null,
    withMargin?: boolean,
  ): ReactElement => {
    return date ? (
      <TaskAlt sx={{ mr: withMargin ? 1 : 0 }} color="success" />
    ) : (
      <HighlightOff sx={{ mr: withMargin ? 1 : 0 }} color="error" />
    );
  };

  const stateColorMapping: Record<PaymentStatesEnum, ChipOwnProps["color"]> = {
    paid: "success",
    refused: "error",
    pending: "primary",
  };

  function stateColor(state: PaymentStatesEnum) {
    return stateColorMapping[state] || "default";
  }

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
        <Stack gap={2}>
          <Grid container spacing={2}>
            <Grid size={12}>
              <Typography variant="h6">
                <FormattedMessage
                  {...orderViewMessages.orderDetailsSectionTitle}
                />
              </Typography>
            </Grid>
            <Grid size={12}>
              <Alert severity="info">
                <FormattedMessage
                  {...orderViewMessages.orderDetailsSectionAlert}
                />
              </Alert>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth={true}
                disabled={true}
                InputProps={{
                  ...(order.organization
                    ? {
                        endAdornment: getViewIcon(
                          PATH_ADMIN.organizations.edit(order.organization.id),
                        ),
                      }
                    : {}),
                }}
                label={intl.formatMessage(orderViewMessages.organization)}
                value={order.organization?.title ?? ""}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
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
            <Grid size={12}>
              {order.course && !order.enrollment && (
                <TextField
                  fullWidth={true}
                  disabled={true}
                  InputProps={{
                    ...(order.course
                      ? {
                          endAdornment: getViewIcon(
                            PATH_ADMIN.courses.edit(order.course.id),
                          ),
                        }
                      : {}),
                  }}
                  label={intl.formatMessage(orderViewMessages.course)}
                  value={order.course.title}
                />
              )}
            </Grid>
            <Grid size={12}>
              {order.enrollment && (
                <TextField
                  fullWidth={true}
                  disabled={true}
                  multiline={true}
                  label={intl.formatMessage(orderViewMessages.enrollment)}
                  value={intl.formatMessage(orderViewMessages.enrollmentValue, {
                    courseRunTitle: order.enrollment.course_run.title,
                    courseRunState: order.enrollment.course_run.state?.text,
                    registerOn: formatShortDate(order.enrollment.created_on),
                  })}
                />
              )}
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
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
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth={true}
                disabled={true}
                label={intl.formatMessage(orderViewMessages.orderGroup)}
                value={order.order_group ? order.order_group.id : "-"}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
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
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth={true}
                disabled={true}
                label={intl.formatMessage(orderViewMessages.state)}
                value={intl.formatMessage(orderStatesMessages[order.state])}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControlLabel
                sx={{ ml: 0.1 }}
                control={getSignedIcon(order.has_waived_withdrawal_right, true)}
                label={intl.formatMessage(
                  order.has_waived_withdrawal_right
                    ? orderViewMessages.hasWaivedWithdrawalRight
                    : orderViewMessages.hasNotWaivedWithdrawalRight,
                )}
              />
            </Grid>
          </Grid>
          <OrderViewContractSection
            order={order}
            getViewIcon={getViewIcon}
            getSignedIcon={getSignedIcon}
          />
          <OrderViewCertificateSection
            getViewIcon={getViewIcon}
            order={order}
          />
          <OrderViewInvoiceSection order={order} />
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 6 }} mt={2}>
              <Typography variant="h6">
                <FormattedMessage {...orderViewMessages.paymentSchedule} />
              </Typography>
              <Box my={2}>
                {order.credit_card ? (
                  <CreditCard {...order.credit_card} expiration_month={5} />
                ) : (
                  <Alert severity="warning">
                    <FormattedMessage {...orderViewMessages.noPaymentMethod} />
                  </Alert>
                )}
              </Box>
              {order.payment_schedule && (
                <Box border={1} borderRadius={1} borderColor="action.disabled">
                  <Table>
                    <TableBody>
                      {order.payment_schedule?.map((row) => (
                        <TableRow
                          key={row.id}
                          data-testid={`order-view-payment-${row.id}`}
                          sx={{ "&:last-child > *": { border: 0 } }}
                        >
                          <TableCell sx={{ borderColor: "action.disabled" }}>
                            {formatShortDate(row.due_date)}
                          </TableCell>
                          <TableCell sx={{ borderColor: "action.disabled" }}>
                            {row.amount} {row.currency}
                          </TableCell>
                          <TableCell sx={{ borderColor: "action.disabled" }}>
                            <Stack alignItems="flex-end">
                              <Chip
                                label={row.state}
                                color={stateColor(row.state)}
                              />
                            </Stack>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </Grid>
          </Grid>
        </Stack>
      </Box>
    </SimpleCard>
  );
}
