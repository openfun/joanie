import { faker } from "@faker-js/faker";
import { Course } from "./Course";
import { CourseRun } from "./CourseRun";
import { CourseFactory } from "@/services/factories/courses";
import { randomNumber } from "@/utils/numbers";
import { CourseRunFactory } from "@/services/factories/courses-runs";
import { ToFormValues } from "@/types/utils";

export type ProductTargetCourseRelation = {
  id: string;
  course: Course;
  graded?: boolean;
  course_runs: CourseRun[];
  position?: number;
};

export type ProductTargetCourseRelationOptionalId = Omit<
  ProductTargetCourseRelation,
  "id"
> & {
  id?: string;
};

export type ProductTargetCourseRelationFormValues = ToFormValues<{
  course: Course;
  course_runs?: CourseRun[];
  enable_course_runs?: boolean;
}>;

export type DTOProductTargetCourseRelation = {
  id?: string;
  course: string;
  graded?: boolean;
  course_runs?: string[];
  position?: number;
};

const buildProductTargetCourseRelation = (): ProductTargetCourseRelation => {
  return {
    id: faker.string.uuid(),
    course: CourseFactory(),
    graded: true,
    course_runs: CourseRunFactory(randomNumber(10)),
  };
};

export function ProductTargetCourseRelationFactory(): ProductTargetCourseRelation;
export function ProductTargetCourseRelationFactory(
  count: number,
): ProductTargetCourseRelation[];
export function ProductTargetCourseRelationFactory(
  count?: number,
): ProductTargetCourseRelation | ProductTargetCourseRelation[] {
  if (count) return [...Array(count)].map(buildProductTargetCourseRelation);
  return buildProductTargetCourseRelation();
}
