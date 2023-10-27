import { useRouter } from "next/router";
import { defineMessages, useIntl } from "react-intl";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { coursesRunsPagesTranslation } from "@/translations/pages/courses-runs/breadcrumbsTranslations";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";
import { useCourseRun } from "@/hooks/useCourseRun/useCourseRun";
import { UseAsTemplateButton } from "@/components/templates/form/buttons/UseAsTemplateButton";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.coursesRuns.edit.pageTitle",
    defaultMessage: "Edit course run: {courseRunName}",
    description: "Label for the edit course run page title",
  },
});

export default function EditCourseRunPage() {
  const intl = useIntl();
  const { query } = useRouter();
  const courseRun = useCourseRun(query.id as string);
  return (
    <DashboardLayoutPage
      actions={
        <UseAsTemplateButton
          href={`${PATH_ADMIN.courses_run.create}?from=${courseRun.item?.id}`}
          show={Boolean(courseRun.item)}
        />
      }
      isLoading={courseRun.states.isLoading}
      title={intl.formatMessage(messages.pageTitle, {
        courseRunName: courseRun.item?.title,
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.courses_run.list,
        },
        {
          name: intl.formatMessage(coursesRunsPagesTranslation.editBreadcrumb),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        {courseRun.item && <CourseRunForm courseRun={courseRun.item} />}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
