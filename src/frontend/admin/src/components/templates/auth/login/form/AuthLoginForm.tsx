import * as React from "react";
import Stack from "@mui/material/Stack";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Typography from "@mui/material/Typography";
import { defineMessages, useIntl } from "react-intl";
import { useRouter } from "next/router";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { useAuthContext } from "@/components/auth/context/AuthContext";

const messages = defineMessages({
  forgotPassword: {
    id: "components.templates.auth.login.form.AuthLoginForm.forgotPasswordLabel",
    defaultMessage: "Forgot password ?",
    description: "Text fort forgot password link",
  },
});

interface LoginFormValues {
  username: string;
  password: string;
}

export function AuthLoginForm() {
  const router = useRouter();
  const authContext = useAuthContext();
  const intl = useIntl();
  const LoginSchema = Yup.object().shape({
    username: Yup.string().required(),
    password: Yup.string().required(),
  });

  const methods = useForm<LoginFormValues>({
    resolver: yupResolver(LoginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const onSubmit = (values: LoginFormValues) => {
    authContext.updateUser({ username: values.username });
    router.push("/admin/courses");
    // AuthRepository.login(values.username, values.password).then(() => {
    //   router.push("/admin/courses");
    // });
  };

  return (
    <RHFProvider methods={methods} onSubmit={methods.handleSubmit(onSubmit)}>
      <Stack spacing={2}>
        <RHFTextField
          name="username"
          label={intl.formatMessage(commonTranslations.username)}
        />
        <RHFTextField
          type="password"
          name="password"
          label={intl.formatMessage(commonTranslations.password)}
        />
        <Stack direction="row" justifyContent="start">
          <CustomLink href="/auth/forgot-password">
            <Typography color="text.secondary" variant="caption">
              {intl.formatMessage(messages.forgotPassword)}
            </Typography>
          </CustomLink>
        </Stack>
      </Stack>
    </RHFProvider>
  );
}
