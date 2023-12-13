import { faker } from "@faker-js/faker";
import { OrganizationFactory } from "@/services/factories/organizations";
import {
  DTOOrganization,
  Organization,
} from "@/services/api/models/Organization";
import { User } from "@/services/api/models/User";

export const postUpdateOrganization = (
  payload: DTOOrganization,
  organizationToUpdate?: Organization,
  list: Organization[] = [],
) => {
  const { signature, logo, ...restPayload } = payload;
  const index = list.findIndex((item) => item.id === organizationToUpdate?.id);

  let newOrganization: Organization;
  if (index >= 0) {
    newOrganization = { ...list[index], ...restPayload };
    list[index] = newOrganization;
  } else {
    newOrganization = { id: faker.string.uuid(), ...restPayload };
    list.push(newOrganization);
  }

  return newOrganization;
};

export const getOrganizationScenarioStore = () => {
  const list = OrganizationFactory(5);
  const userList: User[] = [];

  list.forEach((organization) => {
    organization.accesses?.forEach((access) => {
      userList.push(access.user);
    });
  });

  const postUpdate = (
    payload: DTOOrganization,
    organizationToUpdate?: Organization,
  ) => {
    return postUpdateOrganization(payload, organizationToUpdate, list);
  };

  return {
    list,
    userList,
    postUpdate,
  };
};
