import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { EnrollmentState } from "@/services/api/models/Enrollment";
import { enrollmentStateMessages } from "@/translations/enrollments/enrollment-state";

const messages = defineMessages({
  state: {
    id: "components.templates.enrollments.input.RHFSelectEnrollmentState.state",
    description: "Label text for the select state input",
    defaultMessage: "State",
  },
});

export function RHFSelectEnrollmentState(props: RHFSelectProps) {
  const intl = useIntl();
  const options: SelectOption[] = useMemo(() => {
    return Object.values(EnrollmentState).map((v) => ({
      label: intl.formatMessage(enrollmentStateMessages[v]),
      value: v,
    }));
  }, []);

  return (
    <RHFSelect
      getOptionLabel={(value: EnrollmentState) =>
        intl.formatMessage(enrollmentStateMessages[value])
      }
      options={options}
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.state)}
    />
  );
}
