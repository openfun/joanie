import Button from "@mui/material/Button";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { contractDefinitionsBreadcrumbsTranslation } from "@/translations/pages/contracts-definitions/breadcrumbsTranslations";
import { ContractsDefinitionsList } from "@/components/templates/contract-definition/list/ContractsDefinitionsList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.contractDefinitions.list.pageTitle",
    defaultMessage: "Contracts definitions",
    description: "Label for the contracts definitions list page title",
  },
});

export default function ContractsDefinitionsListPage() {
  const { push } = useRouter();
  const intl = useIntl();
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
        },
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.contract_definition.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <ContractsDefinitionsList />
    </DashboardLayoutPage>
  );
}
