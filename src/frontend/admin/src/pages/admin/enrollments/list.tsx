import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { enrollmentsBreadcrumbsTranslation } from "@/translations/pages/enrollments/breadcrumbsTranslations";
import { EnrollmentsList } from "@/components/templates/enrollments/list/EnrollmentsList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.enrollments.list.pageTitle",
    defaultMessage: "Enrollments",
    description: "Label for the enrollment list page title",
  },
});

export default function EnrollmentListPage() {
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            enrollmentsBreadcrumbsTranslation.rootBreadcrumb,
          ),
        },
        {
          name: intl.formatMessage(
            enrollmentsBreadcrumbsTranslation.listBreadcrumb,
          ),
          href: PATH_ADMIN.enrollments.list,
        },
      ]}
      stretch={false}
    >
      <EnrollmentsList changeUrlOnPageChange={true} />
    </DashboardLayoutPage>
  );
}
