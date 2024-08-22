export const randomNumber = (max: number): number => {
  return Math.floor(Math.random() * max) + 1;
};

export const toDigitString = (value: number) => {
  if (value >= 10) {
    return value.toString();
  }

  return `0${value}`;
};
