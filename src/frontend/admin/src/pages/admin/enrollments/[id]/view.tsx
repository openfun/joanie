import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";
import { EnrollmentView } from "@/components/templates/enrollments/view/EnrollmentView";
import { useEnrollment } from "@/hooks/useEnrollments/useEnrollments";
import EnrollmentActionsButton from "@/components/templates/enrollments/buttons/EnrollmentActions";
import { enrollmentsBreadcrumbsTranslation } from "@/translations/pages/enrollments/breadcrumbsTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.enrollments.view.pageTitle",
    defaultMessage: "Enrollment view",
    description: "Label for the enrollment page title",
  },
});

export default function OrderViewPage() {
  const intl = useIntl();

  const { query } = useRouter();
  const { id } = query;
  const enrollmentQuery = useEnrollment(id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      actions={
        enrollmentQuery.item && (
          <EnrollmentActionsButton enrollment={enrollmentQuery.item} />
        )
      }
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
          href: PATH_ADMIN.orders.list,
        },
        {
          name: intl.formatMessage(
            enrollmentsBreadcrumbsTranslation.viewBreadcrumb,
          ),
        },
      ]}
      stretch={false}
    >
      <LoadingContent loading={enrollmentQuery.item === undefined}>
        {enrollmentQuery.item && (
          <EnrollmentView enrollment={enrollmentQuery.item} />
        )}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
