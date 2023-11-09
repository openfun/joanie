import * as process from "process";
import * as React from "react";
import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { AuthContext, AuthContextInterface } from "./AuthContext";
import { AuthenticatedUser } from "@/types/auth";
import { Maybe } from "@/types/utils";
import { AuthRepository } from "@/services/repositories/auth/AuthRepository";

const testUser = {
  abilities: {
    delete: false,
    get: true,
    has_course_access: true,
    has_organization_access: true,
    patch: true,
    put: true,
  },
  full_name: "",
  id: "ad2be34d-ab38-407f-a5d1-33eadb592023",
  is_staff: true,
  is_superuser: true,
  username: "admin",
};

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<Maybe<AuthenticatedUser>>(undefined);
  const authContext: Maybe<AuthContextInterface> = useMemo(() => {
    if (!user) return undefined;
    return {
      user,
      setUser,
    };
  }, [user]);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_API_SOURCE === "test") {
      setUser(testUser);
    } else {
      AuthRepository.me().then(setUser);
    }
  }, []);

  if (!authContext) return null;

  return (
    <AuthContext.Provider value={authContext}>{children}</AuthContext.Provider>
  );
}
