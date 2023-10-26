import * as React from "react";
import { useMemo } from "react";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { TableComponent } from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseRun } from "@/services/api/models/CourseRun";
import { getCoursesRunsListColumns } from "@/components/templates/courses-runs/list/CourseRunsListColumns";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";

export function CoursesRunsList() {
  const intl = useIntl();
  const { push } = useRouter();

  const paginatedResource = usePaginatedTableResource<CourseRun>({
    useResource: useCoursesRuns,
  });

  const columns: GridColDef[] = useMemo(
    () => getCoursesRunsListColumns(intl),
    [intl],
  );

  return (
    <SimpleCard>
      <TableComponent
        {...paginatedResource.tableProps}
        columns={columns}
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
          paginatedResource.methods.delete(courseRun.id);
        }}
      />
    </SimpleCard>
  );
}
