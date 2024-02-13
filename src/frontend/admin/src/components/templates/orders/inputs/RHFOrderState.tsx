import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { OrderStatesEnum } from "@/services/api/models/Order";
import { orderStatesMessages } from "@/components/templates/orders/view/translations";

const messages = defineMessages({
  state: {
    id: "components.templates.coursesRuns.input.RHFOrderState.state",
    description: "Label text for the select state input",
    defaultMessage: "State",
  },
});

export function RHFOrderState(props: RHFSelectProps) {
  const intl = useIntl();

  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(OrderStatesEnum).forEach((v) => {
      result.push({
        label: intl.formatMessage(orderStatesMessages[v]),
        value: v,
      });
    });
    return result;
  }, []);

  return (
    <RHFSelect
      options={options}
      getOptionLabel={(value: OrderStatesEnum) =>
        intl.formatMessage(orderStatesMessages[value])
      }
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.state)}
    />
  );
}
