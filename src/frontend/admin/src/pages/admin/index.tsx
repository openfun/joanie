import { defineMessages, useIntl } from "react-intl";
import Grid2 from "@mui/material/Grid2";
import * as React from "react";
import { useMemo } from "react";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { LinkCard } from "@/components/presentational/card/LinkCard";
import { getHomeCardData } from "@/utils/pages/home/homeCardsData";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.home.pageTitle",
    defaultMessage: "Joanie administration",
    description: "Label for the home page title",
  },
  rootBreadcrumb: {
    id: "pages.admin.home.rootBreadcrumb",
    defaultMessage: "Home page",
    description: "Label for the root breadcrumn ",
  },
});

export default function Index() {
  const intl = useIntl();

  const cards = useMemo(() => getHomeCardData(intl), [intl]);

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(messages.rootBreadcrumb),
        },
      ]}
      stretch={false}
    >
      <Grid2 container spacing={2}>
        {cards.map((item) => (
          <Grid2 size={{ xs: 12, md: 6, lg: 6, xl: 4 }} key={item.badgeLabel}>
            <LinkCard
              icon={item.icon}
              badgeLabel={item.badgeLabel}
              href={item.href}
              title={item.title}
              description={item.description}
            />
          </Grid2>
        ))}
      </Grid2>
    </DashboardLayoutPage>
  );
}
