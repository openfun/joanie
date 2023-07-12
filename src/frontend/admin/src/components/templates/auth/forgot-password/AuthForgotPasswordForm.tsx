import * as React from "react";
import Stack from "@mui/material/Stack";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";

interface FormValues {
  email: string;
}

export function AuthForgotPasswordForm() {
  const intl = useIntl();

  const LoginSchema = Yup.object().shape({
    email: Yup.string().email().required(),
  });

  const methods = useForm<FormValues>({
    resolver: yupResolver(LoginSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = () => {
    // router.push("/admin/courses");
    // AuthRepository.login(values.username, values.password).then(() => {
    //   router.push("/admin/courses");
    // });
  };

  return (
    <RHFProvider methods={methods} onSubmit={methods.handleSubmit(onSubmit)}>
      <Stack spacing={2}>
        <RHFTextField
          name="email"
          label={intl.formatMessage(commonTranslations.email)}
        />
        <Stack direction="row" justifyContent="start">
          <CustomLink href="/auth/login">
            <Typography color="text.secondary" variant="caption">
              {intl.formatMessage(commonTranslations.login)}
            </Typography>
          </CustomLink>
        </Stack>
      </Stack>
    </RHFProvider>
  );
}
