import { useQuery } from "@tanstack/react-query";
import { CoursesRunsRepository } from "@/services/repositories/courses-runs/CoursesRunsRepository";

export const useAllLanguages = () => {
  const languages = useQuery(
    ["allLanguages"],
    async () => {
      const response = await CoursesRunsRepository.getAllLanguages();
      return response.actions.POST.languages.choices;
    },
    { staleTime: Infinity, cacheTime: Infinity }
  );

  return languages?.data ?? undefined;
};
