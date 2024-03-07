import * as React from "react";
import { useState } from "react";
import { useFormContext } from "react-hook-form";
import { useOrganizations } from "@/hooks/useOrganizations/useOrganizations";
import {
  RHFAutocompleteSearchProps,
  RHFSearch,
} from "@/components/presentational/hook-form/RHFSearch";
import { Organization } from "@/services/api/models/Organization";
import { Maybe } from "@/types/utils";
import { useModal } from "@/components/presentational/modal/useModal";
import { CreateOrEditOrganizationModal } from "@/components/templates/organizations/modals/CreateOrEditOrganizationModal";
import { OrganizationRepository } from "@/services/repositories/organization/OrganizationRepository";

export function OrganizationSearch({
  ...props
}: RHFAutocompleteSearchProps<Organization>) {
  const { setValue, getValues } = useFormContext();
  const [query, setQuery] = useState("");
  const organizations = useOrganizations({ query });
  const modal = useModal();

  const afterSubmit = (org: Organization) => {
    const values: Organization[] = getValues(props.name);
    values.push(org);
    setValue(props.name, values, { shouldTouch: true, shouldValidate: true });
    modal.handleClose();
  };

  return (
    <>
      <RHFSearch
        {...props}
        findFilterValue={async (values) => {
          const request = await OrganizationRepository.getAll({ ids: values });
          return request.results;
        }}
        items={organizations.items}
        onAddClick={modal.handleOpen}
        loading={organizations.states.fetching}
        enableEdit={props.multiple ? false : props.enableEdit}
        onFilter={setQuery}
        getOptionLabel={(option: Maybe<Organization>) => option?.title ?? ""}
        isOptionEqualToValue={(option, value) => option.title === value.title}
      />
      <CreateOrEditOrganizationModal
        modalUtils={modal}
        afterSubmit={afterSubmit}
      />
    </>
  );
}
