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
import { ServerSideErrorForm } from "@/types/utils";
import {
  JoanieLanguage,
  RHFSelectLanguage,
  useSelectLanguageUtils,
} from "@/components/presentational/hook-form/RHFSelectLanguage";
import { genericUpdateFormError } from "@/utils/forms";
import { TranslatableContent } from "@/components/presentational/translatable-content/TranslatableContent";

interface FormValues extends Omit<CourseRun, "course" | "languages"> {
  course: Course;
  languages: JoanieLanguage[];
}

interface Props {
  afterSubmit?: (courseRun: CourseRun) => void;
  courseRun?: CourseRun;
}

export function CourseRunForm({ courseRun, ...props }: Props) {
  const intl = useIntl();
  const selectLanguageUtils = useSelectLanguageUtils();
  const courseRuns = useCoursesRuns({}, { enabled: false });

  const RegisterSchema = Yup.object().shape({
    title: Yup.string().required(),
    course: Yup.mixed().required(),
    resource_link: Yup.string().required(),
    languages: Yup.array().of(Yup.mixed()).required(),
    is_gradable: Yup.boolean(),
    is_listed: Yup.boolean(),
    start: Yup.string().required(),
    end: Yup.string(),
    enrollment_start: Yup.string(),
    enrollment_end: Yup.string(),
  });

  const getDefaultValues = () => {
    return {
      title: courseRun?.title ?? "",
      course: courseRun?.course ?? {},
      resource_link: courseRun?.resource_link ?? "",
      languages: selectLanguageUtils.getObjectsFromValues(courseRun?.languages),
      is_gradable: courseRun?.is_gradable ?? false,
      is_listed: courseRun?.is_listed ?? false,
      start: courseRun?.start ?? "",
      end: courseRun?.end ?? "",
      enrollment_start: courseRun?.enrollment_start ?? "",
      enrollment_end: courseRun?.enrollment_end ?? "",
    };
  };

  const methods = useForm<FormValues>({
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
                  courseRunFormMessages.resourceLinkLabel
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
                  courseRunFormMessages.courseRunDatesSubtitle
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
                  courseRunFormMessages.enrollmentDatesSubtitle
                )}
              </Typography>
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_start"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentStartLabel
                )}
              />
            </Grid>
            <Grid xs={12} md={6}>
              <RHFDateTimePicker
                name="enrollment_end"
                label={intl.formatMessage(
                  courseRunFormMessages.enrollmentEndLabel
                )}
              />
            </Grid>
          </Grid>
        </RHFProvider>
      </Box>
    </TranslatableContent>
  );
}
