import * as React from "react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import * as Yup from "yup";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import Stack from "@mui/material/Stack";
import { FormattedMessage, useIntl } from "react-intl";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import {
  ProductTargetCourseRelation,
  ProductTargetCourseRelationFormValues,
} from "@/services/api/models/ProductTargetCourseRelation";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { productFormMessages } from "@/components/templates/products/form/translations";
import { Optional } from "@/types/utils";
import { CoursesRunsList } from "@/components/templates/courses-runs/list/CoursesRunsList";
import { Course } from "@/services/api/models/Course";
import { CourseRun } from "@/services/api/models/CourseRun";

type Props = {
  targetCourse?: Optional<ProductTargetCourseRelation, "id">;
  onSubmit: (target: ProductTargetCourseRelationFormValues) => void;
};
export function ProductTargetCourseRelationForm(props: Props) {
  const intl = useIntl();

  const Schema = Yup.object().shape({
    course: Yup.mixed<Course>().required(),
    course_runs: Yup.array<any, CourseRun>().min(0).optional(),
  });

  const getDefaultValues = (): ProductTargetCourseRelationFormValues => {
    let courseRunsDefault: CourseRun[] = [];
    let courseDefault: any = null;
    if (props.targetCourse) {
      const { course_runs: courseRuns, ...course } = props.targetCourse;
      courseRunsDefault = courseRuns ?? [];
      courseDefault = course.course;
    }

    return {
      course: courseDefault,
      course_runs: courseRunsDefault,
    };
  };

  const methods = useForm({
    resolver: yupResolver(Schema),
    defaultValues: getDefaultValues(),
  });

  const onSubmit = (values: ProductTargetCourseRelationFormValues): void => {
    props.onSubmit({
      course: values.course,
      course_runs: values.course_runs ?? [],
    });
  };

  const valueCourse = methods.watch("course");

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [props.targetCourse]);

  return (
    <RHFProvider
      id="product-target-course-form"
      methods={methods}
      onSubmit={methods.handleSubmit(onSubmit)}
    >
      <Grid container spacing={2}>
        <Grid xs={12}>
          <Alert severity="info">
            {intl.formatMessage(
              productFormMessages.productTargetCourseFormInfo,
            )}
          </Alert>
        </Grid>
        <Grid xs={12} mt={3}>
          <Stack spacing={2}>
            <CourseSearch enableAdd enableEdit name="course" />

            {valueCourse != null && (
              <Box mt={4}>
                <Typography variant="subtitle2" component="h6">
                  <FormattedMessage
                    {...productFormMessages.addTargetCourseCourseRunModalTitle}
                  />
                </Typography>
                <CoursesRunsList
                  enableDelete={false}
                  defaultSelectedRows={
                    props.targetCourse?.course_runs.map(
                      (courseRun) => courseRun.id,
                    ) ?? []
                  }
                  enableSelect
                  onSelectRows={(ids, selectedCourseRuns) => {
                    methods.setValue("course_runs", selectedCourseRuns);
                  }}
                  courseId={valueCourse.id}
                />
              </Box>
            )}
          </Stack>
        </Grid>
      </Grid>
    </RHFProvider>
  );
}
