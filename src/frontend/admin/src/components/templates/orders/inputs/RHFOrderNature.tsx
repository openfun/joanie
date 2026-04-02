import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { OrderNatureEnum } from "@/services/api/models/Order";
import { orderNatureMessages } from "@/components/templates/orders/view/translations";

const messages = defineMessages({
  nature: {
    id: "components.templates.orders.input.RHFOrderNature.nature",
    description: "Label text for the select nature input",
    defaultMessage: "Nature",
  },
});

export function RHFOrderNature(props: RHFSelectProps) {
  const intl = useIntl();

  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(OrderNatureEnum).forEach((v) => {
      result.push({
        label: intl.formatMessage(orderNatureMessages[v]),
        value: v,
      });
    });
    return result;
  }, []);

  return (
    <RHFSelect
      options={options}
      getOptionLabel={(value: OrderNatureEnum) =>
        intl.formatMessage(orderNatureMessages[value])
      }
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.nature)}
    />
  );
}
