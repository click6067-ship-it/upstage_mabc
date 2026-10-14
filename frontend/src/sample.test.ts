import { describe, it, expect } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { buildComparePayload, itemFromInput } from './api/compare';
import { createEmptyRow, splitMappings } from './actions';
import BottomNav from './BottomNav';
import { isPristine, sampleRoute } from './sample';

describe('first visit: every bottom tab works, with the example payslips', () => {
  it('no tab is disabled', () => {
    const html = renderToStaticMarkup(createElement(BottomNav, { activeTab: 'home', onTabChange: () => {} }));
    expect(html.match(/<button/g)).toHaveLength(4);
    expect(html).not.toContain('disabled');
  });

  it('the example is the two sample PDFs: same 9 items, only 식대 changes 50,000 → 70,000', () => {
    const r = sampleRoute();
    expect([r.employmentKey, r.periodStart, r.periodEnd]).toEqual(['새봄정밀 (가상)', '2026-08-01', '2026-08-31']);
    expect(r.before.map((x) => x.key)).toEqual(r.after.map((x) => x.key));
    expect(new Set(r.before.map((x) => x.key)).size).toBe(9);
    const changed = r.before.filter((b, i) => b.amount !== r.after[i].amount).map((b, i) => [b.key, b.amount]);
    expect(changed).toEqual([['식대', '50000']]);
    expect(r.after.find((x) => x.key === '식대')!.amount).toBe('70000');
    // Each item is paired with its namesake, as a user would confirm under "같은 항목인지 확인".
    expect(r.mappings).toEqual(r.before.map((b, i) => ({ beforeId: b.id, afterId: r.after[i].id })));
  });

  it('the example builds a valid compare request (amounts in won, one item per row)', () => {
    const r = sampleRoute();
    const before = r.before.map((x, i) => itemFromInput(x, i + 1, 'before'));
    const after = r.after.map((x, i) => itemFromInput(x, i + 1, 'after'));
    const { valid, invalid } = splitMappings(r.mappings, before, after);
    expect([valid.length, invalid.length]).toEqual([9, 0]);
    const req = buildComparePayload(r.employmentKey, r.periodStart, r.periodEnd, before, after, valid, 'v1', crypto.randomUUID());
    const items = (side: 'before' | 'after') => req.payload[side].sections.flatMap((s) => s.items);
    expect(items('before').map((i) => i.fields.amountKrw)).toEqual([2299000, 165000, 50000, 100000, 80000, 10000, 22000, 29000, 3000]);
    expect(items('after').find((i) => i.key === '식대')!.fields.amountKrw).toBe(70000);
  });

  it('the example never covers what the user typed', () => {
    const empty = { employmentKey: '', periodStart: '', periodEnd: '', before: [createEmptyRow('b', 1)], after: [createEmptyRow('a', 1)], mappings: [] };
    expect(isPristine(empty)).toBe(true);
    expect(isPristine({ ...empty, before: [{ ...empty.before[0], amount: '1000' }] })).toBe(false);
    expect(isPristine({ ...empty, periodStart: '2026-09-01' })).toBe(false);
    expect(isPristine(sampleRoute())).toBe(false);
  });
});
