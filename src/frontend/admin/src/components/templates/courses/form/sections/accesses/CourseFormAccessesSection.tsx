import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useIntl } from "react-intl";
import { useCourses } from "@/hooks/useCourses/useCourses";
import { LoadingContent } from "@/components/presentational/loading/LoadingContent";
import { SimpleCard } from "@/components/presentational/card/SimpleCard";
import { courseFormMessages } from "@/components/templates/courses/form/translations";
import { AccessesList } from "@/components/templates/accesses/list/AccessesList";
import { Course, CourseRoles } from "@/services/api/models/Course";

type Props = {
  course?: Course;
};

export function CourseFormAccessesSection({ course }: Props) {
  const intl = useIntl();
  const courses = useCourses({}, { enabled: false });
  return (
    <LoadingContent loading={courses.accesses === undefined}>
      {course && course.accesses && (
        <SimpleCard>
          <Box padding={4}>
            <Typography variant="h6" component="h2">
              {intl.formatMessage(courseFormMessages.membersSectionTitle)}
            </Typography>
          </Box>
          <AccessesList
            defaultRole={CourseRoles.MANAGER}
            onRemove={async (accessId) => {
              await courses.methods.removeAccessUser(course.id, accessId);
            }}
            onUpdateAccess={(accessId, payload) => {
              return courses.methods.updateAccessUser(
                course.id,
                accessId,
                payload,
              );
            }}
            onAdd={(user, role) => {
              if (course?.id && user.id) {
                courses.methods.addAccessUser(course.id, user.id, role);
              }
            }}
            accesses={course?.accesses ?? []}
            availableAccesses={courses.accesses ?? []}
          />
        </SimpleCard>
      )}
    </LoadingContent>
  );
}
