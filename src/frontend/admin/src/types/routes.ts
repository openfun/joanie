export interface EntityRoutesPaths {
  getAll: (params?: string) => string;
  get: (id: string, params?: string) => string;
  create: string;
  update: (id: string) => string;
  delete: (id: string) => string;
}
