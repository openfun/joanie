import Button from "@mui/material/Button";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { productsPagesTranslation } from "@/translations/pages/products/breadcrumbsTranslations";
import { ProductList } from "@/components/templates/products/list/ProductsList";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.products.list.pageTitle",
    defaultMessage: "Products",
    description: "Label for the product list page title",
  },
});

export default function ProductListPage() {
  const { push } = useRouter();
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(productsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(productsPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.organizations.list,
        },
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.products.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <ProductList />
    </DashboardLayoutPage>
  );
}
