import * as React from "react";
import { defineMessages, useIntl } from "react-intl";
import { ModalUtils } from "@/components/presentational/modal/useModal";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { Course } from "@/services/api/models/Course";
import { CourseForm } from "@/components/templates/courses/form/CourseForm";

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
  course?: Course;
  afterSubmit: (course: Course) => void;
};
export function CreateOrEditCourseModal(props: Props) {
  const intl = useIntl();
  return (
    <>
      <CustomModal
        disablePadding={true}
        title={intl.formatMessage(messages.add)}
        {...props.createModalUtils}
      >
        <CourseForm
          showProductRelationSection={false}
          afterSubmit={props.afterSubmit}
        />
      </CustomModal>

      {props.editModalUtils && props.course && (
        <CustomModal
          disablePadding={true}
          title={intl.formatMessage(messages.edit, {
            name: props.course.title,
          })}
          {...props.editModalUtils}
        >
          <CourseForm
            course={props.course}
            showProductRelationSection={false}
            afterSubmit={props.afterSubmit}
          />
        </CustomModal>
      )}
    </>
  );
}
