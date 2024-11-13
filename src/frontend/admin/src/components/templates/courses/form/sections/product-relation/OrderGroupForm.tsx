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

const messages = defineMessages({
  numberOfSeatInputLabel: {
    id: "components.templates.products.form.sections.OderGroups.OrderGroupForm.numberOfSeatInputLabel",
    defaultMessage: "Number of seats",
    description: "The input label for the number of seats",
  },
  isActiveLabel: {
    id: "components.templates.products.form.sections.OderGroups.OrderGroupForm.isActiveLabel",
    defaultMessage: "Activate this order group",
    description: "The input label for the activate switch",
  },
});

export type OrderGroupFormValues = {
  nb_seats: number;
  is_active: boolean;
};

type Props = {
  orderGroup?: Maybe<OrderGroup>;
  onSubmit?: (values: OrderGroupFormValues) => void;
};

const getMinNbSeats = (orderGroup?: OrderGroup): number => {
  if (!orderGroup) {
    return 0;
  }
  return orderGroup.nb_seats - orderGroup.nb_available_seats;
};

export function OrderGroupForm({ orderGroup, onSubmit }: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    nb_seats: Yup.number().min(getMinNbSeats(orderGroup)).required(),
    is_active: Yup.boolean().required(),
  });

  const getDefaultValues = () => ({
    nb_seats: orderGroup?.nb_seats ?? 0,
    is_active: orderGroup?.is_active ?? false,
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
          <RHFSwitch
            name="is_active"
            label={intl.formatMessage(messages.isActiveLabel)}
          />
        </Grid2>
      </Grid2>
    </RHFProvider>
  );
}
