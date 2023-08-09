export type AuthenticatedUser = {
  full_name: string;
  id: string;
  is_staff: boolean;
  is_superuser: boolean;
  username: string;
  abilities: {
    delete: boolean;
    get: boolean;
    has_course_access: boolean;
    has_organization_access: boolean;
    patch: boolean;
    put: boolean;
  };
};
