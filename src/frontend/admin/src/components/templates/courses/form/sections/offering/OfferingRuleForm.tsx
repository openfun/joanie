import * as React from "react";
import { useEffect } from "react";
import { defineMessages, useIntl } from "react-intl";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid2 from "@mui/material/Grid2";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { OfferingRule } from "@/services/api/models/OfferingRule";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";
import { Maybe } from "@/types/utils";
import { DiscountSelect } from "@/components/presentational/discount/DiscountSelect";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";

const messages = defineMessages({
  descriptionInputLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.descriptionInputLabel",
    defaultMessage: "Description",
    description: "The input label for the description",
  },
  numberOfSeatInputLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.numberOfSeatInputLabel",
    defaultMessage: "Number of seats",
    description: "The input label for the number of seats",
  },
  startLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.startLabel",
    defaultMessage: "Start date",
    description: "The input label for the start date",
  },
  endLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.endLabel",
    defaultMessage: "End date",
    description: "The input label for the end date",
  },
  isActiveLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.isActiveLabel",
    defaultMessage: "Activate this offering rule",
    description: "The input label for the activate switch",
  },
  discountLabel: {
    id: "components.templates.products.form.sections.OfferingRules.OfferingRuleForm.discountLabel",
    defaultMessage: "Discount",
    description: "The input label for the discount select",
  },
});

export type OfferingRuleFormValues = {
  description?: string | null | undefined;
  nb_seats?: number | null | undefined;
  is_active: boolean;
  discount_id?: string | null | undefined;
};

type Props = {
  offeringRule?: Maybe<OfferingRule>;
  onSubmit?: (values: OfferingRuleFormValues) => void;
};

const getMinNbSeats = (offeringRule?: OfferingRule): number => {
  if (!offeringRule) {
    return 0;
  }
  return (offeringRule.nb_seats ?? 0) - (offeringRule.nb_available_seats ?? 0);
};

export function OfferingRuleForm({ offeringRule, onSubmit }: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    nb_seats: Yup.number().min(getMinNbSeats(offeringRule)).nullable(),
    start: Yup.string().nullable(),
    end: Yup.string().nullable(),
    is_active: Yup.boolean().required(),
    discount_id: Yup.string().nullable(),
  });

  const getDefaultValues = () => ({
    nb_seats: offeringRule?.nb_seats ?? null,
    start: offeringRule?.start ?? null,
    end: offeringRule?.end ?? null,
    is_active: offeringRule?.is_active ?? false,
    discount_id: offeringRule?.discount?.id ?? null,
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  useEffect(() => {
    form.reset(getDefaultValues());
  }, [offeringRule]);

  return (
    <RHFProvider
      methods={form}
      id="offering-rule-form"
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
