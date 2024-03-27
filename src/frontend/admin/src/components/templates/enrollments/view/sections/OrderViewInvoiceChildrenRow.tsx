import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import {
  OrderInvoiceTypesEnum,
  OrderMainInvoiceChildren,
} from "@/services/api/models/Order";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import {
  invoiceTypesMessages,
  orderViewMessages,
} from "@/components/templates/orders/view/translations";

type Props = {
  child: OrderMainInvoiceChildren;
};
export function OrderViewInvoiceChildrenRow({ child }: Props) {
  const intl = useIntl();
  return (
    <DefaultRow
      enableDelete={false}
      mainTitle={intl.formatMessage(invoiceTypesMessages[child.type])}
      subTitle={`${intl.formatMessage(orderViewMessages.invoiceRef)} ${
        child.reference
      }`}
      permanentRightActions={
        <Box>
          <Typography
            sx={{
              color:
                child.type === OrderInvoiceTypesEnum.INVOICE
                  ? "success.main"
                  : "error.main",
            }}
            variant="subtitle2"
          >
            {child.invoiced_balance} {child.total_currency}
          </Typography>
          <Typography variant="caption">
            {`(${new Date(child.created_on).toLocaleDateString()})`}
          </Typography>
        </Box>
      }
    />
  );
}
