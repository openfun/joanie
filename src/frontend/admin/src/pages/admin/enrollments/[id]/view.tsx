import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { ordersBreadcrumbsTranslation } from "@/translations/pages/orders/breadcrumbsTranslations";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";
import { EnrollmentView } from "@/components/templates/enrollments/view/EnrollmentView";
import { useEnrollment } from "@/hooks/useEnrollments/useEnrollments";
import EnrollmentActionsButton from "@/components/templates/enrollments/buttons/EnrollmentActions";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.orders.list.pageTitle",
    defaultMessage: "Orders",
    description: "Label for the order list page title",
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
          <EnrollmentActionsButton order={enrollmentQuery.item} />
        )
      }
      breadcrumbs={[
        {
          name: intl.formatMessage(ordersBreadcrumbsTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(ordersBreadcrumbsTranslation.listBreadcrumb),
          href: PATH_ADMIN.orders.list,
        },
        {
          name: intl.formatMessage(ordersBreadcrumbsTranslation.viewBreadcrumb),
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
