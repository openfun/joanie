import { useRouter } from "next/router";
import { useEffect } from "react";
import { PATH_ADMIN } from "@/utils/routes/path";

export default function Certificates() {
  const { pathname, push } = useRouter();

  useEffect(() => {
    if (pathname === PATH_ADMIN.certificates.root) {
      push(PATH_ADMIN.certificates.list);
    }
  }, [pathname]);

  return null;
}
