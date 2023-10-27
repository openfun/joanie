import { useEffect } from "react";
import { useRouter } from "next/router";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function Index() {
  const { pathname, replace } = useRouter();

  useEffect(() => {
    replace(PATH_ADMIN.rootAdmin);
  }, [pathname]);

  return null;
}
