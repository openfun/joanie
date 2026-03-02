import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { ordersBreadcrumbsTranslation } from "@/translations/pages/orders/breadcrumbsTranslations";
import { OrderCreateForm } from "@/components/templates/orders/form/OrderCreateForm";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.orders.create.pageTitle",
    defaultMessage: "Add order",
    description: "Label for the create order page title",
  },
});

export default function CreateOrderPage() {
  const intl = useIntl();
  const router = useRouter();

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
          name: intl.formatMessage(
            ordersBreadcrumbsTranslation.createBreadcrumb,
          ),
          isActive: true,
        },
      ]}
    >
      <OrderCreateForm
        afterSubmit={(order) => router.push(PATH_ADMIN.orders.view(order.id!))}
      />
    </DashboardLayoutPage>
  );
}
