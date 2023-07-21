import * as React from "react";
import { useMemo, useState } from "react";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseRun } from "@/services/api/models/CourseRun";
import { getCoursesRunsListColumns } from "@/components/templates/courses-runs/list/CourseRunsListColumns";
import { Maybe } from "@/types/utils";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";

export function CoursesRunsList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [query, setQuery] = useState<Maybe<string>>();
  const courseRuns = useCoursesRuns({ query });

  const debouncedSetQuery = useDebouncedCallback(setQuery, 300);

  const columns: GridColDef[] = useMemo(
    () => getCoursesRunsListColumns(intl),
    [intl],
  );

  return (
    <SimpleCard>
      <TableComponent
        rows={courseRuns.items}
        loading={courseRuns.states.isLoading}
        columns={columns}
        onSearch={debouncedSetQuery}
        columnBuffer={6}
        onEditClick={(courseRun: CourseRun) => {
          if (courseRun.id) {
            push(PATH_ADMIN.courses_run.edit(courseRun?.id));
          }
        }}
        getEntityName={(courseRun) => {
          return courseRun.title;
        }}
        onRemoveClick={(courseRun: CourseRun) => {
          courseRuns.methods.delete(courseRun.id);
        }}
      />
    </SimpleCard>
  );
}
