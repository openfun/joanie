import { Organization } from "./Organization";
import { Course } from "./Course";
import { Product } from "@/services/api/models/Product";

export type CourseRelationToProduct = {
  product: Product;
  organizations: Organization[];
};

export type DTOCourseRelationToProduct = {
  product: string;
  organizations: string[];
};

export type ProductRelationToCourse = {
  course: Course;
  organizations: Organization[];
};
