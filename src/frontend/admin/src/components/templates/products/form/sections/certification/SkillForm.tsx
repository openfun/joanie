import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { Skill } from "@/services/api/models/Skill";
import { useSkill } from "@/hooks/useSkills";
import { TranslatableForm } from "@/components/presentational/translatable-content/TranslatableForm";
import { Nullable } from "@/types/utils";

const messages = defineMessages({
  titleInputLabel: {
    id: "components.templates.products.form.sections.certification.SkillForm.titleInputLabel",
    description: "Label of the title input",
    defaultMessage: "Title",
  },
});

const FORM_VALIDATION_SCHEMA = Yup.object().shape({
  title: Yup.string().required(),
});

type SkillFormValues = Omit<Skill, "id">;

type SkillFormProps = {
  skill?: Nullable<Skill>;
  onSuccess?: (skill: Skill) => void;
};

function SkillForm({ skill, onSuccess }: SkillFormProps) {
  const {
    item,
    methods: { create, update, invalidate },
  } = useSkill(skill?.id, {}, { enabled: !!skill });
  const intl = useIntl();

  const defaultValues = useMemo(
    () => ({
      title: item?.title ?? "",
    }),
    [item],
  );
  const form = useForm({
    resolver: yupResolver(FORM_VALIDATION_SCHEMA),
    values: defaultValues,
  });

  const onSubmit = form.handleSubmit(async (values: SkillFormValues) => {
    /* Manage success and error cases */
    const updateOrCreate = skill ? update : create;
    updateOrCreate(
      { id: skill?.id, ...values },
      {
        onSuccess,
      },
    );
  });

  if (skill && !item) {
    return (
      <Box padding={4}>
        <CircularProgress color="inherit" />
      </Box>
    );
  }

  return (
    <TranslatableForm
      resetForm={() => form.reset(defaultValues)}
      entitiesDeps={[item]}
      onSelectLang={invalidate}
    >
      <Box padding={4}>
        <RHFProvider id="teacher-form" methods={form} onSubmit={onSubmit}>
          <Grid container spacing={2}>
            <RHFTextField
              name="title"
              label={intl.formatMessage(messages.titleInputLabel)}
              required
            />
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableForm>
  );
}

export default SkillForm;
