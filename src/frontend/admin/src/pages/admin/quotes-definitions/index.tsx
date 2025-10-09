import { useRouter } from "next/router";
import { useEffect } from "react";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function QuoteDefinitions() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.quote_definition.root) {
      push(PATH_ADMIN.quote_definition.list);
    }
  }, [pathname]);

  return null;
}
