import { useEffect } from "react";
import { useRouter } from "next/router";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function Index() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.organizations.root) {
      push(PATH_ADMIN.organizations.list);
    }
  }, [pathname]);

  return null;
}
