import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";
import { coursesRunsPagesTranslation } from "@/translations/pages/courses-runs/breadcrumbsTranslations";
import { PATH_ADMIN } from "@/utils/routes/path";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.coursesRuns.create.pageTitle",
    defaultMessage: "Add a course run",
    description: "Label for the courses runs list page title",
  },
});

export default function CoursesRunsCreatePage() {
  const intl = useIntl();
  const router = useRouter();

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.courses_run.list,
        },
        {
          name: intl.formatMessage(
            coursesRunsPagesTranslation.createBreadcrumb
          ),
          isActive: true,
        },
      ]}
    >
      <SimpleCard>
        <CourseRunForm
          afterSubmit={(payload) => {
            router.push(PATH_ADMIN.courses_run.edit(payload.id));
          }}
        />
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
