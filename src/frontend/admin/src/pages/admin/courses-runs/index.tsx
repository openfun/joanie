import { useRouter } from "next/router";
import { useEffect } from "react";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function Index() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.courses_run.root) {
      push(PATH_ADMIN.courses_run.list);
    }
  }, [pathname]);

  return null;
}
