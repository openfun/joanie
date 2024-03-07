import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import { useFormContext } from "react-hook-form";
import { Priority } from "@/services/api/models/Course";
import {
  RHFSelect,
  RHFSelectProps,
  SelectOption,
} from "@/components/presentational/hook-form/RHFSelect";
import { courseRunStateMessages } from "@/translations/course-runs/priority-state";
import { useSearchFilterContext } from "@/components/presentational/filters/SearchFilters";

const messages = defineMessages({
  state: {
    id: "components.templates.coursesRuns.input.RHFSelectCourseRunState.state",
    description: "Label text for the select state input",
    defaultMessage: "State",
  },
});

export function RHFSelectCourseRunState(props: RHFSelectProps) {
  const searchFilterContext = useSearchFilterContext(props.isFilterContext);
  const { setValue } = useFormContext();
  const intl = useIntl();
  const options: SelectOption[] = useMemo(() => {
    const result: SelectOption[] = [];
    Object.values(Priority).forEach((v) => {
      if (v && typeof v === "number") {
        result.push({
          label: intl.formatMessage(courseRunStateMessages[v as Priority]),
          value: v + "",
        });
      }
    });
    return result;
  }, []);

  const afterChange = (newValue: string) => {
    if (!props.isFilterContext || !searchFilterContext) {
      return;
    }

    if (newValue && !Number.isNaN(Number(newValue))) {
      searchFilterContext.addChip({
        name: props.name,
        label: intl.formatMessage(messages.state),
        value: intl.formatMessage(
          courseRunStateMessages[newValue as unknown as Priority],
        ),
        onDelete: (name: string) => {
          setValue(name, "", { shouldValidate: true, shouldDirty: true });
        },
      });
    } else {
      searchFilterContext.removeChip(props.name);
    }
  };

  return (
    <RHFSelect
      options={options}
      afterChange={afterChange}
      noneOption={true}
      {...props}
      label={intl.formatMessage(messages.state)}
    />
  );
}
