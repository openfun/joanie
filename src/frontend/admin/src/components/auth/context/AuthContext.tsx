import { Maybe } from "yup";
import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

type User = any;

export interface AuthContextInterface {
  user: Maybe<User> | null;
  updateUser: (user: Maybe<User> | null) => void;
}

const AuthContext = createContext<Maybe<AuthContextInterface>>(undefined);

type AuthContextProviderProps = {
  children: ReactNode;
  initialUser?: Maybe<User> | null;
};

export function AuthContextProvider({
  children,
  ...props
}: AuthContextProviderProps) {
  const [user, setUser] = useState<Maybe<User> | null>(
    props.initialUser ?? undefined
  );

  const queryClient = useQueryClient();

  useEffect(() => {
    if (props.initialUser != null) {
      queryClient.setQueryData(["currentUser"], props.initialUser);
    }
  }, []);

  const context: AuthContextInterface = useMemo(
    () => ({
      user,
      updateUser: (newUser: Maybe<User> | null) => {
        queryClient.setQueryData(["currentUser"], newUser);
        setUser(newUser);
      },
    }),
    [user]
  );
  return (
    <AuthContext.Provider value={context}>{children}</AuthContext.Provider>
  );
}

export const useAuthContext = () => {
  const authContext = useContext(AuthContext);

  if (authContext) {
    return authContext;
  }

  throw new Error(`useAuthContext must be used within a AuthContextProvider`);
};
