import { useIntl, defineMessages } from "react-intl";
import { useQuery } from "@tanstack/react-query";
import {
  RHFSelect,
  RHFSelectProps,
} from "@/components/presentational/hook-form/RHFSelect";
import { ContractDefinitionRepository } from "@/services/repositories/contract-definition/ContractDefinitionRepository";

const messages = defineMessages({
  inputLabel: {
    id: "components.templates.contractDefinitions.inputs.RHFContractDefinitionName.inputLabel",
    defaultMessage: "Template name",
    description: 'Label for the "name" input',
  },
});

type Props = RHFSelectProps & {
  name: string;
};

function RHFContractDefinitionName({ name }: Props) {
  const intl = useIntl();
  const templateNames = useQuery({
    queryKey: ["contractDefinitionTemplates"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => {
      return ContractDefinitionRepository.getAllTemplates();
    },
  });

  return (
    <RHFSelect
      data-testid="contract-definition-template-name-input"
      disabled={templateNames.isLoading}
      name={name}
      options={templateNames.data ?? []}
      label={intl.formatMessage(messages.inputLabel)}
    />
  );
}

export default RHFContractDefinitionName;
