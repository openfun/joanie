import * as React from "react";
import { Course } from "@/services/api/models/Course";
import { OfferingList } from "@/components/templates/offerings/offering/OfferingList";

type Props = {
  course: Course;
  invalidateCourse: () => void;
};

export function OfferingsSection({ course, invalidateCourse }: Props) {
  return (
    <OfferingList
      courseId={course.id}
      offerings={course.offerings ?? []}
      invalidate={invalidateCourse}
    />
  );
}
