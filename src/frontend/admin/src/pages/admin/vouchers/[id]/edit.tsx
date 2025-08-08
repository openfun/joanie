import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { useVoucher } from "@/hooks/useVouchers/useVouchers";
import { VoucherForm } from "@/components/templates/vouchers/form/VoucherForm";
import { vouchersPagesTranslation } from "@/translations/pages/vouchers/breadcrumbsTranslations";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.vouchers.edit.pageTitle",
    defaultMessage: "Edit voucher: {voucherName}",
    description: "Label for the edit voucher page title",
  },
});

export default function EditVoucherPage() {
  const { query } = useRouter();
  const { id } = query;
  const voucher = useVoucher(id as string);

  const intl = useIntl();
  return (
    <DashboardLayoutPage
      isLoading={!voucher.states.isFetched}
      title={intl.formatMessage(messages.pageTitle, {
        voucherName: voucher.item?.code,
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(vouchersPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(vouchersPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.vouchers.list,
        },
        {
          name: intl.formatMessage(vouchersPagesTranslation.editBreadcrumb),
          isActive: true,
        },
      ]}
    >
      <LoadingContent loading={voucher.states.isLoading}>
        {voucher.item && <VoucherForm voucher={voucher.item} />}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
