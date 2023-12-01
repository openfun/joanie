import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { useOrganization } from "@/hooks/useOrganizations/useOrganizations";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { Organization } from "@/services/api/models/Organization";

const messages = defineMessages({
  add: {
    id: "components.templates.organizations.modals.CreateOrEditOrganizationModal.add",
    defaultMessage: "Add an organization",
    description: "Title for add organization modal",
  },

  edit: {
    id: "components.templates.organizations.modals.CreateOrEditOrganizationModal.edit",
    defaultMessage: 'Edit the "{name}" organization ',
    description: "Title for add organization modal",
  },
});

type Props = {
  modalUtils: ModalUtils;
  orgId?: string;
  afterSubmit: (definition: Organization) => void;
};
export function CreateOrEditOrganizationModal({ orgId, ...props }: Props) {
  const intl = useIntl();
  const organization = useOrganization(orgId ?? undefined);
  return (
    <FullScreenModal
      disablePadding={true}
      title={intl.formatMessage(messages.add)}
      {...props.modalUtils}
    >
      <OrganizationForm
        organization={orgId ? organization.item : undefined}
        afterSubmit={props.afterSubmit}
      />
    </FullScreenModal>
  );
}
