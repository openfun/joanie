import * as React from "react";
import { FormattedMessage, useIntl } from "react-intl";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import { Course } from "@/services/api/models/Course";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { CustomModal } from "@/components/presentational/modal/Modal";
import { useModal } from "@/components/presentational/modal/useModal";
import { CourseRunForm } from "@/components/templates/courses-runs/form/CourseRunForm";
import { useCoursesRuns } from "@/hooks/useCourseRun/useCourseRun";
import { CoursesRunsList } from "@/components/templates/courses-runs/list/CoursesRunsList";
import { courseFormMessages } from "@/components/templates/courses/form/translations";

type Props = {
  course: Course;
};

export function CourseFormTargetCourseRunsSection({ course }: Props) {
  const intl = useIntl();
  const modal = useModal();
  const courseRunsQuery = useCoursesRuns({}, { enabled: false });

  return (
    <>
      <SimpleCard>
        <CoursesRunsList
          courseId={course.id}
          topActions={
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Typography variant="h6" component="h2">
                <FormattedMessage
                  {...courseFormMessages.targetCourseRunTitle}
                />
              </Typography>
              <Button variant="contained" onClick={modal.handleOpen}>
                <FormattedMessage {...courseFormMessages.addCourseRunButton} />
              </Button>
            </Box>
          }
        />
      </SimpleCard>
      <CustomModal
        fullWidth
        maxWidth="lg"
        title={intl.formatMessage(courseFormMessages.addCourseRunModalTitle)}
        {...modal}
      >
        <CourseRunForm
          addToCourse={course}
          afterSubmit={() => {
            courseRunsQuery.methods.invalidate();
            modal.handleClose();
          }}
        />
      </CustomModal>
    </>
  );
}
