import { Optional } from "@/types/utils";

export type ContractDefinition = {
  id: string;
  title: string;
  description: string;
  body: string;
  appendix: string;
  language: string;
  name: ContractDefinitionTemplate;
};

export type ContractDefinitionFormValues = Omit<
  ContractDefinition,
  "id" | "name"
> & {
  name: ContractDefinitionTemplate | "";
};

export type DTOContractDefinition = Optional<ContractDefinition, "id">;

export enum ContractDefinitionTemplate {
  DEFAULT = "contract_definition_default",
  UNICAMP = "contract_definition_unicamp",
  PRO_DEFAULT = "professional_training_agreement_default",
  PRO_UNICAMP = "professional_training_agreement_unicamp",
}
