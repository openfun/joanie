import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { VoucherQuery } from "@/services/api/models/Voucher";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.vouchers.filters.VoucherFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by code",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter: (values: VoucherQuery) => void;
};

export function VoucherFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  const getDefaultValues = () => {
    return {};
  };

  const RegisterSchema = Yup.object().shape({});

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues() as any, // To not trigger type validation for default value
  });

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
      renderContent={() => (
        <RHFProvider
          id="voucher-filter-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            updateUrl={true}
            useAnotherValueReference={false}
            onSubmit={onFilter}
          >
            {/* No additional voucher-specific fields for now */}
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
