import * as React from "react";
import { useMemo } from "react";
import { useIntl } from "react-intl";
import { Course } from "@/services/api/models/Course";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { CourseFormTargetCourseRunsSection } from "@/components/templates/courses/form/sections/target-course-runs/CourseFormTargetCourseRunsSection";
import { CourseFormAccessesSection } from "@/components/templates/courses/form/sections/accesses/CourseFormAccessesSection";
import { CourseFormProductRelationsSection } from "@/components/templates/courses/form/sections/product-relation/CourseFormProductRelationsSection";
import { CourseGeneralForm } from "@/components/templates/courses/form/general/GeneralCourseForm";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import {
  TabsComponent,
  TabValue,
} from "@/components/presentational/tabs/TabsComponent";

interface Props {
  afterSubmit?: (course: Course) => void;
  course?: Course;
  shortcutMode?: boolean;
  fromCourse?: Course;
}

export function CourseForm({ course, shortcutMode = false, ...props }: Props) {
  const intl = useIntl();
  const coursesQuery = useCourses({}, { enabled: false });
  const defaultCourse = course ?? props.fromCourse;

  const tabs = useMemo(() => {
    let result: TabValue[] = [
      {
        label: intl.formatMessage(courseFormMessages.generalTabTitle),
        tabInfo: intl.formatMessage(courseFormMessages.generalSectionInfo),
        component: (
          <CourseGeneralForm
            course={defaultCourse}
            afterSubmit={props.afterSubmit}
          />
        ),
      },
    ];

    if (course) {
      result = [
        ...result,
        {
          label: intl.formatMessage(courseFormMessages.membersTabTitle),
          component: <CourseFormAccessesSection course={course} />,
          tabInfo: intl.formatMessage(courseFormMessages.membersSectionInfo),
        },
        {
          label: intl.formatMessage(courseFormMessages.courseRunsTabTitle),
          show: !!course,
          component: <CourseFormTargetCourseRunsSection course={course} />,
          tabInfo: intl.formatMessage(
            courseFormMessages.targetCourseRunAlertInfo,
          ),
        },
        {
          label: intl.formatMessage(courseFormMessages.productsTabTitle),
          show: !!course && !shortcutMode,
          tabInfo: intl.formatMessage(courseFormMessages.productsTabInfo),
          component: (
            <CourseFormProductRelationsSection
              invalidateCourse={() => coursesQuery.methods.invalidate()}
              course={course}
            />
          ),
        },
      ];
    }
    return result;
  }, [course, intl]);

  return <TabsComponent id="course-form-tabs" tabs={tabs} />;
}
