import { Button } from "@mui/material";
import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CoursesList } from "@/components/templates/courses/list/CoursesList";
import { coursesPagesTranslation } from "@/translations/pages/courses/breadcrumbsTranslations";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.courses.list.pageTitle",
    defaultMessage: "Courses",
    description: "Label for the courses list page title",
  },
});

export default function CoursesListPage() {
  const { push } = useRouter();
  const intl = useIntl();

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesPagesTranslation.listBreadcrumb),
          isActive: true,
        },
      ]}
      actions={
        <Button
          onClick={() => push(PATH_ADMIN.courses.create)}
          size="small"
          variant="contained"
        >
          Add
        </Button>
      }
    >
      <CoursesList />
    </DashboardLayoutPage>
  );
}
