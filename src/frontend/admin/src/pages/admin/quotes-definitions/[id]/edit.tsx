import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { useQuoteDefinition } from "@/hooks/useQuoteDefinitions/useQuoteDefinitions";
import { quoteDefinitionsBreadcrumbsTranslation } from "@/translations/pages/quotes-definitions/breadcrumbsTranslations";
import { QuoteDefinitionForm } from "@/components/templates/quote-definition/form/QuoteDefinitionForm";
import { UseAsTemplateButton } from "@/components/templates/form/buttons/UseAsTemplateButton";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.quotes.edit.pageTitle",
    defaultMessage: "Edit quote definition: {name}",
    description: "Label for the edit quote definition page title",
  },
});

export default function EditQuoteDefinitionPage() {
  const intl = useIntl();
  const { query } = useRouter();
  const { id } = query;
  const quoteDefinitionQuery = useQuoteDefinition(id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle, {
        name: quoteDefinitionQuery.item?.title ?? "",
      })}
      actions={
        <UseAsTemplateButton
          href={`${PATH_ADMIN.quote_definition.create}?from=${quoteDefinitionQuery.item?.id}`}
          show={Boolean(quoteDefinitionQuery?.item)}
        />
      }
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
            quoteDefinitionsBreadcrumbsTranslation.editBreadcrumb,
          ),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        <LoadingContent loading={quoteDefinitionQuery.states.isLoading}>
          {quoteDefinitionQuery.item && (
            <QuoteDefinitionForm quoteDefinition={quoteDefinitionQuery.item} />
          )}
        </LoadingContent>
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
