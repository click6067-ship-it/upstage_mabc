import { describe, it, expect } from 'vitest';
import { itemFromInput, mappingFromPair, buildComparePayload } from './api/compare';
import { ItemChangeResult, type FieldValue, type SourceRef } from './api/types';
import { CompareResult } from './store/types';
import {
  createEmptyRow,
  applyRowPatch,
  addRowToList,
  removeRowFromList,
  addMapping,
  removeMappingsForRow,
  splitMappings,
  formatAmount,
  formatLabel,
  formatDetails,
  formatSourceText,
} from './actions';

describe('frontend compare models', () => {
  it('builds a v1 revision request with mapped before/after ids', () => {
    const beforeInput = [createEmptyRow('b', 1)];
    const afterInput = [createEmptyRow('a', 1)];
    const before = beforeInput.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const after = afterInput.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const mapping = mappingFromPair(before[0].id, after[0].id);
    const req = buildComparePayload('job', '2026-09-01', '2026-09-30', before, after, [mapping], 'v1', crypto.randomUUID());

    expect(req.schemaVersion).toBe(1);
    expect(req.requestId).toBeDefined();
    expect(req.requestId.length).toBe(36);
    expect(req.versionKey).toBe('v1');
    expect(req.payload.mode).toBe('revision');
    expect(req.payload.confirmedMappings).toEqual([mapping]);
  });

  it('keeps blank sourceId out of sourceRefs', () => {
    const emptyRow = createEmptyRow('b', 1);
    const row = applyRowPatch(emptyRow, { key: '식대', amount: '60000', sourceId: '', sourcePage: '', sourceExcerpt: '' });
    const item = itemFromInput(row, 1, 'after');
    expect(item.sourceRefs).toHaveLength(0);
  });

  it('parses a number into fields and leaves blanks untouched', () => {
    const emptyRow = createEmptyRow('a', 1);
    const row = applyRowPatch(emptyRow, { key: '식대', amount: '70000', minutes: '', rate: '', text: '정정 식대', sourceId: '정정자료', sourcePage: '2', sourceExcerpt: '70000원' });
    const item = itemFromInput(row, 1, 'after');
    expect((item.fields as Record<string, unknown>).amountKrw).toBe(70000);
    expect(item.sourceRefs).toHaveLength(1);
    expect(item.sourceRefs[0].sourceId).toBe('정정자료');
  });

  it('distinguishes korean 2-item ids with different keys', () => {
    const emptyRow1 = createEmptyRow('b', 1);
    const row1 = applyRowPatch(emptyRow1, { key: '식대', label: '월 식대', amount: '50000' });
    const emptyRow2 = createEmptyRow('b', 2);
    const row2 = applyRowPatch(emptyRow2, { key: '교통비', label: '월 교통비', amount: '30000' });
    const item1 = itemFromInput(row1, 1, 'before');
    const item2 = itemFromInput(row2, 2, 'before');
    expect(item1.id).not.toBe(item2.id);
    expect(item1.key).toBe('식대');
    expect(item2.key).toBe('교통비');
    expect(item1.id).toMatch(/^[0-9a-f-]{36}$/i);
    expect(item2.id).toMatch(/^[0-9a-f-]{36}$/i);
    expect(item1.id).toBe(row1.id);
    expect(item2.id).toBe(row2.id);
  });

  it('preserves id when label is modified', () => {
    const emptyRow = createEmptyRow('a', 1);
    const row1 = applyRowPatch(emptyRow, { key: '식대', label: '월 식대', amount: '50000' });
    const item1 = itemFromInput(row1, 1, 'after');
    const row2 = applyRowPatch(row1, { label: '수정 식대' });
    const item2 = itemFromInput(row2, 1, 'after');
    expect(item1.id).toBe(item2.id);
    expect(item2.label).toBe('수정 식대');
    expect(item2.key).toBe('식대');
  });

  it('avoids duplicate id after delete middle row and add new row', () => {
    const list = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000' }),
      applyRowPatch(createEmptyRow('b', 2), { key: '교통비', label: '월 교통비', amount: '30000' }),
      applyRowPatch(createEmptyRow('b', 3), { key: '교통비', label: '월 교통비', amount: '30000' }),
    ];
    const removed = removeRowFromList(list, 1);
    const added = addRowToList(removed, applyRowPatch(createEmptyRow('b', 3), { key: '식대', label: '월 식대', amount: '60000' }));
    const ids = added.map(r => r.id);
    expect(ids).toHaveLength(3);
    expect(new Set(ids).size).toBe(3);
    added.forEach((r, idx) => {
      const item = itemFromInput(r, idx + 1, 'before');
      expect(item.id).toBe(r.id);
    });
  });

  it('enforces 1:1 mapping and releases pair on empty afterId', () => {
    let mappings = addMapping([], 'b-1', 'a-1');
    expect(mappings).toEqual([{ beforeId: 'b-1', afterId: 'a-1' }]);
    mappings = addMapping(mappings, 'b-2', 'a-1');
    expect(mappings).toHaveLength(1);
    expect(mappings[0].beforeId).toBe('b-2');
    mappings = addMapping(mappings, 'b-2', '');
    expect(mappings).toHaveLength(0);
    mappings = addMapping([], 'b-3', 'a-2');
    mappings = addMapping(mappings, 'b-4', 'a-3');
    expect(mappings).toHaveLength(2);
    mappings = removeMappingsForRow(mappings, 'a-2');
    expect(mappings).toHaveLength(1);
    expect(mappings[0].beforeId).toBe('b-4');
  });

  it('builds payload with 1:1 mappings only', () => {
    const beforeList = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000' }),
      applyRowPatch(createEmptyRow('b', 2), { key: '교통비', label: '월 교통비', amount: '30000' }),
    ];
    const afterList = [
      applyRowPatch(createEmptyRow('a', 1), { key: '식대', label: '월 식대', amount: '60000' }),
      applyRowPatch(createEmptyRow('a', 2), { key: '교통비', label: '월 교통비', amount: '20000' }),
    ];
    const mappings = addMapping(addMapping([], 'b-1', 'a-1'), 'b-2', 'a-2');
    const before = beforeList.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const after = afterList.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const payloadMappings = mappings.map(m => mappingFromPair(m.beforeId, m.afterId));
    const req = buildComparePayload('job', '2026-09-01', '2026-09-30', before, after, payloadMappings, 'v1', crypto.randomUUID());
    expect(req.payload.confirmedMappings).toHaveLength(2);
    expect(req.payload.confirmedMappings).toEqual(payloadMappings);
  });

  it('reports error for invalid mappings without filtering them from input', () => {
    const beforeList = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000' }),
    ];
    const afterList = [
      applyRowPatch(createEmptyRow('a', 1), { key: '교통비', label: '월 교통비', amount: '30000' }),
      applyRowPatch(createEmptyRow('a', 2), { key: '식대', label: '월 식대', amount: '60000' }),
    ];
    const allMappings = [
      { beforeId: beforeList[0].id, afterId: afterList[0].id },
      { beforeId: beforeList[0].id, afterId: afterList[1].id },
    ];
    const beforeItems = beforeList.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = afterList.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const { valid, invalid } = splitMappings(allMappings, beforeItems, afterItems);
    expect(invalid).toHaveLength(1);
    expect(valid).toHaveLength(1);
    const beforeId = beforeList[0].id;
    const afterId = afterList[1].id;
    expect(beforeItems.find(b => b.id === beforeId)).toBeDefined();
    expect(afterItems.find(a => a.id === afterId)).toBeDefined();
    expect(beforeItems).toHaveLength(beforeList.length);
    expect(afterItems).toHaveLength(afterList.length);
  });

  it('splitMappings filters duplicate beforeId mappings as invalid', () => {
    const before = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000' }),
    ];
    const after = [
      applyRowPatch(createEmptyRow('a', 1), { key: '식대', label: '월 식대', amount: '60000' }),
      applyRowPatch(createEmptyRow('a', 2), { key: '교통비', label: '월 교통비', amount: '20000' }),
    ];
    const mappings = [
      { beforeId: before[0].id, afterId: after[0].id },
      { beforeId: before[0].id, afterId: after[1].id },
    ];
    const beforeItems = before.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = after.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const { valid, invalid } = splitMappings(mappings, beforeItems, afterItems);
    expect(invalid).toHaveLength(1);
    expect(valid).toHaveLength(1);
    expect(valid[0].beforeItemId).toBe(before[0].id);
    expect(valid[0].afterItemId).toBe(after[0].id);
  });

  it('splitMappings rejects mappings referencing deleted rows', () => {
    const before = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000' }),
      applyRowPatch(createEmptyRow('b', 2), { key: '교통비', label: '월 교통비', amount: '30000' }),
    ];
    const after = [
      applyRowPatch(createEmptyRow('a', 1), { key: '식대', label: '월 식대', amount: '60000' }),
    ];
    const mappings = [
      { beforeId: before[0].id, afterId: after[0].id },
      { beforeId: before[1].id, afterId: after[0].id },
    ];
    const beforeItems = before.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = after.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const { valid, invalid } = splitMappings(mappings, beforeItems, afterItems);
    expect(invalid).toHaveLength(1);
    expect(valid).toHaveLength(1);
    expect(valid[0].beforeItemId).toBe(before[0].id);
    expect(valid[0].afterItemId).toBe(after[0].id);
    expect(invalid[0]).toContain(before[1].id);
  });

  it('Formatted result shows mapped item amounts from CompareResponse.itemChanges', () => {
    const beforeList = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000', sourceId: '9월 명세서', sourcePage: '1', sourceExcerpt: '식대 50000원' }),
    ];
    const afterList = [
      applyRowPatch(createEmptyRow('a', 1), { key: '식대', label: '월 식대', amount: '60000', sourceId: '정정 명세서', sourcePage: '1', sourceExcerpt: '식대 60000원' }),
    ];
    const mappings = addMapping([], beforeList[0].id, afterList[0].id);
    const beforeItems = beforeList.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = afterList.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const { valid } = splitMappings(mappings, beforeItems, afterItems);
    expect(valid).toHaveLength(1);
    const beforeFields = beforeItems[0].fields;
    const afterFields = afterItems[0].fields;
    expect((beforeFields as Record<string, unknown>).amountKrw).toBe(50000);
    expect((afterFields as Record<string, unknown>).amountKrw).toBe(60000);
    expect(formatAmount(beforeFields)).toBe('50,000원');
    expect(formatAmount(afterFields)).toBe('60,000원');
    expect(formatLabel(beforeFields)).toBe('');
    expect(formatLabel(afterFields)).toBe('');
    expect(formatDetails(beforeFields)).toBe('');
    expect(formatDetails(afterFields)).toBe('');
  });

  it('Render helpers produce aligned labels and sources for mapped items', () => {
    const beforeList = [
      applyRowPatch(createEmptyRow('b', 1), { key: '식대', label: '월 식대', amount: '50000', text: '식대', sourceId: '명세서', sourcePage: '1', sourceExcerpt: '50000원' }),
    ];
    const afterList = [
      applyRowPatch(createEmptyRow('a', 1), { key: '식대', label: '월 식대', amount: '60000', text: '정정 식대', sourceId: '정정자료', sourcePage: '2', sourceExcerpt: '60000원' }),
    ];
    const beforeItems = beforeList.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = afterList.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const beforeFields = beforeItems[0].fields;
    const afterFields = afterItems[0].fields;
    expect(formatAmount(beforeFields)).toBe('50,000원');
    expect(formatAmount(afterFields)).toBe('60,000원');
    expect(formatLabel(beforeFields)).toBe('식대');
    expect(formatLabel(afterFields)).toBe('정정 식대');
    expect(formatDetails(beforeFields)).toBe('표기: 식대');
    expect(formatDetails(afterFields)).toBe('표기: 정정 식대');
    expect(formatSourceText(beforeItems[0].sourceRefs)).toBe('명세서 p.1 “50000원”');
    expect(formatSourceText(afterItems[0].sourceRefs)).toBe('정정자료 p.2 “60000원”');
  });
});
