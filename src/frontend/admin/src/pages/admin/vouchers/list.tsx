import Button from "@mui/material/Button";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { vouchersPagesTranslation } from "@/translations/pages/vouchers/breadcrumbsTranslations";
import { VouchersList } from "@/components/templates/vouchers/list/VouchersList";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.vouchers.list.pageTitle",
    defaultMessage: "Vouchers",
    description: "Label for the voucher list page title",
  },
});

export default function VoucherListPage() {
  const { push } = useRouter();
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(vouchersPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(vouchersPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.vouchers.list,
        },
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.vouchers.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <SimpleCard>
        <VouchersList changeUrlOnPageChange={true} />
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
