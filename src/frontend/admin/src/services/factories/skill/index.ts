import { faker } from "@faker-js/faker";
import { Skill } from "@/services/api/models/Skill";

function build(): Skill {
  return {
    id: faker.string.uuid(),
    title: faker.lorem.words({ min: 1, max: 3 }),
  };
}

export function SkillFactory(): Skill;
export function SkillFactory(count: number): Skill[];
export function SkillFactory(count?: number): Skill | Skill[] {
  if (count) return [...Array(count)].map(build);
  return build();
}
