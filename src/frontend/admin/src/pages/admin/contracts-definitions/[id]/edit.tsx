import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useContractDefinition } from "@/hooks/useContractDefinitions/useContractDefinitions";
import { contractDefinitionsBreadcrumbsTranslation } from "@/translations/pages/contracts-definitions/breadcrumbsTranslations";
import { ContractDefinitionForm } from "@/components/templates/contract-definition/form/ContractDefinitionForm";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.certificates.edit.pageTitle",
    defaultMessage: "Edit certificate: {name}",
    description: "Label for the edit certificate page title",
  },
});

export default function EditCertificatePage() {
  const intl = useIntl();
  const { query } = useRouter();
  const { id } = query;
  const contractDefinitionQuery = useContractDefinition(id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle, {
        name: contractDefinitionQuery.item?.title ?? "",
      })}
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
            contractDefinitionsBreadcrumbsTranslation.editBreadcrumb,
          ),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        {contractDefinitionQuery.item && (
          <ContractDefinitionForm
            contractDefinition={contractDefinitionQuery.item}
          />
        )}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
