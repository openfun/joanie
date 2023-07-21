import { render, screen } from "@testing-library/react";
import { rest } from "msw";
import * as React from "react";

import userEvent from "@testing-library/user-event";
import { useForm } from "react-hook-form";
import { server } from "mocks/server";
import { UsersFactory } from "@/services/factories/users";
import { buildApiUrl } from "@/services/http/HttpService";
import { userRoutes } from "@/services/repositories/Users/UsersRepository";
import { UserSearch } from "@/components/templates/users/inputs/search/UserSearch";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";

const returnedUser = UsersFactory();
describe("<UserSearch />", () => {
  beforeAll(() => {
    server.use(
      rest.get(buildApiUrl(userRoutes.getAll()), (req, res, ctx) => {
        return res(ctx.json([returnedUser]));
      }),
    );
  });

  function Element() {
    const methods = useForm({
      defaultValues: {
        name: null,
      },
    });

    return (
      <RHFProvider methods={methods} onSubmit={methods.handleSubmit(() => {})}>
        <UserSearch name="user" label="User search" size="small" />
      </RHFProvider>
    );
  }

  it("render and search by username", async () => {
    render(<Element />, {
      wrapper: TestingWrapper,
    });
    const userSearch = await screen.findByRole("combobox");
    await userEvent.click(userSearch);
    await userEvent.type(userSearch, returnedUser.username);
    screen.getByText(returnedUser.username);
  });

  it("render and search by fullname", async () => {
    render(<Element />, {
      wrapper: TestingWrapper,
    });
    const userSearch = await screen.findByRole("combobox");
    await userEvent.click(userSearch);
    await userEvent.type(userSearch, returnedUser.fullname);
    screen.getByText(returnedUser.username);
  });
});
