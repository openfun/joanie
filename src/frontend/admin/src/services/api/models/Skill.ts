export type Skill = {
  id: string;
  title: string;
};

export type DTOSkill = Omit<Skill, "id">;
