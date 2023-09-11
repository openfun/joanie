import { act, render, screen, within } from "@testing-library/react";
import Button from "@mui/material/Button";
import userEvent from "@testing-library/user-event";
import { PropsWithChildren } from "react";
import {
  Wizard,
  WizardStepProps,
} from "@/components/presentational/wizard/Wizard";
import { TestingWrapper } from "@/components/testing/TestingWrapper";

describe("<Wizard />", () => {
  function WizardTestStep(props: PropsWithChildren<WizardStepProps>) {
    return <div>{props.children}</div>;
  }
  it("renders a Wizard component", async () => {
    const before = jest.fn();

    render(
      <Wizard
        lastStepActions={<Button>Submit</Button>}
        rightActions={<Button>Reset</Button>}
        callbackBeforeSwitchStep={(activeStep, switchStep) => {
          switchStep();
          before(activeStep);
        }}
        steps={[
          {
            label: "One",
            component: <WizardTestStep>Step one</WizardTestStep>,
          },
          {
            label: "Two",
            component: <WizardTestStep>Step two</WizardTestStep>,
          },
          {
            label: "Three",
            component: <WizardTestStep>Step three</WizardTestStep>,
          },
        ]}
      />,
      { wrapper: TestingWrapper },
    );

    const stepOne = await screen.findByText("One");
    expect(stepOne).toHaveClass("Mui-active");
    const stepTwo = await screen.findByText("Two");
    expect(stepTwo).not.toHaveClass("Mui-active");
    const stepThree = await screen.findByText("Three");
    expect(stepThree).not.toHaveClass("Mui-active");

    await screen.findByText("Step one");
    const backButton = screen.getByRole("button", { name: "Back" });
    const nextButton = screen.getByRole("button", { name: "Next" });
    expect(backButton).toBeDisabled();
    expect(nextButton).not.toBeDisabled();

    screen.getByRole("button", { name: "Reset" });

    await userEvent.click(nextButton);
    expect(before).toBeCalledWith(0);
    await screen.findByText("Step two");
    expect(stepTwo).toHaveClass("Mui-active");
    expect(stepOne).not.toHaveClass("Mui-active");

    expect(backButton).not.toBeDisabled();
    expect(nextButton).not.toBeDisabled();

    await userEvent.click(backButton);
    await screen.findByText("Step one");
    expect(stepOne).toHaveClass("Mui-active");
    expect(stepTwo).not.toHaveClass("Mui-active");

    await userEvent.click(nextButton);
    await screen.findByText("Step two");

    await userEvent.click(nextButton);
    expect(before).toBeCalledWith(1);
    await screen.findByText("Step three");
    expect(stepThree).toHaveClass("Mui-active");
    expect(stepTwo).not.toHaveClass("Mui-active");
    expect(backButton).not.toBeDisabled();
    expect(nextButton).toBeDisabled();

    screen.getByRole("button", { name: "Submit" });

    await userEvent.click(screen.getByRole("button", { name: "One" }));
    expect(before).toBeCalledWith(2);
    screen.getByText("Step one");

    await userEvent.click(screen.getByRole("button", { name: "Three" }));
    expect(before).toBeCalledWith(0);
    screen.getByText("Step three");

    await userEvent.click(screen.getByRole("button", { name: "Two" }));
    expect(before).toBeCalledWith(2);
    screen.getByText("Step two");
  });
  it("renders a Wizard component and test invalid step", async () => {
    jest.useFakeTimers({ advanceTimers: true });
    const before = jest.fn();

    render(
      <Wizard
        lastStepActions={<Button>Submit</Button>}
        rightActions={<Button>Reset</Button>}
        callbackBeforeSwitchStep={(activeStep, switchStep) => {
          switchStep();
          before(activeStep);
        }}
        steps={[
          {
            label: "One",
            component: (
              <WizardTestStep defaultIsValid={false}>Step one</WizardTestStep>
            ),
          },
          {
            label: "Two",
            component: <WizardTestStep>Step two</WizardTestStep>,
          },
          {
            label: "Three",
            component: <WizardTestStep>Step three</WizardTestStep>,
          },
        ]}
      />,
      { wrapper: TestingWrapper },
    );

    await screen.findByText("Step one");
    const backButton = screen.getByRole("button", { name: "Back" });
    const nextButton = screen.getByRole("button", { name: "Next" });
    const buttonsContainer = screen.getByTestId("wizard-buttons-container");
    expect(backButton).toBeDisabled();
    expect(nextButton).toBeDisabled();

    await userEvent.hover(buttonsContainer);
    act(() => {
      jest.runAllTimers();
    });
    const tooltip = await screen.findByRole("tooltip");
    const { getByText } = within(tooltip);
    getByText("Invalid step, please validate this step");

    const stepOne = await screen.findByText("One");
    const stepTwo = await screen.findByText("Two");
    expect(stepOne).toHaveClass("Mui-active");
    expect(stepTwo).not.toHaveClass("Mui-active");

    await userEvent.click(stepTwo);
    expect(stepOne).toHaveClass("Mui-active");
    expect(stepTwo).not.toHaveClass("Mui-active");
  });
});
