import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { VoucherQuery } from "@/services/api/models/Voucher";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.vouchers.filters.VoucherFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by code or discount",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter: (values: VoucherQuery) => void;
};

export function VoucherFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
    />
  );
}
