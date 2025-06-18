import * as React from "react";
import Switch from "@mui/material/Switch";
import { defineMessages, useIntl } from "react-intl";
import { SxProps } from "@mui/material/styles";
import Box from "@mui/material/Box";
import { DefaultRow } from "@/components/presentational/list/DefaultRow";
import { OfferRule, OfferRuleDummy } from "@/services/api/models/OfferRule";
import { getDiscountLabel } from "@/services/api/models/Discount";
import { formatShortDate } from "@/utils/dates";

const messages = defineMessages({
  mainTitleOfferRule: {
    id: "components.templates.courses.form.productRelation.row.mainTitleOfferRule",
    description: "Title for the offer rule row",
    defaultMessage: "Offer rule {number}",
  },
  subTitleOfferRule: {
    id: "components.templates.courses.form.productRelation.row.subTitleOfferRule",
    description: "Sub title for the offer rule row",
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
  addOfferRuleButton: {
    id: "components.templates.courses.form.productRelation.row.addOfferRuleButton",
    description: "Add offer rule button label",
    defaultMessage: "Add offer rule",
  },
  offerRuleIsActiveSwitchAriaLabel: {
    id: "components.templates.courses.form.productRelation.row.offerRuleIsActiveSwitchAriaLabel",
    description: "Aria-label for the offer rule is active switch",
    defaultMessage: "Offer rule is active switch",
  },
  offerRuleDisabledActionsMessage: {
    id: "components.templates.courses.form.productRelation.row.offerRuleDisabledActionsMessage",
    description: "Information message for offer rule disabled actions",
    defaultMessage:
      "Seats have already been reserved, so you cannot perform this action.",
  },
});

const isOfferRule = (item: OfferRule | OfferRuleDummy): item is OfferRule => {
  if (!item) return false;
  return "id" in item;
};

const isOfferRuleDummy = (
  item: OfferRule | OfferRuleDummy,
): item is OfferRuleDummy => {
  if (!item) return false;
  return "dummyId" in item;
};

type Props = {
  offerRule: OfferRule | OfferRuleDummy;
  orderIndex: number;
  onDelete?: () => void;
  onEdit?: () => void;
  onUpdateIsActive?: (isActive: boolean) => void;
};
export function OfferRuleRow({
  offerRule,
  orderIndex,
  onUpdateIsActive,
  onDelete,
  onEdit,
}: Props) {
  const canEdit = offerRule.can_edit;
  const intl = useIntl();
  const mainTitle = intl.formatMessage(messages.mainTitleOfferRule, {
    number: orderIndex + 1,
  });

  function getSubTitle() {
    const rules: string[] = [];

    if (offerRule.description) {
      rules.push(offerRule.description);
    }

    if (offerRule.nb_available_seats !== null) {
      const reservedSeats =
        (offerRule.nb_seats ?? 0) - (offerRule.nb_available_seats ?? 0);
      const totalSeats = offerRule.nb_seats;
      rules.push(
        intl.formatMessage(messages.subTitleOfferRule, {
          reservedSeats,
          totalSeats,
        }),
      );
    }

    if (offerRule.start) {
      rules.push(
        intl.formatMessage(messages.startLabel) +
          formatShortDate(offerRule.start),
      );
    }

    if (offerRule.end) {
      rules.push(
        intl.formatMessage(messages.endLabel) + formatShortDate(offerRule.end),
      );
    }

    if (offerRule.discount) {
      rules.push(
        intl.formatMessage(messages.discountLabel) +
          getDiscountLabel(offerRule.discount),
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
    ? intl.formatMessage(messages.offerRuleDisabledActionsMessage)
    : undefined;

  if (isOfferRuleDummy(offerRule)) {
    return (
      <DefaultRow
        testId={`offer-rule-${offerRule.dummyId}`}
        key={offerRule.dummyId}
        enableDelete={false}
        enableEdit={false}
        loading={true}
        sx={sxProps}
        mainTitle={mainTitle}
        subTitle={getSubTitle()}
      />
    );
  }

  if (isOfferRule(offerRule)) {
    return (
      <DefaultRow
        testId={`offer-rule-${offerRule.id}`}
        key={offerRule.id}
        deleteTestId={`delete-offer-rule-${offerRule.id}`}
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
                messages.offerRuleIsActiveSwitchAriaLabel,
              ),
            }}
            size="small"
            data-testid={`is-active-switch-offer-rule-${offerRule.id}`}
            disabled={!canEdit}
            onChange={(event, checked) => {
              onUpdateIsActive?.(checked);
            }}
            checked={offerRule.is_active}
          />
        }
      />
    );
  }

  return undefined;
}
