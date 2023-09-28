export const removeEOL = (str?: string): string => {
  if (!str) {
    return "";
  }
  return str?.replace(/(\r)/gm, "");
};
