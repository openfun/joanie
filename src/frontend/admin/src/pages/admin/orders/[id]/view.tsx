import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { ordersBreadcrumbsTranslation } from "@/translations/pages/orders/breadcrumbsTranslations";
import { OrderView } from "@/components/templates/orders/view/OrderView";
import { useOrder } from "@/hooks/useOrders/useOrders";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

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
  const orderQuery = useOrder(id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
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
      <LoadingContent loading={orderQuery.item === undefined}>
        {orderQuery.item && <OrderView order={orderQuery.item} />}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
