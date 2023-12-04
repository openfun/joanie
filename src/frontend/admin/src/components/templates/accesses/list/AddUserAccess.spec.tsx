import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "mocks/server";
import { CourseRoles } from "@/services/api/models/Course";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { AddUserAccess } from "@/components/templates/accesses/list/AddUserAccess";
import { UsersFactory } from "@/services/factories/users";
import { buildApiUrl } from "@/services/http/HttpService";
import { userRoutes } from "@/services/repositories/Users/UsersRepository";

describe("<AddUserAccess />", () => {
  it("render component and test onAdd callback", async () => {
    const returnedUser = UsersFactory();
    server.use(
      http.get(buildApiUrl(userRoutes.getAll()), () => {
        return HttpResponse.json([returnedUser]);
      }),
    );
    const allAccesses = Object.values(CourseRoles);
    const roles = allAccesses.map((item) => ({
      label: item,
      value: item,
    }));

    const onAdd = jest.fn();

    render(
      <AddUserAccess
        allAccesses={roles}
        defaultRole={roles[0].value}
        onAdd={onAdd}
      />,
      {
        wrapper: TestingWrapper,
      },
    );

    // Search and select user
    const userSearch = await screen.findByRole("combobox", { name: "User" });
    await userEvent.click(userSearch);
    await userEvent.type(userSearch, returnedUser.username);
    const searchResult = screen.getByText(returnedUser.username);
    await userEvent.click(searchResult);

    // Test default role
    const select = screen.getByTestId("select-role");
    const inputValue = within(select).getByTestId("select-value");
    expect(inputValue).toHaveValue(roles[0].value);

    // Click on add button
    const addButton = screen.getByRole("button", { name: "Add" });
    await userEvent.click(addButton);
    expect(onAdd).toBeCalledWith(returnedUser, roles[0].value);
  }, 10000);
});
