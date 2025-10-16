import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { batchOrdersBreadcrumbsTranslation } from "@/translations/pages/batch-orders/breadcrumbsTranslations";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";
import { useBatchOrder } from "@/hooks/useBatchOrders/useBatchOrders";
import { BatchOrderView } from "@/components/templates/batch-orders/view/BatchOrderView";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.batchOrders.view.pageTitle",
    defaultMessage: "Batch Orders",
    description: "Label for the batch orders view page title",
  },
});

export default function BatchOrderViewPage() {
  const intl = useIntl();
  const { query } = useRouter();
  const { id } = query;
  const batchOrderQuery = useBatchOrder(id as string);

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
        {
          name: "View",
        },
      ]}
      stretch={false}
    >
      <LoadingContent loading={batchOrderQuery.item === undefined}>
        {batchOrderQuery.item && (
          <BatchOrderView batchOrder={batchOrderQuery.item} />
        )}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
