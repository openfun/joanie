import { useSearchParams } from "next/navigation";
import { Maybe } from "@/types/utils";

export const useFromIdSearchParams = (): Maybe<string> => {
  const searchParams = useSearchParams();
  const fromId = searchParams.get("from");
  return fromId ?? undefined;
};
