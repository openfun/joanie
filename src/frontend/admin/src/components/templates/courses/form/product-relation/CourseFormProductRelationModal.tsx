import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  CustomModal,
  CustomModalProps,
} from "@/components/presentational/modal/Modal";
import {
  CourseProductRelation,
  DTOCourseProductRelation,
} from "@/services/api/models/Relations";
import {
  CourseProductRelationForm,
  CourseProductRelationFormValues,
} from "@/components/templates/courses/form/product-relation/CourseProductRelationForm";

const messages = defineMessages({
  addModalTitle: {
    id: "components.templates.courses.form.productRelationModal.addModalTitle",
    defaultMessage: "Add the relation",
    description: "Title for productRelationModal in add mode ",
  },
  editModalTitle: {
    id: "components.templates.courses.form.productRelationModal.editModalTitle",
    defaultMessage: "Edit the relation",
    description: "Title for productRelationModal in edit mode ",
  },
  addButton: {
    id: "components.templates.courses.form.productRelationModal.addButton",
    defaultMessage: "Add",
    description: "Label for the validate button in add mode",
  },
  editButton: {
    id: "components.templates.courses.form.productRelationModal.editButton",
    defaultMessage: "Validate",
    description: "Label for the validate button in edit mode",
  },
});

enum Mode {
  EDIT = "edit",
  ADD = "add",
}

interface Props extends Omit<CustomModalProps, "title"> {
  courseId: string;
  courseRelationToProduct?: CourseRelationToProduct;
  onAdd: (
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ) => void;
  onEdit: (
    id: string,
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ) => void;
}

export function CourseFormProductRelationModal(props: Props) {
  const intl = useIntl();

  const mode: Mode = useMemo(() => {
    return props.courseRelationToProduct !== undefined ? Mode.EDIT : Mode.ADD;
  }, [props.courseRelationToProduct]);

  const validate = async (
    payload: DTOCourseRelationToProduct,
    formValues: CourseProductRelationFormValues,
  ): Promise<void> => {
    if (mode === Mode.ADD) {
      props.onAdd(payload, formValues);
    } else {
      props.onEdit(props.courseRelationToProduct!.id, payload, formValues);
    }
  };

  return (
    <CustomModal
      title={intl.formatMessage(
        mode === Mode.EDIT ? messages.editModalTitle : messages.addModalTitle,
      )}
      open={props.open}
      handleClose={props.handleClose}
    >
      <CourseProductRelationForm
        courseId={props.courseId}
        relation={props.courseRelationToProduct}
        onSubmit={validate}
      />
    </CustomModal>
  );
}
