import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.certificatesDefinitions.filters.CertificateDefinitionFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title, code",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter?: (values: any) => void;
};

export function OrganizationFilters({ onFilter, ...searchFilterProps }: Props) {
  const intl = useIntl();

  return (
    <SearchFilters
      {...searchFilterProps}
      searchInputPlaceholder={intl.formatMessage(messages.searchPlaceholder)}
    />
  );
}
