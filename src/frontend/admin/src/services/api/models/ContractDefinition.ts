import { Optional } from "@/types/utils";

export type ContractDefinition = {
  id: string;
  title: string;
  description?: string;
  body?: string;
  language: string;
  name: string;
};

export type DTOContractDefinition = Optional<ContractDefinition, "id">;
