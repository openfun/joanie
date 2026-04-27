import { useQuery } from "@tanstack/react-query";
import { WaffleRepository } from "@/services/repositories/waffle/WaffleRepository";

export const useWaffle = () => {
  return useQuery({
    queryKey: ["waffle"],
    staleTime: Infinity,
    gcTime: Infinity,
    queryFn: async () => WaffleRepository.getStatus(),
  });
};

export const useWaffleSwitch = (name: string): boolean => {
  const { data } = useWaffle();
  return data?.switches?.[name]?.is_active ?? false;
};
