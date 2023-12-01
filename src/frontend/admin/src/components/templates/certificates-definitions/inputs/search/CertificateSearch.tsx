import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Maybe, Nullable } from "@/types/utils";
import { useCertificateDefinitions } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { useModal } from "@/components/presentational/modal/useModal";
import { CreateOrEditCertificationModal } from "@/components/templates/certificates-definitions/modals/CreateOrEditCertificationModal";

export function CertificateSearch(
  props: RHFAutocompleteSearchProps<CertificateDefinition>,
) {
  const { setValue, getValues } = useFormContext();
  const definition: Nullable<CertificateDefinition> = getValues(props.name);
  const [query, setQuery] = useState("");
  const certificates = useCertificateDefinitions({ query });
  const addModal = useModal();
  const editModal = useModal();

  const afterSubmit = (def: CertificateDefinition) => {
    editModal.handleClose();
    addModal.handleClose();
    setValue(props.name, def, { shouldTouch: true, shouldValidate: true });
  };

  return (
    <>
      <RHFSearch
        {...props}
        filterOptions={(x) => x}
        items={certificates.items}
        loading={certificates.states.fetching}
        onAddClick={() => addModal.handleOpen()}
        onEditClick={() => editModal.handleOpen()}
        onFilter={(term) => setQuery(term)}
        getOptionLabel={(option: Maybe<CertificateDefinition>) =>
          option?.title ?? ""
        }
        isOptionEqualToValue={(option, value) => option.id === value.id}
      />

      <CreateOrEditCertificationModal
        afterSubmit={afterSubmit}
        definitionId={
          definition && props.enableEdit ? definition.id : undefined
        }
        createModalUtils={addModal}
        editModalUtils={editModal}
      />
    </>
  );
}
