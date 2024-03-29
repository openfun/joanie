import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { certificateDefinitionsBreadcrumbsTranslation } from "@/translations/pages/certificates-definitions/breadcrumbsTranslations";
import { CertificateDefinitionForm } from "@/components/templates/certificates-definitions/form/CertificateDefinitionForm";
import { useCertificateDefinition } from "@/hooks/useCertificateDefinitions/useCertificateDefinitions";
import { UseAsTemplateButton } from "@/components/templates/form/buttons/UseAsTemplateButton";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

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
  const definition = useCertificateDefinition(id as string);
  return (
    <DashboardLayoutPage
      actions={
        <UseAsTemplateButton
          href={`${PATH_ADMIN.certificates.create}?from=${definition.item?.id}`}
          show={Boolean(definition?.item)}
        />
      }
      title={intl.formatMessage(messages.pageTitle, {
        name: definition.item?.title ?? "",
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.rootBreadcrumb,
          ),
        },
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.listBreadcrumb,
          ),
          href: PATH_ADMIN.certificates.list,
        },
        {
          name: intl.formatMessage(
            certificateDefinitionsBreadcrumbsTranslation.editBreadcrumb,
          ),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        <LoadingContent loading={definition.states.isLoading}>
          {definition.item && (
            <CertificateDefinitionForm definition={definition.item} />
          )}
        </LoadingContent>
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
