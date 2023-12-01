import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { useCertificateDefinition } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";

const messages = defineMessages({
  add: {
    id: "components.templates.certificatesDefinitions.modals.CreateOrEditCertificationModal.add",
    defaultMessage: "Add a certificate definition",
    description: "Title for add definition modal",
  },

  edit: {
    id: "components.templates.certificatesDefinitions.modals.CreateOrEditCertificationModal.edit",
    defaultMessage: 'Edit the "{name}" definition ',
    description: "Title for add definition modal",
  },
});

type Props = {
  createModalUtils: ModalUtils;
  editModalUtils?: ModalUtils;
  definitionId?: string;
  afterSubmit: (definition: CertificateDefinition) => void;
};
export function CreateOrEditCertificationModal(props: Props) {
  const intl = useIntl();
  const definitionQuery = useCertificateDefinition(
    props.definitionId ?? undefined,
  );
  return (
    <>
      <FullScreenModal
        disablePadding={true}
        title={intl.formatMessage(messages.add)}
        {...props.createModalUtils}
      >
        <SimpleCard>
          <CertificateDefinitionForm afterSubmit={props.afterSubmit} />
        </SimpleCard>
      </FullScreenModal>

      {props.editModalUtils && props.definitionId && definitionQuery.item && (
        <FullScreenModal
          disablePadding={true}
          title={intl.formatMessage(messages.edit, {
            name: definitionQuery.item.title,
          })}
          {...props.editModalUtils}
        >
          <SimpleCard>
            <CertificateDefinitionForm
              definition={definitionQuery.item}
              afterSubmit={props.afterSubmit}
            />
          </SimpleCard>
        </FullScreenModal>
      )}
    </>
  );
}
