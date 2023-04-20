export type ImageDetailField = {
  filename: string;
  height: number;
  width: number;
  src: string;
  size: number;
};

export type ThumbnailDetailField = ImageDetailField & {
  srcset?: string;
};
