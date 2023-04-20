const ROOTS_ADMIN = "/admin";
function path(sublink: string, root: string = ROOTS_ADMIN) {
  return `${root}${sublink}`;
}

export const PATH_ADMIN = {
  root: ROOTS_ADMIN,
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
  certificates: {
    root: path("/certificates-definitions"),
    list: path("/certificates-definitions/list"),
    create: path("/certificates-definitions/create"),
    edit: (id: string) => path(`/certificates-definitions/${id}/edit`),
  },
};
