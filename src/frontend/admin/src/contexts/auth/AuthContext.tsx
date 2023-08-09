import React from "react";
import { Maybe } from "@/types/utils";
import { AuthenticatedUser } from "@/types/auth";

export interface AuthContextInterface {
  user: AuthenticatedUser;
  setUser: (user: AuthenticatedUser) => void;
}

export const AuthContext =
  React.createContext<Maybe<AuthContextInterface>>(undefined);

export const useAuthContext = () => {
  const authContext = React.useContext(AuthContext);

  if (!authContext) {
    throw new Error(`useAuthContext must be used within a AuthContext`);
  }

  return authContext;
};
