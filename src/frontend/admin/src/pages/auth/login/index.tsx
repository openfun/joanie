import * as React from "react";
import { AuthLayout } from "@/layouts/auth/AuthLayout";
import { GuestGuard } from "@/components/auth/guard/GuestGuard";
import { AuthLoginForm } from "@/components/templates/auth/login/form/AuthLoginForm";

export default function Login() {
  return (
    <GuestGuard>
      <AuthLoginForm />
    </GuestGuard>
  );
}

Login.getLayout = (page: React.ReactElement) => <AuthLayout>{page}</AuthLayout>;
