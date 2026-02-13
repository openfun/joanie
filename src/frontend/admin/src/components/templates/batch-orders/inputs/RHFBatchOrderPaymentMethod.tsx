import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { BatchOrderPaymentMethodEnum } from "@/services/api/models/BatchOrder";
import { batchOrderPaymentMethodsMessages } from "@/components/templates/batch-orders/view/translations";

const messages = defineMessages({
  paymentMethod: {
    id: "components.templates.batchOrders.input.RHFBatchOrderPaymentMethod.paymentMethod",
    description: "Label text for the select payment method input",
    defaultMessage: "Payment method",
  },
});

export function RHFBatchOrderPaymentMethod(props: RHFSelectProps) {
  const intl = useIntl();

  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(BatchOrderPaymentMethodEnum).forEach((v) => {
      result.push({
        label: intl.formatMessage(batchOrderPaymentMethodsMessages[v]),
        value: v,
      });
    });
    return result;
  }, []);

  return (
    <RHFSelect
      options={options}
      getOptionLabel={(value: BatchOrderPaymentMethodEnum) =>
        intl.formatMessage(batchOrderPaymentMethodsMessages[value])
      }
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.paymentMethod)}
    />
  );
}
