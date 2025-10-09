import Button from "@mui/material/Button";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { quoteDefinitionsBreadcrumbsTranslation } from "@/translations/pages/quotes-definitions/breadcrumbsTranslations";
import { QuoteDefinitionsList } from "@/components/templates/quote-definition/list/QuoteDefinitionsList";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.quoteDefinitions.list.pageTitle",
    defaultMessage: "Quote definitions",
    description: "Label for the quote definitions list page title",
  },
});

export default function QuoteDefinitionsListPage() {
  const { push } = useRouter();
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(
            quoteDefinitionsBreadcrumbsTranslation.rootBreadcrumb,
          ),
        },
        {
          name: intl.formatMessage(
            quoteDefinitionsBreadcrumbsTranslation.listBreadcrumb,
          ),
        },
      ]}
      stretch={false}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.quote_definition.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <QuoteDefinitionsList changeUrlOnPageChange={true} />
    </DashboardLayoutPage>
  );
}
