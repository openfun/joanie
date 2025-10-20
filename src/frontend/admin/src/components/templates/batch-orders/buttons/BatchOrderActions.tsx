import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import CancelIcon from "@mui/icons-material/Cancel";
import {
  BatchOrder,
  BatchOrderStatesEnum,
} from "@/services/api/models/BatchOrder";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import {
  useBatchOrder,
  useBatchOrders,
} from "@/hooks/useBatchOrders/useBatchOrders";

const messages = defineMessages({
  batchOrderActionsLabel: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.batchOrderActionsLabel",
    description: "Label for the actions button",
    defaultMessage: "Actions",
  },
  alreadyCancelTooltip: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.alreadyCancelTooltip",
    description: "Text when the batch order has already been canceled",
    defaultMessage: "The batch order has already been canceled",
  },
  isNotCanceled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.isNotCanceled",
    description: "Text when the batch order is not canceled",
    defaultMessage: "You must cancel the batch order before refunding it.",
  },
  cancelBatchOrder: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.cancelBatchOrder",
    description: "Label for the cancel batch order action",
    defaultMessage: "Cancel this batch order",
  },
});

type Props = {
  batchOrder: BatchOrder;
};

export default function BatchOrderActionsButton({ batchOrder }: Props) {
  const intl = useIntl();
  const batchOrdersQuery = useBatchOrders({}, { enabled: false });
  const batchOrderQuery = useBatchOrder(order.id);

  const options = useMemo(() => {
    const allOptions: MenuOption[] = [
      {
        icon: <CancelIcon />,
        mainLabel: intl.formatMessage(messages.cancelBatchOrder),
        isDisable: [BatchOrderStatesEnum.BATCH_ORDER_STATE_CANCELED].includes(
          batchOrder.state,
        ),
        disableMessage: intl.formatMessage(messages.alreadyCancelTooltip),
        onClick: async () => {
          await batchOrderQuery.methods.delete(batchOrder.id, {
            onSuccess: batchOrdersQuery.methods.invalidate,
          });
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
      label={intl.formatMessage(messages.batchOrderActionsLabel)}
      id="order-view-action-button"
      variant="outlined"
      options={options}
    />
  );
}
