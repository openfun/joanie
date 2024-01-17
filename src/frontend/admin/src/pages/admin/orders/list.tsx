import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { ordersBreadcrumbsTranslation } from "@/translations/pages/orders/breadcrumbsTranslations";
import { OrdersList } from "@/components/templates/orders/list/OrdersList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.orders.list.pageTitle",
    defaultMessage: "Orders",
    description: "Label for the order list page title",
  },
});

export default function OrderListPage() {
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(ordersBreadcrumbsTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(ordersBreadcrumbsTranslation.listBreadcrumb),
          href: PATH_ADMIN.organizations.list,
        },
      ]}
      stretch={false}
    >
      <OrdersList />
    </DashboardLayoutPage>
  );
}
