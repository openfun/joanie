import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { orgBreadcrumbsTranslation } from "@/translations/pages/organizations/breadcrumbsTranslations";
import { PATH_ADMIN } from "@/utils/routes/path";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { useOrganization } from "@/hooks/useOrganizations/useOrganizations";
import { UseAsTemplateButton } from "@/components/templates/form/buttons/UseAsTemplateButton";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.organizations.edit.pageTitle",
    defaultMessage: "Edit organization: {organizationName}",
    description: "Label for the edit organization page title",
  },
});

export default function EditOrganizationPage() {
  const { query } = useRouter();
  const { id } = query;
  const org = useOrganization(id as string);

  const intl = useIntl();
  return (
    <DashboardLayoutPage
      actions={
        <UseAsTemplateButton
          href={`${PATH_ADMIN.organizations.create}?from=${org.item?.id}`}
          show={Boolean(org?.item)}
        />
      }
      isLoading={!org.states.isFetched}
      title={intl.formatMessage(messages.pageTitle, {
        organizationName: org.item?.title,
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(orgBreadcrumbsTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(orgBreadcrumbsTranslation.listBreadcrumb),
          href: PATH_ADMIN.organizations.list,
        },
        {
          name: intl.formatMessage(orgBreadcrumbsTranslation.editBreadcrumb),
          isActive: true,
        },
      ]}
    >
      <LoadingContent loading={org.states.isLoading}>
        {org.item && <OrganizationForm organization={org.item} />}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
