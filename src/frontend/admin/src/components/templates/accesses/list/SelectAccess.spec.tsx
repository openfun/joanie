import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SelectAccess } from "@/components/templates/accesses/list/SelectAccess";
import { AccessesFactory } from "@/services/factories/accesses";
import { CourseRoles } from "@/services/api/models/Course";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<SelectAccess/>", () => {
  it("render component", async () => {
    const allAccesses = Object.values(CourseRoles);
    const access = AccessesFactory(allAccesses);
    const roles = allAccesses.map((item) => ({
      label: item,
      value: item,
    }));
    const onUpdate = jest.fn();
    render(
      <SelectAccess
        access={access}
        availableAccesses={roles}
        onUpdateAccess={onUpdate}
      />,
      {
        wrapper: TestingWrapper,
      },
    );

    const select = await screen.findByRole("combobox");
    await userEvent.click(select);
    const listbox = within(screen.getByRole("listbox"));
    roles.forEach((role) => {
      listbox.getByText(role.label);
    });
  });
});
