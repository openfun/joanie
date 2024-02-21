import Stepper from "@mui/material/Stepper";
import * as React from "react";
import {
  ReactElement,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import Step from "@mui/material/Step";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import StepButton from "@mui/material/StepButton";
import { defineMessages, useIntl } from "react-intl";
import Tooltip from "@mui/material/Tooltip";
import { Maybe } from "@/types/utils";

const messages = defineMessages({
  next: {
    id: "components.presentational.wizard.next",
    defaultMessage: "Next",
    description:
      "Text of the next button, which allows you to go to the next step.",
  },
  back: {
    id: "components.presentational.wizard.back",
    defaultMessage: "Back",
    description:
      "Text of the back button, which allows you to return to the previous step",
  },
  invalidStep: {
    id: "components.presentational.wizard.invalidStep",
    defaultMessage: "Invalid step, please validate this step",
    description:
      "Text used in a popover when hovering over buttons when the step is invalid",
  },
});

export interface WizardStepProps {
  onValidate?: (isValid: boolean) => void;
  defaultIsValid?: boolean;
}

export type WizardStep = {
  label: string;
  component: ReactElement;
};

export type WizardHandle = {
  step: number;

  back: () => void;
  next: () => void;
};

type Props = {
  steps: WizardStep[];
  callbackBeforeSwitchStep?: (step: number, switchStep: () => void) => void;
  lastStepActions?: ReactNode;
  rightActions?: ReactNode;
};

export function Wizard({ steps, ...props }: Props) {
  const [activeStep, setActiveStep] = useState<number>(0);
  const [disabledStepMessage, setDisabledStepMessage] = useState<string>();
  const [stepsAreValid, setStepsAreValid] = useState<boolean[]>(() => {
    return steps.map((step) =>
      step.component.props.defaultIsValid !== undefined
        ? step.component.props.defaultIsValid
        : true,
    );
  });

  useEffect(() => {
    const result: boolean[] = [];
    steps.forEach((value, index) => {
      if (stepsAreValid[index]) {
        result[index] = stepsAreValid[index];
      } else {
        result[index] =
          value.component.props.defaultIsValid !== undefined
            ? value.component.props.defaultIsValid
            : true;
      }
    });
    setStepsAreValid(result);
  }, [steps]);

  const handleNext = (): void => {
    if (activeStep === steps.length - 1) {
      return;
    }
    const nextStepCallback = () => setActiveStep(activeStep + 1);
    if (props.callbackBeforeSwitchStep) {
      props.callbackBeforeSwitchStep(activeStep, nextStepCallback);
    } else {
      nextStepCallback();
    }
  };

  const handleBack = (): void => {
    if (activeStep === 0) {
      return;
    }
    const previousStepCallback = () => setActiveStep(activeStep - 1);
    if (props.callbackBeforeSwitchStep) {
      props.callbackBeforeSwitchStep(activeStep, previousStepCallback);
    } else {
      previousStepCallback();
    }
  };

  const handleStep = (step: number) => () => {
    if (!stepsAreValid[activeStep]) {
      return;
    }
    const switchStep = () => {
      setActiveStep(step);
    };

    if (props.callbackBeforeSwitchStep) {
      props.callbackBeforeSwitchStep(activeStep, switchStep);
    } else {
      switchStep();
    }
  };

  const setIsValidStep = useCallback(
    (isValid: boolean, disableMessage?: string) => {
      const result = [...stepsAreValid];
      result[activeStep] = isValid;
      setStepsAreValid(result);
      if (disableMessage) {
        setDisabledStepMessage(disableMessage);
      }
    },
    [activeStep],
  );

  const contextValue: WizardContextInterface = useMemo(() => {
    return {
      setIsValidStep,
      setDisabledStepMessage,
    };
  }, []);

  const component = useMemo(() => {
    return React.cloneElement(steps[activeStep].component, {
      onValidate: (isValid: boolean) => {
        const current = [...stepsAreValid];
        current[activeStep] = isValid;
        setStepsAreValid(current);
      },
    });
  }, [steps, activeStep]);

  useEffect(() => {
    setDisabledStepMessage(undefined);
  }, [activeStep]);

  return (
    <WizardContext.Provider value={contextValue}>
      <Box width="100%">
        <Stepper nonLinear activeStep={activeStep} alternativeLabel>
          {steps.map((step, index) => (
            <Step key={step.label}>
              <StepButton onClick={handleStep(index)}>{step.label}</StepButton>
            </Step>
          ))}
        </Stepper>
        <Box p={2} key={activeStep}>
          {component}
        </Box>
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "space-between",
            pt: 2,
          }}
        >
          {steps.length > 1 && (
            <NavigateButton
              disableMessage={disabledStepMessage}
              handleNext={handleNext}
              handlePrevious={handleBack}
              activeStep={activeStep}
              isValidStep={stepsAreValid[activeStep]}
              maxStep={steps.length}
            />
          )}
          {props.rightActions}
          {props.lastStepActions && activeStep === steps.length - 1 && (
            <Box>{props.lastStepActions}</Box>
          )}
        </Box>
      </Box>
    </WizardContext.Provider>
  );
}

type NavigationButtonsProps = {
  handleNext: () => void;
  handlePrevious: () => void;
  disableMessage?: string;
  activeStep: number;
  isValidStep: boolean;
  maxStep: number;
};
function NavigateButton({
  handlePrevious,
  handleNext,
  activeStep,
  isValidStep,
  disableMessage,
  maxStep,
}: NavigationButtonsProps) {
  const intl = useIntl();

  const getTooltipMessage = (): string => {
    if (disableMessage) {
      return disableMessage;
    }
    return intl.formatMessage(messages.invalidStep);
  };

  const getButtons = () => {
    return (
      <Box data-testid="wizard-buttons-container">
        <Button
          color="inherit"
          disabled={activeStep === 0 || !isValidStep}
          onClick={handlePrevious}
          sx={{ mr: 1 }}
        >
          {intl.formatMessage(messages.back)}
        </Button>

        <Button
          onClick={handleNext}
          disabled={activeStep === maxStep - 1 || !isValidStep}
        >
          {intl.formatMessage(messages.next)}
        </Button>
      </Box>
    );
  };

  if (!isValidStep) {
    return (
      <Tooltip placement="right" title={getTooltipMessage()} arrow>
        {getButtons()}
      </Tooltip>
    );
  }

  return getButtons();
}

export interface WizardContextInterface {
  setIsValidStep: (isValid: boolean, disabledMessage?: string) => void;
  setDisabledStepMessage: (message: string) => void;
}

export const WizardContext =
  React.createContext<Maybe<WizardContextInterface>>(undefined);

export const useWizardContext = () => {
  const wizardFilterContext = useContext(WizardContext);

  if (!wizardFilterContext) {
    throw new Error(`useWizardContext must be used within a WizardContext`);
  }

  return wizardFilterContext;
};
