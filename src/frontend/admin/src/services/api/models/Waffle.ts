export type WaffleEntry = {
  is_active: boolean;
  last_modified: string;
};

export type WaffleStatus = {
  flags: Record<string, WaffleEntry>;
  switches: Record<string, WaffleEntry>;
  samples: Record<string, WaffleEntry>;
};
