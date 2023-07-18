import { faker } from "@faker-js/faker";
import { ThumbnailDetailField } from "@/services/api/models/Image";

const build = (): ThumbnailDetailField => {
  return {
    filename: faker.lorem.words(),
    width: 128,
    height: 128,
    src: faker.image.urlLoremFlickr({ category: "abstract" }),
    size: 837,
  };
};

export function ThumbnailDetailFactory(): ThumbnailDetailField;
export function ThumbnailDetailFactory(count: number): ThumbnailDetailField[];
export function ThumbnailDetailFactory(
  count?: number,
): ThumbnailDetailField | ThumbnailDetailField[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
