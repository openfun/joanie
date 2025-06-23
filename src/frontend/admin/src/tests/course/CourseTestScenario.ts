import { faker } from "@faker-js/faker";
import { Page } from "@playwright/test";
import { Course, DTOCourse } from "@/services/api/models/Course";
import { CourseFactory } from "@/services/factories/courses";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";
import { BaseProduct } from "@/services/api/models/Product";
import { mockResource } from "@/tests/mockResource";
import { CourseRun } from "@/services/api/models/CourseRun";
import { catchAllIdRegex } from "@/tests/useResourceHandler";
import { postUpdateOrganization } from "@/tests/organization/OrganizationTestScenario";
import { Offering, DTOOffering } from "@/services/api/models/Offerings";
import {
  DTOOfferingRule,
  OfferingRule,
} from "@/services/api/models/OfferingRule";
import { mockCourseRunsFromCourse } from "@/tests/mocks/course-runs/course-runs-mocks";
import { Discount, DTODiscount } from "@/services/api/models/Discount";
import { DiscountFactory } from "@/services/factories/discounts";

export const getCourseScenarioStore = () => {
  const list = CourseFactory(5);
  const organizationList: Organization[] = [];
  const userList: User[] = [];
  const products: BaseProduct[] = [];
  const offerings: Offering[] = [];
  const courseRuns: CourseRun[] = [];
  let offeringRules: OfferingRule[] = [];
  const discounts: Discount[] = DiscountFactory(3);

  list.forEach((course) => {
    course.organizations.forEach((organization) => {
      organizationList.push(organization);
    });
    course.accesses?.forEach((access) => {
      userList.push(access.user);
    });
    course.offerings?.forEach((offering) => {
      offerings.push(offering);
      products.push(offering.product);
      organizationList.concat(offering.organizations);
      offeringRules = offeringRules.concat(offering.offering_rules);
    });
    course.courses_runs?.forEach((courseRun) => {
      courseRuns.push(courseRun);
    });
  });

  const productResource = mockResource<BaseProduct, DTOCourse>({
    data: products,
  });

  const organizationResource = mockResource<Organization, DTOOrganization>({
    data: organizationList,
  });

  const offeringResource = mockResource<Offering, DTOOffering>({
    data: offerings,
  });

  const courseResource = mockResource<Course, DTOCourse>({
    data: list,
  });

  const postOffering = (payload: DTOOffering, offering?: Offering) => {
    const course = courseResource.getResource(payload.course_id);
    const product = productResource.getResource(payload.product_id);
    const orgs: Organization[] = [];
    payload.organization_ids.forEach((id) => {
      const organization = organizationResource.getResource(id);
      if (organization) {
        orgs.push(organization);
      }
    });

    let result: Offering;
    if (offering) {
      result = {
        ...offering,
        product,
        organizations: orgs,
      };
      const index = offeringResource.getResourceIndex(offering.id);
      offerings[index] = result;
    } else {
      const { offerings: pr, ...restCourse } = course;
      result = {
        id: faker.string.uuid(),
        product,
        course: restCourse,
        organizations: orgs,
        offering_rules: [],
        can_edit: true,
      };
      offerings.push(result);
      course.offerings = [...(pr ?? []), result];
    }
    return result;
  };

  const postUpdate = (payload: DTOCourse, course?: Course) => {
    const {
      organization_ids: organizationsPayload,
      cover,
      effort,
      ...restPayload
    } = payload;

    const addedOrganizations: Organization[] = [];
    organizationsPayload.forEach((orgId) => {
      addedOrganizations.push(organizationResource.getResource(orgId));
    });

    const index = list.findIndex((item) => item.id === course?.id);

    const effortPayload = effort ? { effort } : {};
    let newCourse: Course;
    if (course && index >= 0) {
      newCourse = {
        ...course,
        ...restPayload,
        organizations: addedOrganizations,
        ...effortPayload,
      };
      list[index] = newCourse;
    } else {
      newCourse = {
        id: faker.string.uuid(),
        ...restPayload,
        organizations: addedOrganizations,
        is_graded: false,
        ...effortPayload,
      };
      list.push(newCourse);
    }
    return newCourse;
  };

  const createOrg = (payload: DTOOrganization) => {
    return postUpdateOrganization(payload, undefined, organizationList);
  };

  const createDiscount = (payload: DTODiscount) => {
    let discount = DiscountFactory();
    discount = {
      ...discount,
      ...payload,
    };
    discounts.push(discount);
    return discount;
  };

  return {
    list,
    organizations: organizationList,
    users: userList,
    products,
    courseRuns,
    offeringRules,
    discounts,
    postUpdate,
    createOrg,
    postOffering,
    offerings,
    mockCourseRunsFromCourse,
    mockOfferingRule,
    createDiscount,
  };
};

