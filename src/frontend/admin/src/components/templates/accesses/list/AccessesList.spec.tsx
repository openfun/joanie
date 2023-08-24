import { render, screen, within } from "@testing-library/react";
import { AccessesFactory } from "@/services/factories/accesses";
import { CourseRoles } from "@/services/api/models/Course";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { AccessesList } from "@/components/templates/accesses/list/AccessesList";

describe("<AccessesList />", () => {
  it("render course accesses", async () => {
    const allAccesses = Object.values(CourseRoles);
    const accesses = AccessesFactory(allAccesses, 4);
    const roles = allAccesses.map((item) => ({
      label: item,
      value: item,
    }));

    const onAdd = jest.fn();
    const onUpdate = jest.fn();
    const onRemove = jest.fn();

    render(
      <AccessesList
        defaultRole={CourseRoles.MANAGER}
        availableAccesses={roles}
        accesses={accesses}
        onRemove={onRemove}
        onUpdateAccess={onUpdate}
        onAdd={onAdd}
      />,
      {
        wrapper: TestingWrapper,
      },
    );

    const select = await screen.findByTestId("select-role");
    const inputValue = within(select).getByTestId("select-value");
    expect(inputValue).toHaveValue(CourseRoles.MANAGER);

    screen.getByText("Username");
    screen.getByText("User role");
    accesses.forEach((access) => {
      screen.getByText(access.user.username);
      const userRoleSelect = screen.getByTestId(
        `change-user-role-select-${access.user.id}`,
      );
      expect(
        within(userRoleSelect).getByTestId("basic-select-input"),
      ).toHaveValue(access.role);
    });
  });
});
