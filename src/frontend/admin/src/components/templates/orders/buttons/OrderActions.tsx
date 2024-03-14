import * as React from "react";
import { useMemo } from "react";
import CancelIcon from "@mui/icons-material/Cancel";
import { defineMessages, useIntl } from "react-intl";
import { Order, OrderStatesEnum } from "@/services/api/models/Order";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import { useOrder, useOrders } from "@/hooks/useOrders/useOrders";

const messages = defineMessages({
  orderActionsLabel: {
    id: "components.templates.orders.buttons.orderActionsButton.orderActionsLabel",
    description: "Label for the actions button",
    defaultMessage: "Actions",
  },
  cancelOrder: {
    id: "components.templates.orders.buttons.orderActionsButton.cancelOrder",
    description: "Label for the cancel order action",
    defaultMessage: "Cancel this order",
  },
});

type Props = {
  order: Order;
};

export default function OrderActionsButton({ order }: Props) {
  const intl = useIntl();
  const ordersQuery = useOrders({}, { enabled: false });
  const orderQuery = useOrder(order.id);

  const options = useMemo(() => {
    const allOptions: MenuOption[] = [];
    if (order.state !== OrderStatesEnum.ORDER_STATE_CANCELED) {
      allOptions.push({
        icon: <CancelIcon />,
        mainLabel: intl.formatMessage(messages.cancelOrder),
        onClick: async () => {
          await orderQuery.methods.delete(order.id, {
            onSuccess: ordersQuery.methods.invalidate,
          });
        },
      });
    }
    return allOptions;
  }, [order]);

  if (options.length === 0) {
    return undefined;
  }

  return (
    <ButtonMenu
      data-testid="order-view-action-button"
      label={intl.formatMessage(messages.orderActionsLabel)}
      id="order-view-action-button"
      variant="contained"
      color="secondary"
      options={options}
    />
  );
}
