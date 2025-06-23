import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  CustomModal,
  CustomModalProps,
} from "@/components/presentational/modal/Modal";
import { Offering, DTOOffering } from "@/services/api/models/Offerings";
import {
  OfferingForm,
  OfferingFormValues,
} from "@/components/templates/courses/form/offering/OfferingForm";

const messages = defineMessages({
  addModalTitle: {
    id: "components.templates.courses.form.productRelationModal.addModalTitle",
    defaultMessage: "Add offering",
    description: "Title for productRelationModal in add mode ",
  },
  editModalTitle: {
    id: "components.templates.courses.form.productRelationModal.editModalTitle",
    defaultMessage: "Edit offering",
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
  courseId?: string;
  productId?: string;
  offering?: Offering;
  onSubmitForm?: (payload: DTOOffering, formValues: OfferingFormValues) => void;
}

export function OfferingFormModal(props: Props) {
  const intl = useIntl();
  const mode: Mode = useMemo(() => {
    return props.offering !== undefined ? Mode.EDIT : Mode.ADD;
  }, [props.offering]);

  return (
    <CustomModal
      title={intl.formatMessage(
        mode === Mode.EDIT ? messages.editModalTitle : messages.addModalTitle,
      )}
      open={props.open}
      handleClose={props.handleClose}
    >
      <OfferingForm
        productId={props.productId}
        courseId={props.courseId}
        defaultProduct={props.offering?.product}
        defaultCourse={props.offering?.course}
        onSubmit={props.onSubmitForm}
      />
    </CustomModal>
  );
}
