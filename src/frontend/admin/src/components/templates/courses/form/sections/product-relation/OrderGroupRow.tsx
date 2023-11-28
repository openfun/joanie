import * as React from "react";
import Switch from "@mui/material/Switch";
import { defineMessages, useIntl } from "react-intl";
import { SxProps } from "@mui/material/styles";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { OrderGroup, OrderGroupDummy } from "@/services/api/models/OrderGroup";

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
  return "id" in item;
};

const isOrderGroupDummy = (
  item: OrderGroup | OrderGroupDummy,
): item is OrderGroupDummy => {
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
  const subTitle = intl.formatMessage(messages.subTitleOrderGroup, {
    reservedSeats: orderGroup.nb_seats - orderGroup.nb_available_seats,
    totalSeats: orderGroup.nb_seats,
  });

  const sxProps: SxProps = { backgroundColor: "white" };
  const disableMessage = !canEdit
    ? intl.formatMessage(messages.orderGroupDisabledActionsMessage)
    : undefined;

  if (isOrderGroupDummy(orderGroup)) {
    return (
      <DefaultRow
        key={orderGroup.dummyId}
        enableDelete={false}
        enableEdit={false}
        loading={true}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={subTitle}
      />
    );
  }

  if (isOrderGroup(orderGroup)) {
    return (
      <DefaultRow
        key={orderGroup.id}
        enableDelete={canEdit}
        enableEdit={canEdit}
        disableEditMessage={disableMessage}
        disableDeleteMessage={disableMessage}
        onDelete={onDelete}
        onEdit={onEdit}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={subTitle}
        permanentRightActions={
          <Switch
            inputProps={{
              "aria-label": intl.formatMessage(
                messages.orderGroupIsActiveSwitchAriaLabel,
              ),
            }}
            size="small"
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
