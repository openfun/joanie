import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import {
  RHFSelect,
  RHFSelectProps,
} from "@/components/presentational/hook-form/RHFSelect";
import { SearchFilterComponentProps } from "@/components/presentational/filters/SearchFilters";
import { CertificateDefinitionRepository } from "@/services/repositories/certificate-definition/CertificateDefinitionRepository";

const messages = defineMessages({
  templateLabel: {
    id: "components.templates.certificateDefinition.form.RHFCertificateDefinitionTemplates.templateLabel",
    defaultMessage: "Template",
    description: "Label for the certificate definition template input",
  },
});

type Props = SearchFilterComponentProps &
  RHFSelectProps & {
    name: string;
  };

export function RHFCertificateDefinitionTemplates({
  name,
  isFilterContext,
}: Props) {
  const intl = useIntl();

  const languages = useQuery({
    queryKey: ["certificateDefinitionTemplates"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => {
      return CertificateDefinitionRepository.getAllTemplates();
    },
  });

  return (
    <RHFSelect
      data-testid="certificate-template-select"
      disabled={languages.isLoading}
      name={name}
      options={languages.data ?? []}
      isFilterContext={isFilterContext}
      label={intl.formatMessage(messages.templateLabel)}
    />
  );
}
