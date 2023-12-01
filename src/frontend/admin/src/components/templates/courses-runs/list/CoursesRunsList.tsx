import * as React from "react";
import { useMemo } from "react";
import { useIntl } from "react-intl";
import { useRouter } from "next/router";
import { GridColDef } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import {
  DefaultTableProps,
  TableComponent,
} from "@/components/presentational/table/TableComponent";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CourseRun } from "@/services/api/models/CourseRun";
import { getCoursesRunsListColumns } from "@/components/templates/courses-runs/list/CourseRunsListColumns";
import {
  CourseRunResourcesQuery,
  useCoursesRuns,
} from "@/hooks/useCourseRun/useCourseRun";
import { usePaginatedTableResource } from "@/components/presentational/table/usePaginatedTableResource";

type Props = DefaultTableProps<CourseRun> & {
  courseId?: string;
};

export function CoursesRunsList({ courseId, ...props }: Props) {
  const intl = useIntl();
  const snackbar = useSnackbar();
  const { push } = useRouter();

  const paginatedResource = usePaginatedTableResource<
    CourseRun,
    CourseRunResourcesQuery
  >({
    useResource: useCoursesRuns,
    filters: { courseId },
  });

  const columns: GridColDef[] = useMemo(
    () => getCoursesRunsListColumns(intl, snackbar),
    [intl],
  );

  const useAsTemplate = (courseRun: CourseRun) => {
    if (courseRun.id === undefined) {
      return;
    }
    push(`${PATH_ADMIN.courses_run.create}?from=${courseRun?.id}`);
  };

  return (
    <TableComponent
      {...paginatedResource.tableProps}
      {...props}
      columns={columns}
      columnBuffer={6}
      onEditClick={(courseRun: CourseRun) => {
        if (courseRun.id) {
          push(PATH_ADMIN.courses_run.edit(courseRun?.id));
        }
      }}
      onUseAsTemplateClick={useAsTemplate}
      getEntityName={(courseRun) => {
        return courseRun.title;
      }}
      onRemoveClick={(courseRun: CourseRun) => {
        paginatedResource.methods.delete(courseRun.id);
      }}
    />
  );
}
