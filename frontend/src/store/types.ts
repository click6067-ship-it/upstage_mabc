export interface RowInput {
  id: string;
  key: string;
  label: string;
  amount: string;
  minutes: string;
  rate: string;
  text: string;
  sourceId: string;
  sourcePage: string;
  sourceExcerpt: string;
}

export interface CompareRouteState {
  employmentKey: string;
  periodStart: string;
  periodEnd: string;
  before: RowInput[];
  after: RowInput[];
  mappings: Array<{ beforeId: string; afterId: string }>;
}

export type { CompareResponse as CompareResult } from '../api/types';
export interface CompareError {
  requestId: string;
  error: {
    code: string;
    messageKey: string;
    retryable: boolean;
    fieldErrors: Array<{ field: string; code: string; messageKey: string }>;
  };
}
