import { useDebouncedCallback } from "use-debounce";
import { useState } from "react";
import Chip from "@mui/material/Chip";
import { defineMessages, useIntl } from "react-intl";
import SkillForm from "./SkillForm";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { FullScreenModal } from "@/components/presentational/modal/FullScreenModal";
import { Skill } from "@/services/api/models/Skill";
import { useSkills } from "@/hooks/useSkills";
import {
  ModalUtils,
  useModal,
} from "@/components/presentational/modal/useModal";
import RHFChipsField from "@/components/presentational/hook-form/RHFChipsField";
import { Nullable } from "@/types/utils";
import { Product } from "@/services/api/models/Product";
import { commonTranslations } from "@/translations/common/commonTranslations";

const messages = defineMessages({
  fieldLabel: {
    id: "components.templates.products.form.sections.certification.SkillsField.fieldLabel",
    description: "Label of the skills field",
    defaultMessage: "Skills",
  },
  fieldHelperText: {
    id: "components.templates.products.form.sections.certification.SkillsField.fieldHelperText",
    description: "Helper text for the skills field",
    defaultMessage: "Skills that will appear on the certificate.",
  },
});

type SkillsFieldProps = {
  product: Product;
};

function SkillsField({ product }: SkillsFieldProps) {
  const intl = useIntl();
  const modal = useModal();
  const [query, setQuery] = useState("");
  const [editedSkill, setEditedSkill] = useState<Nullable<Skill>>(null);
  const skillsQuery = useSkills({ query });
  const searchSkills = useDebouncedCallback(setQuery, 300);

  const mergeValues = (values: Skill[], newValue: Skill) => {
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
      name="skills"
      label={intl.formatMessage(messages.fieldLabel)}
      helperText={intl.formatMessage(messages.fieldHelperText)}
      options={skillsQuery.items}
      loading={skillsQuery.states.fetching}
      defaultValue={product.skills}
      getOptionLabel={(option) => {
        if (typeof option === "string") return option;
        return option.title;
      }}
      getOptionKey={(option) => {
        if (typeof option === "string") return option;
        return option.id;
      }}
      getOptionDisabled={(option) => {
        return product.skills.some((entry) => entry.id === option.id);
      }}
      isOptionEqualToValue={(option, value) => {
        return option.id === value.id;
      }}
      onCreateTag={modal.handleOpen}
      onInputChange={(_, searchValue) => searchSkills(searchValue)}
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
                setEditedSkill(option);
                modal.handleOpen();
              }}
            />
          );
        });
      }}
      renderTagEditForm={(field) => (
        <CreateOrEditSkillModal
          skill={editedSkill}
          modalProps={{
            ...modal,
            handleClose: () => {
              modal.handleClose();
              setEditedSkill(null);
            },
          }}
          onSuccess={(value) => {
            const newValues = mergeValues(field.value, value);
            field.onChange(newValues);
          }}
        />
      )}
    />
  );
}

type CreateOrEditSkillModalProps = {
  modalProps: ModalUtils;
  skill?: Nullable<Skill>;
  onSuccess?: (skill: Skill) => void;
};

function CreateOrEditSkillModal({
  modalProps,
  skill,
  onSuccess,
}: CreateOrEditSkillModalProps) {
  const intl = useIntl();
  const isEdit = Boolean(skill);
  const handleSuccess = (newSkill: Skill) => {
    onSuccess?.(newSkill);
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
        <SkillForm skill={skill} onSuccess={handleSuccess} />
      </SimpleCard>
    </FullScreenModal>
  );
}

export default SkillsField;
