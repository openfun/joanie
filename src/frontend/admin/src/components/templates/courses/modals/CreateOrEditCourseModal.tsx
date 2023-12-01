import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { Course } from "@/services/api/models/Course";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { useCourse } from "@/hooks/useCourses/useCourses";

const messages = defineMessages({
  add: {
    id: "components.templates.certificatesDefinitions.modals.CreateOrEditCertificationModal.add",
    defaultMessage: "Add a course",
    description: "Title for add definition modal",
  },

  edit: {
    id: "components.templates.certificatesDefinitions.modals.CreateOrEditCertificationModal.edit",
    defaultMessage: 'Edit the "{name}" course ',
    description: "Title for add definition modal",
  },
});

type Props = {
  createModalUtils: ModalUtils;
  editModalUtils?: ModalUtils;
  courseId?: string;
  afterSubmit: (course: Course) => void;
};
export function CreateOrEditCourseModal(props: Props) {
  const intl = useIntl();
  const courseRun = useCourse(props.courseId ?? undefined);

  return (
    <>
      <FullScreenModal
        title={intl.formatMessage(messages.add)}
        {...props.createModalUtils}
      >
        <CourseForm shortcutMode={true} afterSubmit={props.afterSubmit} />
      </FullScreenModal>

      {props.editModalUtils && props.courseId && courseRun.item && (
        <FullScreenModal
          title={intl.formatMessage(messages.edit, {
            name: courseRun.item.title,
          })}
          {...props.editModalUtils}
        >
          <CourseForm
            course={courseRun.item}
            shortcutMode={true}
            afterSubmit={props.afterSubmit}
          />
        </FullScreenModal>
      )}
    </>
  );
}
