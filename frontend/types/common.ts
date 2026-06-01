export type ListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
};
