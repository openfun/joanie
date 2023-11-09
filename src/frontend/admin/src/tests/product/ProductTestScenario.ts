import { faker } from "@faker-js/faker";
import { ProductFactory } from "@/services/factories/product";
import { Course } from "@/services/api/models/Course";
import { Organization } from "@/services/api/models/Organization";
import { CourseRun } from "@/services/api/models/CourseRun";
import { DTOProduct, Product } from "@/services/api/models/Product";
import { CertificateDefinition } from "@/services/api/models/CertificateDefinition";

type ProductStore = {
  products: Product[];
  certificateDefinitions: CertificateDefinition[];
  courses: Course[];
  organizations: Organization[];
  courseRuns: CourseRun[];
  postUpdate: (payload: DTOProduct, item?: Product) => Product;
};

export const getProductScenarioStore = (): ProductStore => {
  const products = ProductFactory(5);
  const certificateDefinitions = products.map((product) => {
    return product.certificate_definition!;
  });
  const courses: Course[] = [];
  const organizations: Organization[] = [];
  const courseRuns: CourseRun[] = [];

  products.forEach((product) => {
    product.courses!.forEach((productRelationToCourse) => {
      courses.push(productRelationToCourse.course);
      productRelationToCourse.organizations.forEach((org) => {
        organizations.push(org);
      });
    });

    product.target_courses?.forEach((value) => {
      courses.push(value.course);
      value.course_runs.forEach((courseRun) => {
        courseRuns.push(courseRun);
      });
    });
  });

  const postUpdate = (payload: DTOProduct, item?: Product) => {
    const { certificate_definition: newCertificateDefinition, ...restPayload } =
      payload;

    const certificateDef = certificateDefinitions.find(
      (certificateDefinition) =>
        certificateDefinition.id === newCertificateDefinition,
    );

    let newProduct: Product;
    if (item) {
      newProduct = {
        ...item,
        ...restPayload,
        certificate_definition: certificateDef ?? item.certificate_definition,
      };
    } else {
      newProduct = {
        id: faker.string.uuid(),
        ...restPayload,
        ...(certificateDef && { certificate_definition: certificateDef }),
      };
    }
    products.push(newProduct);
    return newProduct;
  };

  return {
    products,
    certificateDefinitions,
    courses,
    organizations,
    courseRuns,
    postUpdate,
  };
};
