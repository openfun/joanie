import { defineMessages, useIntl } from "react-intl";
import { Button } from "@mui/material";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { CoursesRunsList } from "@/components/templates/courses-runs/list/CoursesRunsList";
import { coursesRunsPagesTranslation } from "@/translations/pages/courses-runs/breadcrumbsTranslations";
import { PATH_ADMIN } from "@/utils/routes/path";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.coursesRuns.list.pageTitle",
    defaultMessage: "Course sessions",
    description: "Label for the courses runs list page title",
  },
});

export default function CoursesRunsListPage() {
  const { push } = useRouter();
  const intl = useIntl();
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.listBreadcrumb),
        },
      ]}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.courses_run.create)}
          size="small"
          variant="contained"
        >
          {intl.formatMessage(commonTranslations.add)}
        </Button>
      }
    >
      <CoursesRunsList />
    </DashboardLayoutPage>
  );
}
