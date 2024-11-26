import Chip from "@mui/material/Chip";
import { useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { defineMessages, useIntl } from "react-intl";
import TeacherForm from "./TeacherForm";
import RHFChipsField from "@/components/presentational/hook-form/RHFChipsField";
import {
  ModalUtils,
  useModal,
} from "@/components/presentational/modal/useModal";
import { useTeachers } from "@/hooks/useTeachers";
import { Product } from "@/services/api/models/Product";
import { Teacher } from "@/services/api/models/Teacher";
import { Nullable } from "@/types/utils";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  fieldLabel: {
    id: "components.templates.products.form.sections.certification.TeachersField.fieldLabel",
    description: "Label of the teachers field",
    defaultMessage: "Teachers",
  },
  fieldHelperText: {
    id: "components.templates.products.form.sections.certification.TeachersField.fieldHelperText",
    description: "Helper text for the teachers field",
    defaultMessage: "Teachers that will appear on the certificate.",
  },
});

type TeachersFieldProps = {
  product: Product;
};

function TeachersField({ product }: TeachersFieldProps) {
  const intl = useIntl();
  const modal = useModal();
  const [query, setQuery] = useState("");
  const [editedTeacher, setEditedTeacher] = useState<Nullable<Teacher>>(null);
  const teachersQuery = useTeachers({ query });
  const searchTeachers = useDebouncedCallback(setQuery, 300);

  const mergeValues = (values: Teacher[], newValue: Teacher) => {
    const valueExists = values.some((entry) => entry.id === newValue.id);
    if (valueExists) {
      return values.map((entry) =>
        entry.id === newValue.id ? newValue : entry,
      );
    }
    return [...values, newValue];
  };

  return (
    <RHFChipsField
      name="teachers"
      label={intl.formatMessage(messages.fieldLabel)}
      helperText={intl.formatMessage(messages.fieldHelperText)}
      options={teachersQuery.items}
      loading={teachersQuery.states.fetching}
      getOptionLabel={(option) => {
        if (typeof option === "string") return option;
        return `${option.first_name} ${option.last_name}`;
      }}
      getOptionKey={(option) => {
        if (typeof option === "string") return option;
        return option.id;
      }}
      getOptionDisabled={(option) => {
        return product.teachers.some((entry) => entry.id === option.id);
      }}
      onCreateTag={modal.handleOpen}
      onInputChange={(_, searchValue) => searchTeachers(searchValue)}
      renderTags={(value, getTagProps, ownerState) => {
        return value.map((option, index) => {
          const { key, ...props } = getTagProps({ index });
          return (
            <Chip
              key={key}
              {...props}
              label={ownerState.getOptionLabel(option)}
              data-id={option.id}
              onClick={() => {
                setEditedTeacher(option);
                modal.handleOpen();
              }}
            />
          );
        });
      }}
      renderTagEditForm={(field) => (
        <CreateOrEditTeacherModal
          modalProps={{
            ...modal,
            handleClose: () => {
              modal.handleClose();
              setEditedTeacher(null);
            },
          }}
          teacher={editedTeacher}
          onSuccess={(value) => {
            field.onChange(mergeValues(field.value, value));
          }}
        />
      )}
    />
  );
}

type CreateOrEditTeacherModalProps = {
  modalProps: ModalUtils;
  teacher?: Nullable<Teacher>;
  onSuccess?: (teacher: Teacher) => void;
  onClose?: () => void;
};

function CreateOrEditTeacherModal({
  modalProps,
  teacher,
  onSuccess,
}: CreateOrEditTeacherModalProps) {
  const intl = useIntl();
  const isEdit = Boolean(teacher);
  const handleSuccess = (newTeacher: Teacher) => {
    onSuccess?.(newTeacher);
    modalProps.handleClose();
  };

  return (
    <FullScreenModal
      {...modalProps}
      title={intl.formatMessage(
        isEdit ? commonTranslations.edit : commonTranslations.create,
      )}
    >
      <SimpleCard>
        <TeacherForm teacher={teacher} onSuccess={handleSuccess} />
      </SimpleCard>
    </FullScreenModal>
  );
}

export default TeachersField;
