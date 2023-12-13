import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { OrganizationForm } from "@/components/templates/organizations/form/OrganizationForm";
import { PATH_ADMIN } from "@/utils/routes/path";
import { orgBreadcrumbsTranslation } from "@/translations/pages/organizations/breadcrumbsTranslations";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useOrganization } from "@/hooks/useOrganizations/useOrganizations";

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
  const fromId = useFromIdSearchParams();
  const fromOrganization = useOrganization(
    fromId,
    {},
    { enabled: fromId !== undefined },
  );
  const canShowForm = !fromId || !!fromOrganization.item;

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
      {canShowForm && (
        <OrganizationForm
          fromOrganization={fromOrganization.item}
          afterSubmit={(organization) =>
            router.push(PATH_ADMIN.organizations.edit(organization.id))
          }
        />
      )}
    </DashboardLayoutPage>
  );
}
