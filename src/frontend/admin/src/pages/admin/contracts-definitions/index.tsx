import { useRouter } from "next/router";
import { useEffect } from "react";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function ContractDefinitions() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.contract_definition.root) {
      push(PATH_ADMIN.contract_definition.list);
    }
  }, [pathname]);

  return null;
}
