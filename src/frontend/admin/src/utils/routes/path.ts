const ROOTS_ADMIN = "/admin";
function path(sublink: string, root: string = ROOTS_ADMIN) {
  return `${root}${sublink}`;
}

export const PATH_ADMIN = {
  rootAdmin: ROOTS_ADMIN,
  organizations: {
    root: path("/organizations"),
    list: path("/organizations/list"),
    create: path("/organizations/create"),
    edit: (id: string) => path(`/organizations/${id}/edit`),
  },
  courses: {
    root: path("/courses"),
    list: path("/courses/list"),
    create: path("/courses/create"),
    edit: (id: string) => path(`/courses/${id}/edit`),
  },
  courses_run: {
    root: path("/courses-runs"),
    list: path("/courses-runs/list"),
    create: path("/courses-runs/create"),
    edit: (id: string) => path(`/courses-runs/${id}/edit`),
  },
  products: {
    root: path("/products"),
    list: path("/products/list"),
    create: path("/products/create"),
    edit: (id: string) => path(`/products/${id}/edit`),
  },
  vouchers: {
    root: path("/vouchers"),
    list: path("/vouchers/list"),
    create: path("/vouchers/create"),
    edit: (id: string) => path(`/vouchers/${id}/edit`),
  },
  certificates: {
    root: path("/certificates-definitions"),
    list: path("/certificates-definitions/list"),
    create: path("/certificates-definitions/create"),
    edit: (id: string) => path(`/certificates-definitions/${id}/edit`),
  },
  contract_definition: {
    root: path("/contracts-definitions"),
    list: path("/contracts-definitions/list"),
    create: path("/contracts-definitions/create"),
    edit: (id: string) => path(`/contracts-definitions/${id}/edit`),
  },
  orders: {
    root: path("/orders"),
    list: path("/orders/list"),
    view: (id: string) => path(`/orders/${id}/view`),
  },
  enrollments: {
    root: path("/enrollments"),
    list: path("/enrollments/list"),
    view: (id: string) => path(`/enrollments/${id}/view`),
  },
  auth: {
    login: (redirectUrl?: string) => {
      // eslint-disable-next-line compat/compat
      const url = new URL(
        `${process.env.NEXT_PUBLIC_DJANGO_ADMIN_BASE_URL}/login/`,
      );
      const redirectPath = redirectUrl ?? window.location.pathname;
      url.searchParams.append("next", `/redirects/backoffice${redirectPath}`);

      return url.toString();
    },
    logout: (redirectUrl?: string) => {
      // eslint-disable-next-line compat/compat
      const url = new URL(
        `${process.env.NEXT_PUBLIC_DJANGO_ADMIN_BASE_URL}/logout/`,
      );
      const redirectPath = redirectUrl ?? window.location.pathname;
      url.searchParams.append("next", `/redirects/backoffice${redirectPath}`);

      return url.toString();
    },
  },
};
