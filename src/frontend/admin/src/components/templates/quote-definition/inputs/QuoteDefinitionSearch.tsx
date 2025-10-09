import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe, Nullable } from "@/types/utils";
import { useModal } from "@/components/presentational/modal/useModal";
import { useQuoteDefinitions } from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";
import { QuoteDefinition } from "@/services/api/models/QuoteDefinition";
import { CreateOrEditQuoteDefinitionModal } from "@/components/templates/quote-definition/modals/CreateOrEditQuoteDefinitionModal";

export function QuoteDefinitionSearch(
  props: RHFAutocompleteSearchProps<QuoteDefinition>,
) {
  const { setValue, getValues } = useFormContext();
  const quote: Nullable<QuoteDefinition> = getValues(props.name);
  const [query, setQuery] = useState("");
  const quoteDefinitionsQuery = useQuoteDefinitions({ query });
  const [isCreateMode, setIsCreateMode] = useState(false);
  const modal = useModal();

  const onAddClick = (): void => {
    setIsCreateMode(true);
    modal.handleOpen();
  };

  const afterSubmit = (def: QuoteDefinition) => {
    modal.handleClose();
    setIsCreateMode(false);
    setValue(props.name, def, { shouldTouch: true, shouldValidate: true });
  };

  return (
    <>
      <RHFSearch
        {...props}
        sx={{ marginBottom: 2 }}
        filterOptions={(x) => x}
        items={quoteDefinitionsQuery.items}
        loading={quoteDefinitionsQuery.states.fetching}
        onAddClick={onAddClick}
        onEditClick={modal.handleOpen}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<QuoteDefinition>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.id === value.id}
      />

      <CreateOrEditQuoteDefinitionModal
        afterSubmit={afterSubmit}
        quoteDefinitionId={
          !isCreateMode && quote && props.enableEdit ? quote.id : undefined
        }
        modalUtils={modal}
      />
    </>
  );
}
