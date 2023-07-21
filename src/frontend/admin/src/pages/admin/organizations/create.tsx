import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { PATH_ADMIN } from "@/utils/routes/path";
import { orgBreadcrumbsTranslation } from "@/translations/pages/organizations/breadcrumbsTranslations";

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
          name: intl.formatMessage(orgBreadcrumbsTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(orgBreadcrumbsTranslation.listBreadcrumb),
          href: PATH_ADMIN.organizations.list,
        },
        {
          name: intl.formatMessage(orgBreadcrumbsTranslation.createBreadcrumb),
          isActive: true,
        },
      ]}
    >
      <OrganizationForm
        afterSubmit={(organization) =>
          router.push(PATH_ADMIN.organizations.edit(organization.id))
        }
      />
    </DashboardLayoutPage>
  );
}
