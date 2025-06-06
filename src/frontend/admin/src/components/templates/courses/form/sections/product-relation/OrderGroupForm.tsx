import * as React from "react";
import { useEffect } from "react";
import { defineMessages, useIntl } from "react-intl";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid2 from "@mui/material/Grid2";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { OfferRule } from "@/services/api/models/OfferRule";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";
import { Maybe } from "@/types/utils";
import { DiscountSelect } from "@/components/presentational/discount/DiscountSelect";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";

const messages = defineMessages({
  descriptionInputLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.descriptionInputLabel",
    defaultMessage: "Description",
    description: "The input label for the description",
  },
  numberOfSeatInputLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.numberOfSeatInputLabel",
    defaultMessage: "Number of seats",
    description: "The input label for the number of seats",
  },
  startLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.startLabel",
    defaultMessage: "Start date",
    description: "The input label for the start date",
  },
  endLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.endLabel",
    defaultMessage: "End date",
    description: "The input label for the end date",
  },
  isActiveLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.isActiveLabel",
    defaultMessage: "Activate this offer rule",
    description: "The input label for the activate switch",
  },
  discountLabel: {
    id: "components.templates.products.form.sections.OfferRules.OfferRuleForm.discountLabel",
    defaultMessage: "Discount",
    description: "The input label for the discount select",
  },
});

export type OfferRuleFormValues = {
  description?: string | null | undefined;
  nb_seats?: number | null | undefined;
  is_active: boolean;
  discount_id?: string | null | undefined;
};

type Props = {
  offerRule?: Maybe<OfferRule>;
  onSubmit?: (values: OfferRuleFormValues) => void;
};

const getMinNbSeats = (offerRule?: OfferRule): number => {
  if (!offerRule) {
    return 0;
  }
  return (offerRule.nb_seats ?? 0) - (offerRule.nb_available_seats ?? 0);
};

export function OfferRuleForm({ offerRule, onSubmit }: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    nb_seats: Yup.number().min(getMinNbSeats(offerRule)).nullable(),
    start: Yup.string().nullable(),
    end: Yup.string().nullable(),
    is_active: Yup.boolean().required(),
    discount_id: Yup.string().nullable(),
  });

  const getDefaultValues = () => ({
    nb_seats: offerRule?.nb_seats ?? null,
    start: offerRule?.start ?? null,
    end: offerRule?.end ?? null,
    is_active: offerRule?.is_active ?? false,
    discount_id: offerRule?.discount?.id ?? null,
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  useEffect(() => {
    form.reset(getDefaultValues());
  }, [offerRule]);

  return (
    <RHFProvider
      methods={form}
      id="offer-rule-form"
      onSubmit={form.handleSubmit((values) => onSubmit?.(values))}
    >
      <Grid2 container spacing={2}>
        <Grid2 size={12}>
          <RHFTextField
            type="text"
            name="description"
            label={intl.formatMessage(messages.descriptionInputLabel)}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFTextField
            type="number"
            name="nb_seats"
            label={intl.formatMessage(messages.numberOfSeatInputLabel)}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFDateTimePicker
            name="start"
            label={intl.formatMessage(messages.startLabel)}
            slotProps={{ field: { clearable: true } }}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFDateTimePicker
            name="end"
            label={intl.formatMessage(messages.endLabel)}
            slotProps={{ field: { clearable: true } }}
          />
        </Grid2>
        <Grid2 size={12}>
          <DiscountSelect
            name="discount_id"
            label={intl.formatMessage(messages.discountLabel)}
            helperText={form.formState.errors.discount_id?.message}
          />
        </Grid2>
        <Grid2 size={12}>
          <RHFSwitch
            name="is_active"
            label={intl.formatMessage(messages.isActiveLabel)}
          />
        </Grid2>
      </Grid2>
    </RHFProvider>
  );
}
