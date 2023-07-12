import { JSX } from "react";
import { useRouter } from "next/router";
import { useAuthContext } from "@/components/auth/context/AuthContext";

type Props = {
  children: JSX.Element;
};
export function GuestGuard(props: Props) {
  const { user } = useAuthContext();
  const router = useRouter();

  if (user) {
    router.push("/admin/courses");
    return null;
  }

  return props.children;
}
