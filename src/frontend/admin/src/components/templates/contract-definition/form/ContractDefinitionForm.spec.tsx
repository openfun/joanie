import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TestingWrapper } from "@/components/testing/TestingWrapper";
import { ContractDefinitionForm } from "@/components/templates/contract-definition/form/ContractDefinitionForm";

describe("<ContractDefinitionForm/>", () => {
  beforeEach(() => {
    jest.useFakeTimers({ advanceTimers: true });
  });

  afterEach(() => {
    cleanup();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("renders an empty form ", async () => {
    const user = userEvent.setup();
    render(<ContractDefinitionForm />, {
      wrapper: TestingWrapper,
    });

    await screen.findByRole("textbox", { name: "Title" });
    screen.getByRole("combobox", { name: "Language" });
    screen.getByRole("textbox", { name: "Description" });

    const markdownEditorContainer = await screen.findByTestId("md-editor");
    const markdownTextbox = within(markdownEditorContainer).getByRole(
      "textbox",
    );
    await user.type(markdownTextbox, "### Hello");
    expect(markdownTextbox).toHaveValue("### Hello");

    screen.getByRole("button", { name: "Submit" });
  });
});
