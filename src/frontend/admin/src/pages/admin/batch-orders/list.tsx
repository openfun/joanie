import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { batchOrdersBreadcrumbsTranslation } from "@/translations/pages/batch-orders/breadcrumbsTranslations";
import { BatchOrdersList } from "@/components/templates/batch-orders/list/BatchOrdersList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.batchOrders.list.pageTitle",
    defaultMessage: "Batch orders",
    description: "Label for the batch orders list page title",
  },
});

export default function BatchOrderListPage() {
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            batchOrdersBreadcrumbsTranslation.rootBreadcrumb,
          ),
        },
        {
          name: intl.formatMessage(
            batchOrdersBreadcrumbsTranslation.listBreadcrumb,
          ),
          href: PATH_ADMIN.batch_orders.list,
        },
      ]}
      stretch={false}
    >
      <BatchOrdersList changeUrlOnPageChange={true} />
    </DashboardLayoutPage>
  );
}
