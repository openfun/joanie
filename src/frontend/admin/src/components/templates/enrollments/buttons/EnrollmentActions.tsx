import * as React from "react";
import { useMemo } from "react";
import CancelIcon from "@mui/icons-material/Cancel";
import { defineMessages, useIntl } from "react-intl";
import { OrderStatesEnum } from "@/services/api/models/Order";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import {
  useEnrollment,
  useEnrollments,
} from "@/hooks/useEnrollments/useEnrollments";
import { Enrollment } from "@/services/api/models/Enrollment";

const messages = defineMessages({
  enrollmentActionsLabel: {
    id: "components.templates.enrollments.buttons.enrollmentActionsButton.enrollmentActionsLabel",
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
  enrollment: Enrollment;
};

export default function EnrollmentActionsButton({ enrollment }: Props) {
  const intl = useIntl();
  const ordersQuery = useEnrollments({}, { enabled: false });
  const orderQuery = useEnrollment(order.id);

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
      data-testid="enrollment-view-action-button"
      label={intl.formatMessage(messages.enrollmentActionsLabel)}
      id="order-view-action-button"
      variant="contained"
      color="secondary"
      options={options}
    />
  );
}
