import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { certificationDefinitionsBreadcrumbsTranslation } from "@/translations/pages/certificates-definitions/breadcrumbsTranslations";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";
import { useCertificateDefinition } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";

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
  const certificate = useCertificateDefinition(id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle, {
        name: certificate.item?.title ?? "",
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            certificationDefinitionsBreadcrumbsTranslation.rootBreadcrumb
          ),
        },
        {
          name: intl.formatMessage(
            certificationDefinitionsBreadcrumbsTranslation.listBreadcrumb
          ),
          href: PATH_ADMIN.certificates.list,
        },
        {
          name: intl.formatMessage(
            certificationDefinitionsBreadcrumbsTranslation.editBreadcrumb
          ),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        {certificate.item && (
          <CertificateDefinitionForm certificate={certificate.item} />
        )}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
