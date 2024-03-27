import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useFormContext } from "react-hook-form";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { useSearchFilterContext } from "@/components/presentational/filters/SearchFilters";
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
  const searchFilterContext = useSearchFilterContext(props.isFilterContext);
  const { setValue } = useFormContext();
  const intl = useIntl();
  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(EnrollmentState).forEach((v) => {
      if (v) {
        result.push({
          label: intl.formatMessage(
            enrollmentStateMessages[v as EnrollmentState],
          ),
          value: v + "",
        });
      }
    });
    return result;
  }, []);

  return (
    <RHFSelect
      getOptionLabel={(value) =>
        intl.formatMessage(
          enrollmentStateMessages[value as unknown as EnrollmentState],
        )
      }
      options={options}
      // afterChange={afterChange}
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.state)}
    />
  );
}
