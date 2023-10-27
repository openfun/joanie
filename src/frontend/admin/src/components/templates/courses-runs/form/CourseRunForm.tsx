import * as React from "react";
import { useEffect } from "react";
import * as Yup from "yup";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import Grid from "@mui/material/Unstable_Grid2";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useIntl } from "react-intl";
import { CourseRun, DTOCourseRun } from "@/services/api/models/CourseRun";
import { RHFProvider } from "@/components/presentational/hook-form/RHFProvider";
import { RHFTextField } from "@/components/presentational/hook-form/RHFTextField";
import { RHFDateTimePicker } from "@/components/presentational/hook-form/RHFDateTimePicker";
import { commonTranslations } from "@/translations/common/commonTranslations";
import { courseRunFormMessages } from "@/components/templates/courses-runs/form/translations";
import { CourseSearch } from "@/components/templates/courses/inputs/search/CourseSearch";
import { Course } from "@/services/api/models/Course";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { ServerSideErrorForm, ToFormValues } from "@/types/utils";
import {
  JoanieLanguage,
  RHFSelectLanguage,
  useSelectLanguageUtils,
} from "@/components/presentational/hook-form/RHFSelectLanguage";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";

interface FormValues
  extends ToFormValues<
    Omit<CourseRun, "course" | "state" | "languages" | "id">
  > {
  course: Course;
  languages: JoanieLanguage[];
}

interface Props {
  afterSubmit?: (courseRun: CourseRun) => void;
  courseRun?: CourseRun;
  fromCourseRun?: CourseRun;
}

export function CourseRunForm({ courseRun, ...props }: Props) {
  const intl = useIntl();
  const selectLanguageUtils = useSelectLanguageUtils();
  const courseRuns = useCoursesRuns({}, { enabled: false });
  const defaultCourseRun = courseRun ?? props.fromCourseRun;

  const RegisterSchema = Yup.object().shape({
    title: Yup.string().required(),
    course: Yup.object<Course>().required(),
    resource_link: Yup.string().required(),
    start: Yup.string().defined().nullable(),
    end: Yup.string().defined().nullable(),
    enrollment_start: Yup.string().defined().nullable(),
    enrollment_end: Yup.string().defined().nullable(),
    languages: Yup.array<JoanieLanguage>().required(),
    is_gradable: Yup.boolean().required(),
    is_listed: Yup.boolean().required(),
  });

  const getDefaultValues = () => {
    return {
      title: defaultCourseRun?.title ?? "",
      course: defaultCourseRun?.course ?? (null as any), // to not trigger type validation for the default values
      resource_link: defaultCourseRun?.resource_link ?? "",
      start: defaultCourseRun?.start ?? null,
      end: defaultCourseRun?.end ?? null,
      enrollment_start: defaultCourseRun?.enrollment_start ?? null,
      enrollment_end: defaultCourseRun?.enrollment_end ?? null,
      languages: selectLanguageUtils.getObjectsFromValues(
        defaultCourseRun?.languages,
      ),
      is_gradable: defaultCourseRun?.is_gradable ?? false,
      is_listed: defaultCourseRun?.is_listed ?? false,
    };
  };

  const methods = useForm({
    resolver: yupResolver(RegisterSchema),
    defaultValues: getDefaultValues(),
  });

  const updateFormError = (errors: ServerSideErrorForm<FormValues>) => {
    genericUpdateFormError(errors, methods.setError);
  };

  useEffect(() => {
    methods.reset(getDefaultValues());
  }, [courseRun]);

  const onSubmit = (values: FormValues) => {
    const payload: DTOCourseRun = {
      ...values,
      course: values.course.id,
      languages: selectLanguageUtils.getValuesFromObjects(values.languages),
    };

    if (courseRun) {
      payload.id = courseRun.id;
      courseRuns.methods.update(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => updateFormError(error.data),
      });
    } else {
      courseRuns.methods.create(payload, {
        onSuccess: (data) => props.afterSubmit?.(data),
        onError: (error) => {
          updateFormError(error.data);
        },
      });
    }
  };

  return (
    <TranslatableContent
      onSelectLang={() => {
        if (courseRun) courseRuns.methods.invalidate();
      }}
    >
      <Box padding={4}>
        <RHFProvider
          methods={methods}
          id="course-run-form"
          onSubmit={methods.handleSubmit(onSubmit)}
        >
          <Grid container spacing={2}>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(courseRunFormMessages.generalSubtitle)}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <CourseSearch name="course" label="Course" />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="title"
                label={intl.formatMessage(commonTranslations.title)}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFTextField
                name="resource_link"
                label={intl.formatMessage(
                  courseRunFormMessages.resourceLinkLabel,
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFSelectLanguage
                multiple={true}
                name="languages"
                label="Language"
              />
            </Grid>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(
                  courseRunFormMessages.courseRunDatesSubtitle,
                )}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker name="start" label="Start" />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker name="end" label="End" />
            </Grid>
            <Grid xs={12}>
              <Typography variant="subtitle2">
                {intl.formatMessage(
                  courseRunFormMessages.enrollmentDatesSubtitle,
                )}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_start"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentStartLabel,
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_end"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentEndLabel,
                )}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableContent>
  );
}
