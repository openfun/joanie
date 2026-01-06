import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import { defineMessages, useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { Teacher } from "@/services/api/models/Teacher";
import { useTeachers } from "@/hooks/useTeachers";
import { Nullable } from "@/types/utils";

const messages = defineMessages({
  firstNameInputLabel: {
    id: "components.templates.products.form.sections.certification.TeacherForm.firstNameInputLabel",
    description: "Label of the first_name input",
    defaultMessage: "First name",
  },
  lastNameInputLabel: {
    id: "components.templates.products.form.sections.certification.TeacherForm.lastNameInputLabel",
    description: "Label of the last_name input",
    defaultMessage: "Last name",
  },
});

const FORM_VALIDATION_SCHEMA = Yup.object().shape({
  first_name: Yup.string().required(),
  last_name: Yup.string().required(),
});

type TeacherFormValues = Omit<Teacher, "id">;

type TeacherFormProps = {
  teacher?: Nullable<Teacher>;
  onSuccess?: (teacher: Teacher) => void;
};

function TeacherForm({ teacher, onSuccess }: TeacherFormProps) {
  const intl = useIntl();
  const {
    methods: { create, update },
  } = useTeachers(undefined, { enabled: false });
  const methods = useForm({
    resolver: yupResolver(FORM_VALIDATION_SCHEMA),
    defaultValues: {
      first_name: teacher?.first_name ?? "",
      last_name: teacher?.last_name ?? "",
    },
  });

  const onSubmit = methods.handleSubmit(async (values: TeacherFormValues) => {
    /* Manage success and error cases */
    const updateOrCreate = teacher ? update : create;
    updateOrCreate({ id: teacher?.id, ...values }, { onSuccess });
  });

  return (
    <Box padding={4}>
      <RHFProvider id="teacher-form" methods={methods} onSubmit={onSubmit}>
        <Grid container spacing={2}>
          <Grid size={6}>
            <RHFTextField
              name="first_name"
              label={intl.formatMessage(messages.firstNameInputLabel)}
              required
            />
          </Grid>
          <Grid size={6}>
            <RHFTextField
              name="last_name"
              label={intl.formatMessage(messages.lastNameInputLabel)}
              required
            />
          </Grid>
        </Grid>
      </RHFProvider>
    </Box>
  );
}

export default TeacherForm;
