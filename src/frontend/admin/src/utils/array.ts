export const mergeArrayUnique = <T>(
  firstArray: T[],
  secondArray: T[],
  predicate = (first: T, second: T) => first === second,
) => {
  const result = [...firstArray];
  secondArray.forEach((bItem) =>
    result.some((cItem) => predicate(bItem, cItem)) ? null : result.push(bItem),
  );
  return result;
};
