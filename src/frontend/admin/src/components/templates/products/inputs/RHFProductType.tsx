import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { productTypesMessages } from "@/translations/products/types";
import { ProductType } from "@/services/api/models/Product";

const messages = defineMessages({
  type: {
    id: "components.templates.products.input.RHFProductType.type",
    description: "Label text for the select types input",
    defaultMessage: "Type",
  },
});

export function RHFProductType(props: RHFSelectProps) {
  const intl = useIntl();

  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(ProductType).forEach((v) => {
      result.push({
        label: intl.formatMessage(productTypesMessages[v]),
        value: v,
      });
    });
    return result;
  }, []);

  return (
    <RHFSelect
      options={options}
      getOptionLabel={(value: ProductType) =>
        intl.formatMessage(productTypesMessages[value])
      }
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.type)}
    />
  );
}
