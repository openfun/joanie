import process from "process";

export const isTestEnv = (): boolean => {
  return process.env.NEXT_PUBLIC_API_SOURCE === "test";
};
