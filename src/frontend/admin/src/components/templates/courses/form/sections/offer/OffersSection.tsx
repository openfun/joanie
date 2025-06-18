import * as React from "react";
import { Course } from "@/services/api/models/Course";
import { OfferList } from "@/components/templates/offers/offer/OfferList";

type Props = {
  course: Course;
  invalidateCourse: () => void;
};

export function OffersSection({ course, invalidateCourse }: Props) {
  return (
    <OfferList
      courseId={course.id}
      offers={course.offers ?? []}
      invalidate={invalidateCourse}
    />
  );
}
