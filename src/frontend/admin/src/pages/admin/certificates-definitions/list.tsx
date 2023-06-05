import Button from "@mui/material/Button";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { certificateDefinitionsBreadcrumbsTranslation } from "@/translations/pages/certificates-definitions/breadcrumbsTranslations";
import { CertificatesDefinitionsList } from "@/components/templates/certificates-definitions/list/CertificatesDefintionsList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.certificateDefinitions.list.pageTitle",
    defaultMessage: "Certificates definitions",
    description: "Label for the certificates definitions list page title",
  },
});

export default function CertificatesDefinitionsListPage() {
  const { push } = useRouter();
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.rootBreadcrumb
          ),
        },
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.listBreadcrumb
          ),
        },
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.certificates.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <CertificatesDefinitionsList />
    </DashboardLayoutPage>
  );
}
