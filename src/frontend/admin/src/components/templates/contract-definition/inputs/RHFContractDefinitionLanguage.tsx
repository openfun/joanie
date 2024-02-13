import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import { languageTranslations } from "@/translations/common/languageTranslations";
import {
  RHFSelect,
  RHFSelectProps,
} from "@/components/presentational/hook-form/RHFSelect";
import { SearchFilterComponentProps } from "@/components/presentational/filters/SearchFilters";
import { LocalesEnum } from "@/types/i18n/LocalesEnum";
import { ContractDefinitionRepository } from "@/services/repositories/contract-definition/ContractDefinitionRepository";

const messages = defineMessages({
  languageLabel: {
    id: "components.templates.contractDefinitions.form.RhfContractDefinitionLanguage.languageLabel",
    defaultMessage: "Language",
    description: "Label for the language input",
  },
});

type Props = SearchFilterComponentProps &
  RHFSelectProps & {
    name: string;
  };

export function RHFContractDefinitionLanguage({
  name,
  isFilterContext,
}: Props) {
  const intl = useIntl();

  const defaultLanguages = [
    {
      label: intl.formatMessage(languageTranslations[LocalesEnum.FRENCH]),
      value: LocalesEnum.FRENCH,
    },
    {
      label: intl.formatMessage(languageTranslations[LocalesEnum.ENGLISH]),
      value: LocalesEnum.ENGLISH,
    },
  ];

  const languages = useQuery({
    queryKey: ["contractDefinitionLanguages"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => {
      return ContractDefinitionRepository.getAllLanguages();
    },
  });

  return (
    <RHFSelect
      data-testid="contract-definition-language-input"
      disabled={languages.isLoading}
      getOptionLabel={(value: LocalesEnum) =>
        intl.formatMessage(languageTranslations[value])
      }
      name={name}
      options={languages.data ?? defaultLanguages}
      isFilterContext={isFilterContext}
      label={intl.formatMessage(messages.languageLabel)}
    />
  );
}
