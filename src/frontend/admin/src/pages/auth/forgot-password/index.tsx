import * as React from "react";
import { AuthLayout } from "@/layouts/auth/AuthLayout";
import { GuestGuard } from "@/components/auth/guard/GuestGuard";
import { AuthForgotPasswordForm } from "@/components/templates/auth/forgot-password/AuthForgotPasswordForm";

export default function Login() {
  return (
    <GuestGuard>
      <AuthForgotPasswordForm />
    </GuestGuard>
  );
}

Login.getLayout = (page: React.ReactElement) => <AuthLayout>{page}</AuthLayout>;
