import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { DashboardLayoutPage } from "@/layouts/dashboard/page/DashboardLayoutPage";
import { coursesPagesTranslation } from "@/translations/pages/courses/breadcrumbsTranslations";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { useFromIdSearchParams } from "@/hooks/useFromIdSearchParams";
import { useCourse } from "@/hooks/useCourses/useCourses";

const messages = defineMessages({
  pageTitle: {
    id: "pages.admin.courses.create.pageTitle",
    defaultMessage: "Add a course",
    description: "Label for the courses create page title",
  },
});

export default function CoursesCreatePage() {
  const intl = useIntl();
  const router = useRouter();
  const fromId = useFromIdSearchParams();
  const fromCourse = useCourse(fromId);
  const canShowForm = !fromId || !!fromCourse.item;

  return (
    <DashboardLayoutPage
      title={intl.formatMessage(messages.pageTitle)}
      breadcrumbs={[
        {
          name: intl.formatMessage(coursesPagesTranslation.rootBreadcrumb),
        },
        {
          name: intl.formatMessage(coursesPagesTranslation.listBreadcrumb),
          href: PATH_ADMIN.courses.list,
        },
        {
          name: intl.formatMessage(coursesPagesTranslation.createBreadcrumb),
          isActive: true,
        },
      ]}
    >
      {canShowForm && (
        <CourseForm
          fromCourse={fromCourse.item}
          afterSubmit={(course) =>
            router.push(PATH_ADMIN.courses.edit(course.id))
          }
        />
      )}
    </DashboardLayoutPage>
  );
}
