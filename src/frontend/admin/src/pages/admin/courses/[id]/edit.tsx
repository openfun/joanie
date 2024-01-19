import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { PATH_ADMIN } from "@/utils/routes/path";
import { coursesPagesTranslation } from "@/translations/pages/courses/breadcrumbsTranslations";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { useCourse } from "@/hooks/useCourses/useCourses";
import { UseAsTemplateButton } from "@/components/templates/form/buttons/UseAsTemplateButton";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.courses.edit.pageTitle",
    defaultMessage: "Edit course: {courseName}",
    description: "Label for the edit course run page title",
  },
});

export default function EditCoursePage() {
  const intl = useIntl();
  const { query } = useRouter();
  const course = useCourse(query.id as string);
  return (
    <DashboardLayoutPage
      actions={
        <UseAsTemplateButton
          href={`${PATH_ADMIN.courses.create}?from=${course.item?.id}`}
          show={Boolean(course?.item)}
        />
      }
      title={intl.formatMessage(messages.pageTitle, {
        courseName: course?.item?.title,
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
      <LoadingContent loading={course.states.isLoading}>
        {course.item && <CourseForm course={course.item} />}
      </LoadingContent>
    </DashboardLayoutPage>
  );
}
