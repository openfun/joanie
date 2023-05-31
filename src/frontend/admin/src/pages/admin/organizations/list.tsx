import { Button } from "@mui/material";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { OrganizationsList } from "@/components/templates/organizations/list/OrganizationsList";
import { orgBreadcrumbsTranslation } from "@/translations/pages/organizations/breadcrumbsTranslations";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.organizations.list.pageTitle",
    defaultMessage: "Organizations",
    description: "Label for the organization list page title",
  },
});

export default function OrganizationListPage() {
  const { push } = useRouter();
  const intl = useIntl();
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
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.organizations.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <OrganizationsList />
    </DashboardLayoutPage>
  );
}
