import { faker } from "@faker-js/faker";
import { File } from "@/services/api/models/File";

export const createDummyFile = (): File => {
  return {
    url: faker.image.abstract(),
    name: faker.lorem.words(),
    path: "/test",
  };
};
