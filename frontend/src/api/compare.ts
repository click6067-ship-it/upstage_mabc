import type { RowInput } from '../store/types';
import { type FieldValue, type SourceRef, type Item, type ConfirmedMapping, type CompareRequest, type DocumentPayload, type CompareResponse, type ErrorBody } from './types';

function idFromKey(key: string | null | undefined, position: number, side: 'before' | 'after'): string {
  const k = key && key.trim().length > 0 ? key.trim() : null;
  if (k) {
    return `item-${side}-${k.replace(/\s+/g, '-').replace(/[^0-9A-Za-z-]/g, '')}`;
  }
  return `item-${side}-pos-${position}`;
}

function sourceRefFromInput(sourceId: string | null | undefined, sourcePage: string | null | undefined, sourceExcerpt: string | null | undefined): SourceRef[] {
  const sid = sourceId && sourceId.trim().length > 0 ? sourceId.trim() : null;
  if (!sid) return [];
  const sp = sourcePage ?? '';
  const page = sp === '' ? null : parseInt(sp, 10);
  const ex = sourceExcerpt ?? '';
  const excerpt = ex === '' ? null : ex;
  if (page !== null && Number.isNaN(page)) return [];
  return [
    {
      sourceId: sid,
      locator: {
        page: page === null ? null : page,
        itemId: null,
        excerpt: excerpt === null ? null : excerpt,
      },
    },
  ];
}

function fieldValueFromInput(amount: string | null | undefined, minutes: string | null | undefined, rate: string | null | undefined, text: string | null | undefined): FieldValue {
  const out: Record<string, unknown> = {};
  if (amount != null && amount !== '') {
    const n = parseInt(amount, 10);
    if (!Number.isNaN(n)) out.amountKrw = n;
  }
  if (minutes != null && minutes !== '') {
    const n = parseInt(minutes, 10);
    if (!Number.isNaN(n)) out.minutes = n;
  }
  if (rate != null && rate !== '') {
    const n = parseInt(rate, 10);
    if (!Number.isNaN(n)) out.rateKrw = n;
  }
  if (text != null && text !== '') out.text = text;
  return out as FieldValue;
}

export function itemFromInput(row: RowInput, position: number, side: 'before' | 'after'): Item {
  return {
    id: row.id,
    key: row.key,
    label: row.label,
    position: position,
    fields: fieldValueFromInput(row.amount, row.minutes, row.rate, row.text),
    sourceRefs: sourceRefFromInput(row.sourceId, row.sourcePage, row.sourceExcerpt),
  };
}

export function mappingFromPair(beforeItemId: string, afterItemId: string): ConfirmedMapping {
  return { beforeItemId, afterItemId };
}

export function buildComparePayload(
  employmentKey: string,
  periodStart: string,
  periodEnd: string,
  beforeItems: Item[],
  afterItems: Item[],
  mappings: ConfirmedMapping[],
  versionKey = 'v1',
  requestId: string,
): CompareRequest {
  return {
    schemaVersion: 1,
    requestId,
    versionKey,
    payload: {
      mode: 'revision',
      before: makeDocument(employmentKey, periodStart, periodEnd, 'rev-before', beforeItems),
      after: makeDocument(employmentKey, periodStart, periodEnd, 'rev-after', afterItems),
      confirmedMappings: mappings,
    },
  };
}

function makeDocument(employmentKey: string, periodStart: string, periodEnd: string, revisionKey: string, items: Item[]): DocumentPayload {
  return {
    documentId: 'doc-' + revisionKey,
    employmentKey,
    period: { start: periodStart, end: periodEnd },
    revisionKey,
    sections: [{ key: '급여', items }],
  };
}

export async function postCompare(body: CompareRequest): Promise<CompareResponse | ErrorBody> {
  const res = await fetch('/api/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    keepalive: true,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '{\"requestId\":\"?\",\"error\":{\"code\":\"NETWORK\",\"messageKey\":\"NETWORK\",\"retryable\":true,\"fieldErrors\":[]}}');
    try {
      return JSON.parse(raw) as ErrorBody;
    } catch {
      return {
        requestId: '?',
        error: {
          code: 'NETWORK',
          messageKey: 'NETWORK',
          retryable: true,
          fieldErrors: [],
        },
      };
    }
  }

  const json = (await res.json()) as CompareResponse;
  return json;
}
