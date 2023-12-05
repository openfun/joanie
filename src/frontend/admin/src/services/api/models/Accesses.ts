import { User } from "@/services/api/models/User";

export type Accesses<Roles extends string = string> = {
  id: string;
  role: Roles;
  user: User;
};

export type DTOAccesses<Roles extends string = string> = {
  user_id?: string;
  role: Roles;
};

export type AvailableAccess = {
  value: string;
  display_name: string;
};
