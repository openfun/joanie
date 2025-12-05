import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { useQuoteDefinition } from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";
import { QuoteDefinition } from "@/services/api/models/QuoteDefinition";
import { QuoteDefinitionForm } from "@/components/templates/quote-definition/form/QuoteDefinitionForm";

const messages = defineMessages({
  add: {
    id: "components.templates.quoteDefinitions.modals.CreateOrEditQuoteDefinitionModal.add",
    defaultMessage: "Add a quote definition",
    description: "Title for add definition modal",
  },
  edit: {
    id: "components.templates.quoteDefinitions.modals.CreateOrEditQuoteDefinitionModal.edit",
    defaultMessage: 'Edit the "{name}" quote template ',
    description: "Title for add quote definition modal",
  },
});

type Props = {
  modalUtils: ModalUtils;
  quoteDefinitionId?: string;
  afterSubmit: (definition: QuoteDefinition) => void;
};
export function CreateOrEditQuoteDefinitionModal(props: Props) {
  const intl = useIntl();
  const quoteDefinitionQuery = useQuoteDefinition(
    props.quoteDefinitionId ?? undefined,
  );
  return (
    <FullScreenModal
      disablePadding={true}
      title={intl.formatMessage(messages.add)}
      {...props.modalUtils}
    >
      <SimpleCard>
        <QuoteDefinitionForm
          quoteDefinition={
            props.quoteDefinitionId ? quoteDefinitionQuery.item : undefined
          }
          afterSubmit={props.afterSubmit}
        />
      </SimpleCard>
    </FullScreenModal>
  );
}
