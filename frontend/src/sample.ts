// 처음 온 사람은 PDF를 올려 보지 않는다. 내 입력이 없을 때 '명세서'·'비교 결과' 탭은
// /samples의 예시 명세서(가상, 2026년 8월 정정 전·후 — 식대 50,000 → 70,000)로 채워 보여 준다.
import type { CompareRouteState, RowInput } from './store/types';
import { createEmptyRow } from './actions';

const BEFORE: Array<[string, number]> = [
  ['기본급', 2299000],
  ['연장근로수당', 165000],
  ['식대', 50000],
  ['국민연금', 100000],
  ['건강보험', 80000],
  ['장기요양보험', 10000],
  ['고용보험', 22000],
  ['소득세', 29000],
  ['지방소득세', 3000],
];
const AFTER: Array<[string, number]> = BEFORE.map(([label, amount]) => [label, label === '식대' ? 70000 : amount]);

// 업로드한 명세서와 같은 모양(항목 이름이 key). 비교 엔진은 확인된 짝으로만 대응시키므로 같은 이름끼리 짝을 지어 둔다.
const rows = (prefix: string, items: Array<[string, number]>): RowInput[] =>
  items.map(([label, amount], idx) => ({ ...createEmptyRow(prefix, idx + 1), key: label, label, amount: String(amount) }));

export function sampleRoute(): CompareRouteState {
  const before = rows('b', BEFORE);
  const after = rows('a', AFTER);
  return {
    employmentKey: '새봄정밀 (가상)',
    periodStart: '2026-08-01',
    periodEnd: '2026-08-31',
    before,
    after,
    mappings: before.map((b, i) => ({ beforeId: b.id, afterId: after[i].id })),
  };
}

/** 아직 아무것도 입력하지 않은 상태: 예시로 채워도 사용자 입력을 덮지 않는다. */
export function isPristine(route: CompareRouteState): boolean {
  const empty = (r: RowInput) => !r.key && !r.label && !r.amount && !r.minutes && !r.rate && !r.text;
  return !route.employmentKey && !route.periodStart && !route.periodEnd && route.mappings.length === 0 && [...route.before, ...route.after].every(empty);
}
