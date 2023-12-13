import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { contractDefinitionsBreadcrumbsTranslation } from "@/translations/pages/contracts-definitions/breadcrumbsTranslations";
import { ContractDefinitionForm } from "@/components/templates/contract-definition/form/ContractDefinitionForm";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useContractDefinition } from "@/hooks/useContractDefinitions/useContractDefinitions";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.contractDefinition.create.pageTitle",
    defaultMessage: "Add contract definition",
    description: "Label for the create contract organisation page title",
  },
});

export default function CreateContractDefinitionPage() {
  const intl = useIntl();
  const router = useRouter();
  const fromId = useFromIdSearchParams();
  const fromContractDefinition = useContractDefinition(
    fromId,
    {},
    { enabled: fromId !== undefined },
  );
  const canShowForm = !fromId || !!fromContractDefinition.item;

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            contractDefinitionsBreadcrumbsTranslation.rootBreadcrumb,
          ),
        },
        {
          name: intl.formatMessage(
            contractDefinitionsBreadcrumbsTranslation.listBreadcrumb,
          ),
          href: PATH_ADMIN.contract_definition.list,
        },
        {
          name: intl.formatMessage(
            contractDefinitionsBreadcrumbsTranslation.createBreadcrumb,
          ),
          isActive: true,
        },
      ]}
    >
      <SimpleCard>
        {canShowForm && (
          <ContractDefinitionForm
            fromContractDefinition={fromContractDefinition.item}
            afterSubmit={(newCertificate) =>
              router.push(
                PATH_ADMIN.contract_definition.edit(newCertificate.id),
              )
            }
          />
        )}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
