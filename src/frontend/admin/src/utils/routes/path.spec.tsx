import { PATH_ADMIN } from "@/utils/routes/path";

describe("PATH_ADMIN auth", () => {
  it("should provide login path with a next query param", () => {
    // Login accepts a redirect path
    expect(PATH_ADMIN.auth.login(PATH_ADMIN.courses.list)).toBe(
      `http://localhost:8071/admin/login/?next=${encodeURIComponent(
        "/redirects/backoffice/admin/courses/list",
      )}`,
    );

    // Otherwise, it should redirect to the current location pathname
    expect(PATH_ADMIN.auth.login()).toBe(
      `http://localhost:8071/admin/login/?next=${encodeURIComponent(
        "/redirects/backoffice/",
      )}`,
    );
  });
  it("should provide logout path with a next query param", () => {
    // Logout accepts a redirect path
    expect(PATH_ADMIN.auth.logout(PATH_ADMIN.courses.list)).toBe(
      `http://localhost:8071/admin/logout/?next=${encodeURIComponent(
        "/redirects/backoffice/admin/courses/list",
      )}`,
    );

    // Otherwise, it should redirect to the current location pathname
    expect(PATH_ADMIN.auth.logout()).toBe(
      `http://localhost:8071/admin/logout/?next=${encodeURIComponent(
        "/redirects/backoffice/",
      )}`,
    );
  });
});
