import * as React from "react";
import Switch from "@mui/material/Switch";
import { defineMessages, useIntl } from "react-intl";
import { SxProps } from "@mui/material/styles";
import Box from "@mui/material/Box";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { OrderGroup, OrderGroupDummy } from "@/services/api/models/OrderGroup";
import { getDiscountLabel } from "@/services/api/models/Discount";

const messages = defineMessages({
  mainTitleOrderGroup: {
    id: "components.templates.courses.form.productRelation.row.mainTitleOrderGroup",
    description: "Title for the order group row",
    defaultMessage: "Order group {number}",
  },
  subTitleOrderGroup: {
    id: "components.templates.courses.form.productRelation.row.subTitleOrderGroup",
    description: "Sub title for the order group row",
    defaultMessage: "{reservedSeats}/{totalSeats} seats",
  },
  startLabel: {
    id: "components.templates.courses.form.productRelation.row.startLabel",
    description: "Start date label",
    defaultMessage: "From: ",
  },
  endLabel: {
    id: "components.templates.courses.form.productRelation.row.endLabel",
    description: "End date label",
    defaultMessage: "To: ",
  },
  discountLabel: {
    id: "components.templates.courses.form.productRelation.row.discountLabel",
    description: "Discount label",
    defaultMessage: "Discount: ",
  },
  addOrderGroupButton: {
    id: "components.templates.courses.form.productRelation.row.addOrderGroupButton",
    description: "Add order group button label",
    defaultMessage: "Add order group",
  },
  orderGroupIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.productRelation.row.orderGroupIsActiveSwitchAriaLabel",
    description: "Aria-label for the order group is active switch",
    defaultMessage: "Order group is active switch",
  },
  orderGroupDisabledActionsMessage: {
    id: "components.templates.courses.form.productRelation.row.orderGroupDisabledActionsMessage",
    description: "Information message for order group disabled actions",
    defaultMessage:
      "Seats have already been reserved, so you cannot perform this action.",
  },
});

const isOrderGroup = (
  item: OrderGroup | OrderGroupDummy,
): item is OrderGroup => {
  if (!item) return false;
  return "id" in item;
};

const isOrderGroupDummy = (
  item: OrderGroup | OrderGroupDummy,
): item is OrderGroupDummy => {
  if (!item) return false;
  return "dummyId" in item;
};

type Props = {
  orderGroup: OrderGroup | OrderGroupDummy;
  orderIndex: number;
  onDelete?: () => void;
  onEdit?: () => void;
  onUpdateIsActive?: (isActive: boolean) => void;
};
export function OrderGroupRow({
  orderGroup,
  orderIndex,
  onUpdateIsActive,
  onDelete,
  onEdit,
}: Props) {
  const canEdit = orderGroup.can_edit;
  const intl = useIntl();
  const mainTitle = intl.formatMessage(messages.mainTitleOrderGroup, {
    number: orderIndex + 1,
  });

  function getSubTitle() {
    const rules: string[] = [];

    if (orderGroup.nb_available_seats !== null) {
      const reservedSeats =
        (orderGroup.nb_seats ?? 0) - (orderGroup.nb_available_seats ?? 0);
      const totalSeats = orderGroup.nb_seats;
      rules.push(
        intl.formatMessage(messages.subTitleOrderGroup, {
          reservedSeats,
          totalSeats,
        }),
      );
    }

    if (orderGroup.start) {
      rules.push(
        intl.formatMessage(messages.startLabel) +
          intl.formatTime(new Date(orderGroup.start), {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          }),
      );
    }

    if (orderGroup.end) {
      rules.push(
        intl.formatMessage(messages.endLabel) +
          intl.formatTime(new Date(orderGroup.end), {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          }),
      );
    }

    if (orderGroup.discount) {
      rules.push(
        intl.formatMessage(messages.discountLabel) +
          getDiscountLabel(orderGroup.discount),
      );
    }

    return (
      <>
        {rules.map((rule, index) => (
          <Box key={`${rule}-${index}`} sx={{ mt: 0 }}>
            {rule}
          </Box>
        ))}
      </>
    );
  }

  const sxProps: SxProps = { backgroundColor: "background" };
  const disableMessage = !canEdit
    ? intl.formatMessage(messages.orderGroupDisabledActionsMessage)
    : undefined;

  if (isOrderGroupDummy(orderGroup)) {
    return (
      <DefaultRow
        testId={`order-group-${orderGroup.dummyId}`}
        key={orderGroup.dummyId}
        enableDelete={false}
        enableEdit={false}
        loading={true}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={getSubTitle()}
      />
    );
  }

  if (isOrderGroup(orderGroup)) {
    return (
      <DefaultRow
        testId={`order-group-${orderGroup.id}`}
        key={orderGroup.id}
        deleteTestId={`delete-order-group-${orderGroup.id}`}
        enableDelete={canEdit}
        enableEdit={canEdit}
        disableEditMessage={disableMessage}
        disableDeleteMessage={disableMessage}
        onDelete={onDelete}
        onEdit={onEdit}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={getSubTitle()}
        permanentRightActions={
          <Switch
            inputProps={{
              "aria-label": intl.formatMessage(
                messages.orderGroupIsActiveSwitchAriaLabel,
              ),
            }}
            size="small"
            data-testid={`is-active-switch-order-group-${orderGroup.id}`}
            disabled={!canEdit}
            onChange={(event, checked) => {
              onUpdateIsActive?.(checked);
            }}
            checked={orderGroup.is_active}
          />
        }
      />
    );
  }

  return undefined;
}
