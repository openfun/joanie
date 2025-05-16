import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe, Nullable } from "@/types/utils";
import { useModal } from "@/components/presentational/modal/useModal";
import { useContractDefinitions } from "@/hooks/useContractDefinitions/useContractDefinitions";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { CreateOrEditContractDefinitionModal } from "@/components/templates/contract-definition/modals/CreateOrEditContractDefinitionModal";

export function ContractDefinitionSearch(
  props: RHFAutocompleteSearchProps<ContractDefinition>,
) {
  const { setValue, getValues } = useFormContext();
  const contract: Nullable<ContractDefinition> = getValues(props.name);
  const [query, setQuery] = useState("");
  const contractDefinitionsQuery = useContractDefinitions({ query });
  const [isCreateMode, setIsCreateMode] = useState(false);
  const modal = useModal();

  const onAddClick = (): void => {
    setIsCreateMode(true);
    modal.handleOpen();
  };

  const afterSubmit = (def: ContractDefinition) => {
    modal.handleClose();
    setIsCreateMode(false);
    setValue(props.name, def, { shouldTouch: true, shouldValidate: true });
  };

  return (
    <>
      <RHFSearch
        {...props}
        filterOptions={(x) => x}
        items={contractDefinitionsQuery.items}
        loading={contractDefinitionsQuery.states.fetching}
        onAddClick={onAddClick}
        onEditClick={modal.handleOpen}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<ContractDefinition>) =>
          option?.title ?? ""
        }
        isOptionEqualToValue={(option, value) => option.id === value.id}
      />

      <CreateOrEditContractDefinitionModal
        afterSubmit={afterSubmit}
        contractDefinitionId={
          !isCreateMode && contract && props.enableEdit
            ? contract.id
            : undefined
        }
        modalUtils={modal}
      />
    </>
  );
}
