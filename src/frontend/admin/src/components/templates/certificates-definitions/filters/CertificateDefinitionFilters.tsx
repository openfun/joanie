import * as React from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import { defineMessages, useIntl } from "react-intl";
import {
  MandatorySearchFilterProps,
  SearchFilters,
} from "@/components/presentational/filters/SearchFilters";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFValuesChange } from "@/components/presentational/hook-form/RFHValuesChange";
import { RHFCertificateDefinitionTemplates } from "@/components/templates/certificates-definitions/inputs/RHFCertificateDefinitionTemplates";
import { CertificateDefinitionResourceQuery } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";

const messages = defineMessages({
  searchPlaceholder: {
    id: "components.templates.certificatesDefinitions.filters.CertificateDefinitionFilters.searchPlaceholder",
    description: "Text for the search input placeholder",
    defaultMessage: "Search by title or name",
  },
});

type Props = MandatorySearchFilterProps & {
  onFilter: (values: CertificateDefinitionResourceQuery) => void;
};

export function CertificateDefinitionFilters({
  onFilter,
  ...searchFilterProps
}: Props) {
  const intl = useIntl();
  const getDefaultValues = () => {
    return {
      template: "",
    };
  };
  const RegisterSchema = Yup.object().shape({
    template: Yup.string().nullable(),
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
          id="certificate-definition-filter-form"
          showSubmit={false}
          methods={methods}
        >
          <RHFValuesChange
            debounceTime={200}
            updateUrl={true}
            useAnotherValueReference={true}
            onSubmit={onFilter}
          >
            <Grid container mt={2} spacing={2}>
              <Grid xs={12}>
                <RHFCertificateDefinitionTemplates
                  isFilterContext={true}
                  name="template"
                />
              </Grid>
            </Grid>
          </RHFValuesChange>
        </RHFProvider>
      )}
    />
  );
}
