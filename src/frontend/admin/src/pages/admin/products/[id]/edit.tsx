import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useProduct } from "@/hooks/useProducts/useProducts";
import { ProductForm } from "@/components/templates/products/form/ProductForm";
import { productsPagesTranslation } from "@/translations/pages/products/breadcrumbsTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.products.edit.pageTitle",
    defaultMessage: "Edit product: {productName}",
    description: "Label for the edit product page title",
  },
});

export default function EditProductPage() {
  const { query } = useRouter();
  const { id } = query;
  const product = useProduct(id as string);

  const intl = useIntl();
  return (
    <DashboardLayoutPage
      isLoading={!product.states.isFetched}
      title={intl.formatMessage(messages.pageTitle, {
        productName: product.item?.title,
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(productsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(productsPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.products.list,
        },
        {
          name: intl.formatMessage(productsPagesTranslation.editBreadcrumb),
          isActive: true,
        },
      ]}
    >
      <SimpleCard>
        {product.item && <ProductForm product={product.item} />}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
