import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { coursesPagesTranslation } from "@/translations/pages/courses/breadcrumbsTranslations";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { useCourse } from "@/hooks/useCourses/useCourses";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.courses.edit.pageTitle",
    defaultMessage: "Edit course: {courseName}",
    description: "Label for the edit course run page title",
  },
});

export default function EditCourseRunPage() {
  const intl = useIntl();
  const { query } = useRouter();
  const courseRun = useCourse(query.id as string);
  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle, {
        courseName: courseRun?.item?.title,
      })}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.courses.list,
        },
        {
          name: intl.formatMessage(coursesPagesTranslation.editBreadcrumb),
          isActive: true,
        },
      ]}
      stretch={false}
    >
      <SimpleCard>
        {courseRun.item && <CourseForm course={courseRun.item} />}
      </SimpleCard>
    </DashboardLayoutPage>
  );
}
