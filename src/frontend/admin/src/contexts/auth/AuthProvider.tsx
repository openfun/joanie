import * as React from "react";
import { PropsWithChildren, useEffect, useMemo, useState } from "react";
import { AuthContext, AuthContextInterface } from "./AuthContext";
import { AuthenticatedUser } from "@/types/auth";
import { Maybe } from "@/types/utils";
import { AuthRepository } from "@/services/repositories/auth/AuthRepository";

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
    AuthRepository.me().then(setUser);
  }, []);

  if (!authContext) return null;

  return (
    <AuthContext.Provider value={authContext}>{children}</AuthContext.Provider>
  );
}
