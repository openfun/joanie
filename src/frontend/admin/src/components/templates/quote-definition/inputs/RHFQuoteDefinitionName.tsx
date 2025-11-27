import { useIntl, defineMessages } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import {
  RHFSelect,
  RHFSelectProps,
} from "@/components/presentational/hook-form/RHFSelect";
import { QuoteDefinitionRepository } from "@/services/repositories/quote-definition/QuoteDefinitionRepository";

const messages = defineMessages({
  inputLabel: {
    id: "components.templates.quoteDefinitions.inputs.RHFQuoteDefinitionName.inputLabel",
    defaultMessage: "Template name",
    description: 'Label for the "name" input',
  },
});

type Props = RHFSelectProps & {
  name: string;
};

function RHFQuoteDefinitionName({ name }: Props) {
  const intl = useIntl();
  const templateNames = useQuery({
    queryKey: ["quoteDefinitionTemplates"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => {
      return QuoteDefinitionRepository.getAllTemplates();
    },
  });

  return (
    <RHFSelect
      data-testid="quote-definition-template-name-input"
      disabled={templateNames.isLoading}
      name={name}
      options={templateNames.data ?? []}
      label={intl.formatMessage(messages.inputLabel)}
    />
  );
}

export default RHFQuoteDefinitionName;
