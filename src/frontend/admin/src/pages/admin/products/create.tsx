import { defineMessages, useIntl } from "react-intl";
import * as React from "react";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { productsPagesTranslation } from "@/translations/pages/products/breadcrumbsTranslations";
import { ProductForm } from "@/components/templates/products/form/ProductForm";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useProduct } from "@/hooks/useProducts/useProducts";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.products.create.pageTitle",
    defaultMessage: "Add product",
    description: "Label for the create product page title",
  },
});

export default function CreateProductPage() {
  const intl = useIntl();
  const router = useRouter();
  const fromId = useFromIdSearchParams();
  const fromProduct = useProduct(fromId, {}, { enabled: fromId !== undefined });
  const canShowForm = !fromId || !!fromProduct.item;

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(productsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(productsPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.products.list,
        },
        {
          name: intl.formatMessage(productsPagesTranslation.createBreadcrumb),
          isActive: true,
        },
      ]}
    >
      {canShowForm && (
        <ProductForm
          fromProduct={fromProduct.item}
          afterSubmit={(payload) => {
            router.push(PATH_ADMIN.products.edit(payload.id));
          }}
        />
      )}
    </DashboardLayoutPage>
  );
}
