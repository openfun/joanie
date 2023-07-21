import { render, screen, within } from "@testing-library/react";
import * as React from "react";
import userEvent from "@testing-library/user-event";
import { BasicSelect } from "@/components/presentational/inputs/select/BasicSelect";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<BasicSelect />", () => {
  it("render", async () => {
    const onSelect = jest.fn();
    render(
      <BasicSelect
        showNoneValue={true}
        value="A"
        label="Basic select"
        onSelect={onSelect}
        options={[
          { label: "One", value: "A" },
          { label: "Two", value: "B" },
        ]}
      />,
      { wrapper: TestingWrapper },
    );

    const select = await screen.findByRole("button");
    await userEvent.click(select);
    const listbox = within(screen.getByRole("listbox"));
    listbox.getByText("None");
    listbox.getByText("One");
    await userEvent.click(listbox.getByText("Two"));
    expect(onSelect).toBeCalledWith("B");
  });
});
