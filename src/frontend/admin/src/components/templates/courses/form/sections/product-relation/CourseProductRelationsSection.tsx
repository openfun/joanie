import * as React from "react";
import { Course } from "@/services/api/models/Course";
import { CourseProductRelationList } from "@/components/templates/relations/course-product-relation/CourseProductRelationList";

type Props = {
  course: Course;
  invalidateCourse: () => void;
};

export function CourseProductRelationsSection({
  course,
  invalidateCourse,
}: Props) {
  return (
    <CourseProductRelationList
      courseId={course.id}
      relations={course.product_relations ?? []}
      invalidate={invalidateCourse}
    />
  );
}
