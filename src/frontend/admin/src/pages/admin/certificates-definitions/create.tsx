import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { certificateDefinitionsBreadcrumbsTranslation } from "@/translations/pages/certificates-definitions/breadcrumbsTranslations";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.organizations.create.pageTitle",
    defaultMessage: "Add organization",
    description: "Label for the create organization page title",
  },
});

export default function CreateOrganizationPage() {
  const intl = useIntl();
  const router = useRouter();
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
          href: PATH_ADMIN.certificates.list,
        },
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.createBreadcrumb
          ),
          isActive: true,
        },
      ]}
    >
      <SimpleCard>
        <CertificateDefinitionForm
          afterSubmit={(newCertificate) =>
            router.push(PATH_ADMIN.certificates.edit(newCertificate.id))
          }
        />
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
