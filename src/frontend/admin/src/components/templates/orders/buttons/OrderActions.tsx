import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import CancelIcon from "@mui/icons-material/Cancel";
import ArticleIcon from "@mui/icons-material/Article";
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
  alreadyCancelTooltip: {
    id: "components.templates.orders.buttons.orderActionsButton.alreadyCancelTooltip",
    description: "Text when the order has already been canceled",
    defaultMessage: "The order has already been canceled",
  },
  cancelOrder: {
    id: "components.templates.orders.buttons.orderActionsButton.cancelOrder",
    description: "Label for the cancel order action",
    defaultMessage: "Cancel this order",
  },
  alreadyGenerateCertificateTooltip: {
    id: "components.templates.orders.buttons.orderActionsButton.alreadyGenerateCertificateTooltip",
    description: "Text when the certificate has already been generated",
    defaultMessage: "The certificate has already been generated",
  },
  generateCertificate: {
    id: "components.templates.orders.buttons.orderActionsButton.generateCertificate",
    description: "Label for the generate certificate order action",
    defaultMessage: "Generate certificate",
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
    const allOptions: MenuOption[] = [
      {
        icon: <CancelIcon />,
        mainLabel: intl.formatMessage(messages.cancelOrder),
        isDisable: order.state === OrderStatesEnum.ORDER_STATE_CANCELED,
        disableMessage: intl.formatMessage(messages.alreadyCancelTooltip),
        onClick: async () => {
          await orderQuery.methods.delete(order.id, {
            onSuccess: ordersQuery.methods.invalidate,
          });
        },
      },
      {
        icon: <ArticleIcon />,
        mainLabel: intl.formatMessage(messages.generateCertificate),
        isDisable: !!order.certificate,
        disableMessage: intl.formatMessage(
          messages.alreadyGenerateCertificateTooltip,
        ),
        onClick: async () => {
          ordersQuery.methods.generateCertificate(
            { orderId: order.id },
            {
              onSuccess: orderQuery.methods.invalidate,
            },
          );
        },
      },
    ];

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
