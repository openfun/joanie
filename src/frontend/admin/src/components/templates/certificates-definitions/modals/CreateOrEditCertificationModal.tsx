import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";
import { CustomModal } from "@/components/presentational/modal/Modal";

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
  definition?: CertificateDefinition;
  afterSubmit: (definition: CertificateDefinition) => void;
};
export function CreateOrEditCertificationModal(props: Props) {
  const intl = useIntl();
  return (
    <>
      <CustomModal
        disablePadding={true}
        title={intl.formatMessage(messages.add)}
        {...props.createModalUtils}
      >
        <SimpleCard>
          <CertificateDefinitionForm afterSubmit={props.afterSubmit} />
        </SimpleCard>
      </CustomModal>

      {props.editModalUtils && props.definition && (
        <CustomModal
          disablePadding={true}
          title={intl.formatMessage(messages.edit, {
            name: props.definition.title,
          })}
          {...props.editModalUtils}
        >
          <SimpleCard>
            <CertificateDefinitionForm
              definition={props.definition}
              afterSubmit={props.afterSubmit}
            />
          </SimpleCard>
        </CustomModal>
      )}
    </>
  );
}
