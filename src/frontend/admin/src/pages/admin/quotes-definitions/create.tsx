import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { PATH_ADMIN } from "@/utils/routes/path";
import { quoteDefinitionsBreadcrumbsTranslation } from "@/translations/pages/quotes-definitions/breadcrumbsTranslations";
import { QuoteDefinitionForm } from "@/components/templates/quote-definition/form/QuoteDefinitionForm";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useQuoteDefinition } from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.quoteDefinition.create.pageTitle",
    defaultMessage: "Add quote definition",
    description: "Label for the create quote organization page title",
  },
});

export default function CreateQuoteDefinitionPage() {
  const intl = useIntl();
  const router = useRouter();
  const fromId = useFromIdSearchParams();
  const fromQuoteDefinition = useQuoteDefinition(
    fromId,
    {},
    { enabled: fromId !== undefined },
  );
  const canShowForm = !fromId || !!fromQuoteDefinition.item;

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
          href: PATH_ADMIN.quote_definition.list,
        },
        {
          name: intl.formatMessage(
            quoteDefinitionsBreadcrumbsTranslation.createBreadcrumb,
          ),
          isActive: true,
        },
      ]}
    >
      <SimpleCard>
        {canShowForm && (
          <QuoteDefinitionForm
            fromQuoteDefinition={fromQuoteDefinition.item}
            afterSubmit={(newQuote) =>
              router.push(PATH_ADMIN.quote_definition.edit(newQuote.id))
            }
          />
        )}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
