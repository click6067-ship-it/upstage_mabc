export interface FieldValue {
  amountKrw?: number | null;
  minutes?: number | null;
  rateKrw?: number | null;
  text?: string | null;
}

export interface SourceLocator {
  page?: number | null;
  itemId?: string | null;
  excerpt?: string | null;
}

export interface SourceRef {
  sourceId: string;
  locator: SourceLocator;
}

export interface Item {
  id: string;
  key?: string | null;
  label?: string | null;
  position?: number | null;
  fields: FieldValue;
  sourceRefs: SourceRef[];
}

export interface DocumentPayload {
  documentId: string;
  employmentKey: string;
  period: { start: string; end: string };
  revisionKey: string;
  sections: Array<{ key: string; items: Item[] }>;
}

export interface ConfirmedMapping {
  beforeItemId: string;
  afterItemId: string;
}

export interface ComparePayload {
  mode: string;
  before: DocumentPayload;
  after: DocumentPayload;
  confirmedMappings: ConfirmedMapping[];
}

export interface CompareRequest {
  schemaVersion: 1;
  requestId: string;
  versionKey: string;
  payload: ComparePayload;
}

export interface CompareResponse {
  requestId: string;
  versionKey: string;
  engineVersion: string;
  data: {
    comparisonKind: string;
    sameEmployment: boolean;
    samePeriod: boolean;
    summary: Record<string, unknown>;
    itemChanges: Array<ItemChangeResult>;
    warnings: string[];
  };
  warnings: string[];
}

export interface ItemChangeResult {
  contentKind: string;
  moved: boolean;
  beforeItemId?: string | null;
  afterItemId?: string | null;
  beforeFields?: FieldValue | null;
  afterFields?: FieldValue | null;
  beforeSourceRefs?: SourceRef[] | null;
  afterSourceRefs?: SourceRef[] | null;
  changedFields: string[];
  reasonCode?: string | null;
}

export interface ErrorBody {
  requestId: string;
  error: {
    code: string;
    messageKey: string;
    retryable: boolean;
    fieldErrors: Array<{ field: string; code: string; messageKey: string }>;
  };
}
