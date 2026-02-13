import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { BatchOrderStatesEnum } from "@/services/api/models/BatchOrder";
import { batchOrderStatesMessages } from "@/components/templates/batch-orders/view/translations";

const messages = defineMessages({
  state: {
    id: "components.templates.batchOrders.input.RHFBatchOrderState.state",
    description: "Label text for the select state input",
    defaultMessage: "State",
  },
});

export function RHFBatchOrderState(props: RHFSelectProps) {
  const intl = useIntl();

  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(BatchOrderStatesEnum).forEach((v) => {
      result.push({
        label: intl.formatMessage(batchOrderStatesMessages[v]),
        value: v,
      });
    });
    return result;
  }, []);

  return (
    <RHFSelect
      options={options}
      getOptionLabel={(value: BatchOrderStatesEnum) =>
        intl.formatMessage(batchOrderStatesMessages[value])
      }
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.state)}
    />
  );
}
