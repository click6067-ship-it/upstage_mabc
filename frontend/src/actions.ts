import { RowInput } from './store/types';
import { Item, ConfirmedMapping, FieldValue, SourceRef } from './api/types';
import { mappingFromPair } from './api/compare';

export type ActionKind = 'never-paid' | 'changed' | 'understand' | 'empty';

export function createEmptyRow(prefix: string, idx: number): RowInput {
  return {
    id: crypto.randomUUID(),
    key: '',
    label: '',
    amount: '',
    minutes: '',
    rate: '',
    text: '',
    sourceId: '',
    sourcePage: '',
    sourceExcerpt: '',
  };
}

export function applyRowPatch(row: RowInput, patch: Partial<RowInput>): RowInput {
  return { ...row, ...patch, id: row.id };
}

export function addRowToList(list: RowInput[], row: RowInput): RowInput[] {
  return [...list, row];
}

export function removeRowFromList(list: RowInput[], idx: number): RowInput[] {
  if (list.length <= 1) return list;
  return list.filter((_, i) => i !== idx);
}

export function addMapping(
  mappings: Array<{ beforeId: string; afterId: string }>,
  beforeId: string,
  afterId: string,
): Array<{ beforeId: string; afterId: string }> {
  if (afterId === '') {
    return mappings.filter(m => m.beforeId !== beforeId);
  }
  let result = mappings.filter(m => m.beforeId !== beforeId);
  result = result.filter(m => m.afterId !== afterId);
  result.push({ beforeId, afterId });
  return result;
}

export function removeMappingsForRow(
  mappings: Array<{ beforeId: string; afterId: string }>,
  rowId: string,
): Array<{ beforeId: string; afterId: string }> {
  return mappings.filter(m => m.beforeId !== rowId && m.afterId !== rowId);
}

export function splitMappings(
  mappings: Array<{ beforeId: string; afterId: string }>,
  beforeItems: Item[],
  afterItems: Item[],
): { valid: ConfirmedMapping[]; invalid: string[] } {
  const usedBeforeIds = new Set<string>();
  const usedAfterIds = new Set<string>();
  const valid: ConfirmedMapping[] = [];
  const invalid: string[] = [];

  for (const m of mappings) {
    const b = beforeItems.find(b => b.id === m.beforeId);
    const a = afterItems.find(a => a.id === m.afterId);
    if (!b || !a) {
      invalid.push(`${m.beforeId} → ${m.afterId}`);
      continue;
    }
    if (usedBeforeIds.has(m.beforeId) || usedAfterIds.has(m.afterId)) {
      invalid.push(`${m.beforeId} → ${m.afterId}`);
      continue;
    }
    usedBeforeIds.add(m.beforeId);
    usedAfterIds.add(m.afterId);
    valid.push(mappingFromPair(b.id, a.id));
  }

  return { valid, invalid };
}

export function formatAmount(fields: FieldValue | null | undefined): string {
  if (!fields || typeof fields !== 'object') return '입력 안 됨';
  const v = fields.amountKrw;
  if (v === null || v === undefined) return '입력 안 됨';
  if (typeof v === 'number') {
    if (Number.isInteger(v)) return `${v.toLocaleString()}원`;
    return `${v.toFixed(0).toLocaleString()}원`;
  }
  return String(v);
}

export function formatDetails(fields: FieldValue | null | undefined): string {
  if (!fields || typeof fields !== 'object') return '';
  const parts: string[] = [];
  const minutes = fields.minutes;
  if (minutes !== null && minutes !== undefined) parts.push(`근무 ${Number(minutes).toLocaleString()}분`);
  const rate = fields.rateKrw;
  if (rate !== null && rate !== undefined) parts.push(`시급 ${Number(rate).toLocaleString()}원`);
  const text = fields.text;
  if (typeof text === 'string' && text.trim().length > 0) parts.push(`표기: ${text}`);
  return parts.join(' · ');
}

export function formatLabel(fields: FieldValue | null | undefined): string {
  if (!fields || typeof fields !== 'object') return '';
  const t = fields.text;
  if (typeof t === 'string' && t.trim().length > 0) return t;
  return '';
}

export function formatSourceText(list: SourceRef[]): string {
  const parts = list
    .filter(s => s.sourceId)
    .map(s => {
      const loc = s.locator;
      const page = typeof loc.page === 'number' ? ` p.${loc.page}` : '';
      const excerpt = typeof loc.excerpt === 'string' && loc.excerpt.trim().length > 0 ? ` “${loc.excerpt}”` : '';
      return `${s.sourceId}${page}${excerpt}`;
    });
  return parts.join(' / ') || '자료 없음';
}
