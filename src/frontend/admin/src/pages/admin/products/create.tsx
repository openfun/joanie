import { defineMessages, useIntl } from "react-intl";
import * as React from "react";
import { useState } from "react";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { productsPagesTranslation } from "@/translations/pages/products/breadcrumbsTranslations";
import { ProductForm } from "@/components/templates/products/form/ProductForm";
import { Product } from "@/services/api/models/Product";
import { Maybe } from "@/types/utils";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.products.create.pageTitle",
    defaultMessage: "Add product",
    description: "Label for the create product page title",
  },
});

export default function CreateProductPage() {
  const intl = useIntl();
  const [createdProduct, setCreatedProduct] =
    useState<Maybe<Product>>(undefined);
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
      <ProductForm product={createdProduct} afterSubmit={setCreatedProduct} />
    </DashboardLayoutPage>
  );
}
