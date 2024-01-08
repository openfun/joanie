import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { useContractDefinition } from "@/hooks/useContractDefinitions/useContractDefinitions";
import { ContractDefinition } from "@/services/api/models/ContractDefinition";
import { ContractDefinitionForm } from "@/components/templates/contract-definition/form/ContractDefinitionForm";

const messages = defineMessages({
  add: {
    id: "components.templates.contractDefinitions.modals.CreateOrEditContractDefinitionModal.add",
    defaultMessage: "Add a contract definition",
    description: "Title for add definition modal",
  },

  edit: {
    id: "components.templates.contractDefinitions.modals.CreateOrEditContractDefinitionModal.edit",
    defaultMessage: 'Edit the "{name}" contract template ',
    description: "Title for add contract definition modal",
  },
});

type Props = {
  modalUtils: ModalUtils;
  contractDefinitionId?: string;
  afterSubmit: (definition: ContractDefinition) => void;
};
export function CreateOrEditContractDefinitionModal(props: Props) {
  const intl = useIntl();
  const contractDefinitionQuery = useContractDefinition(
    props.contractDefinitionId ?? undefined,
  );
  return (
    <FullScreenModal
      disablePadding={true}
      title={intl.formatMessage(messages.add)}
      {...props.modalUtils}
    >
      <SimpleCard>
        <ContractDefinitionForm
          contractDefinition={
            props.contractDefinitionId
              ? contractDefinitionQuery.item
              : undefined
          }
          afterSubmit={props.afterSubmit}
        />
      </SimpleCard>
    </FullScreenModal>
  );
}
