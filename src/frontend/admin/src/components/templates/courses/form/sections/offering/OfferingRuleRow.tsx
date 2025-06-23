import * as React from "react";
import Switch from "@mui/material/Switch";
import { defineMessages, useIntl } from "react-intl";
import { SxProps } from "@mui/material/styles";
import Box from "@mui/material/Box";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import {
  OfferingRule,
  OfferingRuleDummy,
} from "@/services/api/models/OfferingRule";
import { getDiscountLabel } from "@/services/api/models/Discount";
import { formatShortDate } from "@/utils/dates";

const messages = defineMessages({
  mainTitleOfferingRule: {
    id: "components.templates.courses.form.productRelation.row.mainTitleOfferingRule",
    description: "Title for the offering rule row",
    defaultMessage: "Offering rule {number}",
  },
  subTitleOfferingRule: {
    id: "components.templates.courses.form.productRelation.row.subTitleOfferingRule",
    description: "Sub title for the offering rule row",
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
  addOfferingRuleButton: {
    id: "components.templates.courses.form.productRelation.row.addOfferingRuleButton",
    description: "Add offering rule button label",
    defaultMessage: "Add offering rule",
  },
  offeringRuleIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.productRelation.row.offeringRuleIsActiveSwitchAriaLabel",
    description: "Aria-label for the offering rule is active switch",
    defaultMessage: "Offering rule is active switch",
  },
  offeringRuleDisabledActionsMessage: {
    id: "components.templates.courses.form.productRelation.row.offeringRuleDisabledActionsMessage",
    description: "Information message for offering rule disabled actions",
    defaultMessage:
      "Seats have already been reserved, so you cannot perform this action.",
  },
});

const isOfferingRule = (
  item: OfferingRule | OfferingRuleDummy,
): item is OfferingRule => {
  if (!item) return false;
  return "id" in item;
};

const isOfferingRuleDummy = (
  item: OfferingRule | OfferingRuleDummy,
): item is OfferingRuleDummy => {
  if (!item) return false;
  return "dummyId" in item;
};

type Props = {
  offeringRule: OfferingRule | OfferingRuleDummy;
  orderIndex: number;
  onDelete?: () => void;
  onEdit?: () => void;
  onUpdateIsActive?: (isActive: boolean) => void;
};
export function OfferingRuleRow({
  offeringRule,
  orderIndex,
  onUpdateIsActive,
  onDelete,
  onEdit,
}: Props) {
  const canEdit = offeringRule.can_edit;
  const intl = useIntl();
  const mainTitle = intl.formatMessage(messages.mainTitleOfferingRule, {
    number: orderIndex + 1,
  });

  function getSubTitle() {
    const rules: string[] = [];

    if (offeringRule.description) {
      rules.push(offeringRule.description);
    }

    if (offeringRule.nb_available_seats !== null) {
      const reservedSeats =
        (offeringRule.nb_seats ?? 0) - (offeringRule.nb_available_seats ?? 0);
      const totalSeats = offeringRule.nb_seats;
      rules.push(
        intl.formatMessage(messages.subTitleOfferingRule, {
          reservedSeats,
          totalSeats,
        }),
      );
    }

    if (offeringRule.start) {
      rules.push(
        intl.formatMessage(messages.startLabel) +
          formatShortDate(offeringRule.start),
      );
    }

    if (offeringRule.end) {
      rules.push(
        intl.formatMessage(messages.endLabel) +
          formatShortDate(offeringRule.end),
      );
    }

    if (offeringRule.discount) {
      rules.push(
        intl.formatMessage(messages.discountLabel) +
          getDiscountLabel(offeringRule.discount),
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
    ? intl.formatMessage(messages.offeringRuleDisabledActionsMessage)
    : undefined;

  if (isOfferingRuleDummy(offeringRule)) {
    return (
      <DefaultRow
        testId={`offering-rule-${offeringRule.dummyId}`}
        key={offeringRule.dummyId}
        enableDelete={false}
        enableEdit={false}
        loading={true}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={getSubTitle()}
      />
    );
  }

  if (isOfferingRule(offeringRule)) {
    return (
      <DefaultRow
        testId={`offering-rule-${offeringRule.id}`}
        key={offeringRule.id}
        deleteTestId={`delete-offering-rule-${offeringRule.id}`}
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
                messages.offeringRuleIsActiveSwitchAriaLabel,
              ),
            }}
            size="small"
            data-testid={`is-active-switch-offering-rule-${offeringRule.id}`}
            disabled={!canEdit}
            onChange={(event, checked) => {
              onUpdateIsActive?.(checked);
            }}
            checked={offeringRule.is_active}
          />
        }
      />
    );
  }

  return undefined;
}
