import * as React from "react";
import { useEffect } from "react";
import { defineMessages, useIntl } from "react-intl";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid2 from "@mui/material/Grid2";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { OrderGroup } from "@/services/api/models/OrderGroup";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import RHFSwitch from "@/components/presentational/hook-form/RHFSwitch";
import { Maybe } from "@/types/utils";
import { DiscountSelect } from "@/components/presentational/discount/DiscountSelect";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";

const messages = defineMessages({
  numberOfSeatInputLabel: {
    id: "components.templates.products.form.sections.OrderGroups.OrderGroupForm.numberOfSeatInputLabel",
    defaultMessage: "Number of seats",
    description: "The input label for the number of seats",
  },
  startLabel: {
    id: "components.templates.products.form.sections.OrderGroups.OrderGroupForm.startLabel",
    defaultMessage: "Start date",
    description: "The input label for the start date",
  },
  endLabel: {
    id: "components.templates.products.form.sections.OrderGroups.OrderGroupForm.endLabel",
    defaultMessage: "End date",
    description: "The input label for the end date",
  },
  isActiveLabel: {
    id: "components.templates.products.form.sections.OrderGroups.OrderGroupForm.isActiveLabel",
    defaultMessage: "Activate this order group",
    description: "The input label for the activate switch",
  },
  discountLabel: {
    id: "components.templates.products.form.sections.OrderGroups.OrderGroupForm.discountLabel",
    defaultMessage: "Discount",
    description: "The input label for the discount select",
  },
});

export type OrderGroupFormValues = {
  nb_seats?: number | null | undefined;
  is_active: boolean;
  discount_id?: string | null | undefined;
};

type Props = {
  orderGroup?: Maybe<OrderGroup>;
  onSubmit?: (values: OrderGroupFormValues) => void;
};

const getMinNbSeats = (orderGroup?: OrderGroup): number => {
  if (!orderGroup) {
    return 0;
  }
  return (orderGroup.nb_seats ?? 0) - (orderGroup.nb_available_seats ?? 0);
};

export function OrderGroupForm({ orderGroup, onSubmit }: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    nb_seats: Yup.number().min(getMinNbSeats(orderGroup)).nullable(),
    start: Yup.string().nullable(),
    end: Yup.string().nullable(),
    is_active: Yup.boolean().required(),
    discount_id: Yup.string().nullable(),
  });

  const getDefaultValues = () => ({
    nb_seats: orderGroup?.nb_seats ?? null,
    start: orderGroup?.start ?? null,
    end: orderGroup?.end ?? null,
    is_active: orderGroup?.is_active ?? false,
    discount_id: orderGroup?.discount?.id ?? null,
  });

  const form = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  useEffect(() => {
    form.reset(getDefaultValues());
  }, [orderGroup]);

  return (
    <RHFProvider
      methods={form}
      id="order-group-form"
      onSubmit={form.handleSubmit((values) => onSubmit?.(values))}
    >
      <Grid2 container spacing={2}>
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
