import { useQuery } from "@tanstack/react-query";
import { CoursesRunsRepository } from "@/services/repositories/courses-runs/CoursesRunsRepository";

export const useAllLanguages = () => {
  const languages = useQuery({
    queryKey: ["allLanguages"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => {
      return CoursesRunsRepository.getAllLanguages();
    },
  });

  return languages?.data ?? undefined;
};
