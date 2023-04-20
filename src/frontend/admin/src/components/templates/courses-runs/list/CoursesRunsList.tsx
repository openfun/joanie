import * as React from "react";
import { useMemo, useState } from "react";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useDebouncedCallback } from "use-debounce";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseRun } from "@/services/api/models/CourseRun";
import { getCoursesRunsListColumns } from "@/components/templates/courses-runs/list/CoursesRunsListCols";
import { Maybe } from "@/types/utils";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";

export function CoursesRunsList() {
  const intl = useIntl();
  const { push } = useRouter();
  const [search, setSearch] = useState<Maybe<string>>();
  const courseRuns = useCoursesRuns({ search });

  const onSearch = useDebouncedCallback((term) => {
    setSearch(term);
  }, 300);

  const columns: GridColDef[] = useMemo(
    () => getCoursesRunsListColumns(intl),
    []
  );

  return (
    <TableComponent
      rows={courseRuns.items}
      loading={courseRuns.states.isLoading}
      columns={columns}
      onSearch={onSearch}
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
  );
}