export const mockOfferingRule = async (
  page: Page,
  offerings: Offering[] = [],
  offeringRuleList: OfferingRule[] = [],
  discounts: Discount[] = [],
) => {
  const offeringRuleRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/offerings/:uuid/offering-rules/`,
    ":uuid",
  );

  const offeringRuleUpdateRegex = catchAllIdRegex(
    `http://localhost:8071/api/v1.0/admin/offerings/:uuid/offering-rules/:uuid/`,
    ":uuid",
  );

  const offeringRuleResource = mockResource<OfferingRule, DTOOfferingRule>({
    data: offeringRuleList,
  });

  const offeringsResource = mockResource<Offering, DTOOffering>({
    data: offerings,
  });

  const discountResource = mockResource<Discount, DTODiscount>({
    data: discounts,
  });

  const postOfferingRule = (
    payload: DTOOfferingRule,
    offeringId: string,
    offeringRuleToEdit?: OfferingRule,
  ) => {
    let result: OfferingRule;
    if (offeringRuleToEdit) {
      result = {
        ...offeringRuleToEdit,
        ...payload,
        nb_available_seats:
          (offeringRuleToEdit.nb_available_seats ?? 0) +
          ((payload.nb_seats ?? 0) - (offeringRuleToEdit.nb_seats ?? 0)),
      };
      const index = offeringRuleResource.getResourceIndex(
        offeringRuleToEdit.id,
      );
      offeringRuleList[index] = result;
    } else {
      result = {
        id: faker.string.uuid(),
        ...payload,
        description: payload.description ?? null,
        nb_seats: payload.nb_seats ?? null,
        nb_available_seats: payload.nb_seats ?? null,
        start: payload.start ?? null,
        end: payload.end ?? null,
        can_edit: false,
        discount: null,
      };
      offeringRuleList.push(result);
      const offering = offeringsResource.getResource(offeringId);
      offering.offering_rules = offering.offering_rules.concat(result);
    }

    if (payload.discount_id) {
      const discount = discountResource.getResource(payload.discount_id);
      if (discount) {
        result.discount = discount;
      }
    }

    return result;
  };

  await page.unroute(offeringRuleRegex);
  await page.route(offeringRuleRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(offeringRuleRegex);
    const offeringId = resultMatch?.[1] ?? "id";

    if (methods === "POST") {
      const payload: DTOOfferingRule = request.postDataJSON();
      const create = postOfferingRule(payload, offeringId);
      await route.fulfill({ json: create });
    }
  });

  await page.unroute(offeringRuleUpdateRegex);
  await page.route(offeringRuleUpdateRegex, async (route, request) => {
    const methods = request.method();
    const resultMatch = request.url().match(offeringRuleUpdateRegex);
    const offeringId = resultMatch?.[1] ?? "id";
    const offeringRuleId = resultMatch?.[2] ?? "offeringRuleId";

    if (methods === "PATCH") {
      const payload: DTOOfferingRule = request.postDataJSON();
      const offeringRule = offeringRuleResource.getResource(offeringRuleId);
      const update = postOfferingRule(payload, offeringId, offeringRule);
      await route.fulfill({ json: update });
    }
    if (methods === "DELETE") {
      const offeringRule = offeringRuleResource.deleteResource(offeringRuleId);
      await route.fulfill({ json: offeringRule });
    }
  });
};
