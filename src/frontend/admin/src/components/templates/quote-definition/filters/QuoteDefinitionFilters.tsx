import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { RHFQuoteDefinitionLanguage } from "@/components/templates/quote-definition/inputs/RHFQuoteDefinitionLanguage";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.quoteDefinition.filters.QuoteDefinitionFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter: (values: any) => void;
};

export function QuoteDefinitionFilters({
  onFilter,
  ...searchFilterProps
}: Props) {
  const intl = useIntl();
  const getDefaultValues = () => {
    return {
      language: "",
    };
  };
  const RegisterSchema = Yup.object().shape({
    language: Yup.string().nullable(),
  });

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
          id="quote-definition-filter-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            useAnotherValueReference={true}
            updateUrl={true}
            onSubmit={onFilter}
          >
            <Grid container mt={2} spacing={2}>
              <Grid size={12}>
                <RHFQuoteDefinitionLanguage
                  isFilterContext={true}
                  name="language"
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
