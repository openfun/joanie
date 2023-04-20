import { useRouter } from "next/router";
import { useEffect } from "react";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function Index() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.courses.root) {
      push(PATH_ADMIN.courses.list);
    }
  }, [pathname]);

  return null;
}
