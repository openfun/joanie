export type Teacher = {
  id: string;
  first_name: string;
  last_name: string;
};

export type DTOTeacher = Omit<Teacher, "id">;
