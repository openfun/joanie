import { faker } from "@faker-js/faker";
import { Course } from "./Course";
import { CourseRun } from "./CourseRun";
import { CourseFactory } from "@/services/factories/courses";
import { randomNumber } from "@/utils/numbers";
import { CourseRunFactory } from "@/services/factories/courses-runs";

export const DEFAULT_IS_GRADED_VALUE = true;

export type ProductTargetCourseRelation = {
  id: string;
  course: Course;
  is_graded?: boolean;
  course_runs: CourseRun[];
  position?: number;
};

export type DTOProductTargetCourseRelation = {
  id?: string;
  course: string;
  is_graded?: boolean;
  course_runs?: string[];
  position?: number;
};

export type ProductTargetCourseRelationOptionalId = Omit<
  ProductTargetCourseRelation,
  "id"
> & {
  id?: string;
};

export type ProductTargetCourseDummy = Omit<
  ProductTargetCourseRelation,
  "id"
> & {
  dummyId?: string;
};

export type ProductTargetCourseRelationFormValues = {
  course: Course;
  course_runs?: CourseRun[];
  enable_course_runs?: boolean;
  is_graded: boolean;
};

const buildProductTargetCourseRelation = (): ProductTargetCourseRelation => {
  return {
    id: faker.string.uuid(),
    course: CourseFactory(),
    is_graded: true,
    course_runs: CourseRunFactory(randomNumber(2)),
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
