import { defineMessages, useIntl } from "react-intl";
import * as React from "react";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { vouchersPagesTranslation } from "@/translations/pages/vouchers/breadcrumbsTranslations";
import { VoucherForm } from "@/components/templates/vouchers/form/VoucherForm";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useVoucher } from "@/hooks/useVouchers/useVouchers";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.vouchers.create.pageTitle",
    defaultMessage: "Add voucher",
    description: "Label for the create voucher page title",
  },
});

export default function CreateVoucherPage() {
  const intl = useIntl();
  const router = useRouter();
  const fromId = useFromIdSearchParams();
  const fromVoucher = useVoucher(fromId, {}, { enabled: fromId !== undefined });
  const canShowForm = !fromId || !!fromVoucher.item;

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
        {
          name: intl.formatMessage(vouchersPagesTranslation.createBreadcrumb),
          isActive: true,
        },
      ]}
    >
      {canShowForm && (
        <VoucherForm
          fromVoucher={fromVoucher.item}
          afterSubmit={(payload) => {
            router.push(PATH_ADMIN.vouchers.edit(payload.id));
          }}
        />
      )}
    </DashboardLayoutPage>
  );
}
