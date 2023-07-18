import { useQuery } from "@tanstack/react-query";
import { CoursesRunsRepository } from "@/services/repositories/courses-runs/CoursesRunsRepository";

export const useAllLanguages = () => {
  const languages = useQuery(
    ["allLanguages"],
    async () => {
      return CoursesRunsRepository.getAllLanguages();
    },
    { staleTime: Infinity, cacheTime: Infinity },
  );

  return languages?.data ?? undefined;
};
