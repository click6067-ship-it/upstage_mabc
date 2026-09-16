import type { PaycheckInput, ReceivedPayment, PaycheckResult, PaycheckErrors } from './types';

const maxAmount = 999999999;

type AmountParseResult = number | { raw: string; error: string };

export function parseAmount(raw: string): AmountParseResult {
  if (raw.trim() === '') return { raw, error: '빈칸은 0으로 채우지 않아요' };
  if (!/^-?\d+$/.test(raw.trim())) return { raw, error: '숫자만 입력해 주세요' };
  const v = Number(raw.trim());
  if (!Number.isInteger(v)) return { raw, error: '정수만 입력해 주세요' };
  if (v < 0) return { raw, error: '0 이상이어야 해요' };
  if (v > maxAmount) return { raw, error: '금액에 들어갈 수 있는 최대 범위보다 커요' };
  return v;
}

export function parsePositiveAmount(raw: string): AmountParseResult {
  const r = parseAmount(raw);
  if (typeof r === 'number') {
    if (r === 0) return { raw, error: '실제로 받은 금액은 0원일 수 없어요' };
    return r;
  }
  return r;
}

// ── 날짜 파싱 ──

interface ParsedDate {
  year: number;
  month: number;
  day: number;
  valid: boolean;
  error?: string;
}

function parseISODate(raw: string): ParsedDate {
  if (!raw.trim()) return { year: 0, month: 0, day: 0, valid: false, error: '날짜가 비어 있어요' };
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw.trim());
  if (!m) return { year: 0, month: 0, day: 0, valid: false, error: '날짜는 YYYY-MM-DD 형식이어야 해요' };
  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (!Number.isInteger(year) || year < 1 || year > 9999 || !Number.isInteger(month) || month < 1 || month > 12 || !Number.isInteger(day) || day < 1 || day > 31) {
    return { year: 0, month: 0, day: 0, valid: false, error: '날짜가 올바르지 않아요' };
  }
  const d = new Date(year, month - 1, day);
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) {
    return { year: 0, month: 0, day: 0, valid: false, error: '날짜가 올바르지 않아요' };
  }
  return { year, month, day, valid: true };
}

export function isValidDate(raw: string): boolean {
  return parseISODate(raw).valid;
}

export function getDateSortKey(raw: string): string {
  return raw.trim().replace(/-/g, '');
}

export interface DateSpan {
  startSort: string;
  endSort: string;
  unknown: boolean;
}

export function parsePeriod(periodStart: string, periodEnd: string): DateSpan {
  const startParsed = parseISODate(periodStart);
  const endParsed = parseISODate(periodEnd);
  if (!startParsed.valid || !endParsed.valid) {
    return {
      startSort: periodStart.trim().replace(/-/g, ''),
      endSort: periodEnd.trim().replace(/-/g, ''),
      unknown: true,
    };
  }
  const startSort = `${startParsed.year}${String(startParsed.month).padStart(2, '0')}${String(startParsed.day).padStart(2, '0')}`;
  const endSort = `${endParsed.year}${String(endParsed.month).padStart(2, '0')}${String(endParsed.day).padStart(2, '0')}`;
  return { startSort, endSort, unknown: startSort > endSort ? true : false };
}

// ── 지급기록 파싱/검증 ──

interface ParsedPayment {
  payment: ReceivedPayment;
  parsedAmount: number | null;
  parsedDate: ParsedDate | null;
  amountError?: string;
  dateError?: string;
}

export function parseReceivedPayments(receivedPayments: ReceivedPayment[]): {
  entries: ParsedPayment[];
  errors: Record<string, string>;
  duplicateByAmountDate: { date: string; amount: number; ids: string[] }[];
  duplicateById: { id: string; count: number }[];
} {
  const entries: ParsedPayment[] = [];
  const errors: Record<string, string> = {};
  const dateAmountMap = new Map<string, { date: string; amount: number; ids: string[]; count: number }>();
  const idCount: Record<string, number> = {};

  for (const p of receivedPayments) {
    idCount[p.id] = (idCount[p.id] || 0) + 1;
  }
  const duplicateById = Object.entries(idCount)
    .filter(([, count]) => count > 1)
    .map(([id, count]) => ({ id, count }));

  const duplicateIdSet = new Set(duplicateById.map(d => d.id));

  for (const p of receivedPayments) {
    const pd = parseISODate(p.receivedDate);
    const amountRes = parsePositiveAmount(p.receivedAmount);
    const parsedAmount = typeof amountRes === 'number' ? amountRes : null;
    const parsedDate: ParsedDate | null = pd.valid ? pd : null;
    let amountError: string | undefined;
    let dateError: string | undefined;

    if (typeof amountRes !== 'number') amountError = amountRes.error;
    if (!pd.valid) dateError = pd.error;

    entries.push({ payment: p, parsedAmount, parsedDate, amountError, dateError });

    // ID 중복 지급은 dateAmountMap에 넣지 않음 (합산 후보에서 제외)
    if (duplicateIdSet.has(p.id)) continue;

    if (parsedAmount !== null && parsedDate !== null) {
      const dateStr = `${pd.year}-${String(pd.month).padStart(2, '0')}-${String(pd.day).padStart(2, '0')}`;
      const key = `${dateStr}|${parsedAmount}`;
      const existing = dateAmountMap.get(key);
      if (existing) {
        dateAmountMap.set(key, { ...existing, ids: [...existing.ids, p.id], count: existing.count + 1 });
      } else {
        dateAmountMap.set(key, { date: dateStr, amount: parsedAmount, ids: [p.id], count: 1 });
      }
    }
  }

  const duplicateByAmountDate = [...dateAmountMap.values()]
    .filter(e => e.count > 1)
    .map(e => ({ date: e.date, amount: e.amount, ids: e.ids }));

  for (const e of entries) {
    const parts: string[] = [];
    if (e.amountError) parts.push(e.amountError);
    if (e.dateError) parts.push(e.dateError);
    if (parts.length > 0) {
      errors[e.payment.id] = parts.join(' ');
    }
  }

  for (const d of duplicateById) {
    if (!errors[d.id]) {
      errors[d.id] = '같은 ID의 지급기록이 여러 번 들어왔어요';
    }
  }

  return { entries, errors, duplicateByAmountDate, duplicateById };
}

// ── 핵심 계산 ──

export function calculatePaycheck(input: PaycheckInput): PaycheckResult {
  const errors: PaycheckErrors = {};
  const warnings: string[] = [];
  const duplicateBlocked: string[] = [];

  // ── 입력 검증 ──
  const employmentKeyEmpty = !input.employmentKey.trim();
  const periodStartEmpty = !input.periodStart.trim();
  const periodEndEmpty = !input.periodEnd.trim();

  if (employmentKeyEmpty) errors.employmentKey = '일자리를 적어 주세요';
  if (periodStartEmpty) errors.periodStart = '시작일 입력이 필요해요';
  if (periodEndEmpty) errors.periodEnd = '종료일 입력이 필요해요';

  const periodSpan = parsePeriod(input.periodStart, input.periodEnd);
  const unknownPeriod = periodSpan.unknown;

  if (!periodEndEmpty && unknownPeriod) {
    errors.periodEnd = '종료일이 시작일보다 빠를 수 없어요';
  }

  // 명시적 미수령 진술 검증: 진술은 있지만 내역이 하나도 없으면 별도 검증(경고 수준)
  const hasExplicitNoReceiptOnly = input.explicitNoReceipt && input.receivedPayments.length === 0 && input.statementAmount.trim() !== '';

  const statementRes = parseAmount(input.statementAmount);
  const statementAmount = typeof statementRes === 'number' ? statementRes : null;
  if (input.statementAmount.trim() !== '' && typeof statementRes !== 'number') {
    errors.statementAmount = statementRes.error;
  }

  // ── 지급기록 파싱/검증 ──
  const { entries, errors: paymentErrors, duplicateByAmountDate, duplicateById } = parseReceivedPayments(input.receivedPayments);

  if (Object.keys(paymentErrors).length > 0) {
    errors.receivedPayments = paymentErrors;
  }

  const dupKeys = new Set(duplicateByAmountDate.map(d => `${d.date}|${d.amount}`));

  // ── 중복 그룹별 해결 상태 검사 ──
  // resolvedDuplicate는 지급의 id/날짜/금액/revision이 현재 기록과 전부 일치할 때만 유효하다.
  // 중복 그룹(같은 날짜·금액, ID 중복 제외)의 모든 기록이 유효한 resolvedDuplicate를 가져야만
  // 그 그룹이 해결된 것으로 보고 합산 대상에 포함한다.
  // 한 그룹을 풀었다고 다른 미해결 그룹까지 계산하지 않는다.

  const resolvedGroupKeys = new Set<string>();

  for (const d of duplicateByAmountDate) {
    const groupKey = `${d.date}|${d.amount}`;
    const groupPayments = entries.filter(e => {
      if (e.parsedAmount === null || e.parsedDate === null) return false;
      if (duplicateById.some(db => db.id === e.payment.id)) return false;
      const eDate = `${e.parsedDate.year}-${String(e.parsedDate.month).padStart(2, '0')}-${String(e.parsedDate.day).padStart(2, '0')}`;
      return eDate === d.date && e.parsedAmount === d.amount;
    });

    if (groupPayments.length === 0) continue;

    const allValid = groupPayments.every(e => {
      const rd = input.resolvedDuplicates.find(r => r.id === e.payment.id);
      if (!rd) return false;
      if (rd.receivedDate !== e.payment.receivedDate.trim()) return false;
      if (rd.receivedAmount !== e.parsedAmount) return false;
      if (rd.revision !== e.payment.revision) return false;
      return true;
    });

    if (allValid) resolvedGroupKeys.add(groupKey);
  }

  // ── 미해결 중복 후보 문자열 (해결된 그룹은 제외) ──
  const duplicateCandidates: string[] = duplicateByAmountDate
    .filter(d => !resolvedGroupKeys.has(`${d.date}|${d.amount}`))
    .map(d => {
      const idList = d.ids.map(id => `'${id}'`).join(', ');
      return `${d.date} (${idList})`;
    });

  // ── confirmed 합산 ──
  // 확인 표시 자체는 합산 가능 여부와 별개로 기록한다(충돌 Detection용).
  let hasAnyConfirmed = false;
  for (const e of entries) {
    if (e.payment.confirmation === 'confirmed' && e.parsedAmount !== null && e.parsedDate !== null) {
      hasAnyConfirmed = true;
    }
  }

  let confirmedSum = 0;
  for (const e of entries) {
    if (e.payment.confirmation === 'confirmed' && e.parsedAmount !== null && e.parsedDate !== null) {
      const isDupId = duplicateById.some(d => d.id === e.payment.id);
      if (isDupId) continue;
      const key = `${e.parsedDate.year}-${String(e.parsedDate.month).padStart(2, '0')}-${String(e.parsedDate.day).padStart(2, '0')}|${e.parsedAmount}`;
      if (dupKeys.has(key) && !resolvedGroupKeys.has(key)) continue;
      confirmedSum += e.parsedAmount;
    }
  }

  // ── receivedTotal 결정 ──
  // 미수령 진술과 확인된 입금이 충돌하면 차이 계산은 보류하되,
  // 실제 확인된 입금액이 있으면 receivedTotal 자체는 판단 가능한 값으로 유지한다.
  // 차이/계산 완결 여부는 difference와 inputHeld에서 함께 판단한다.
  const hasGoneReceiptConflict = input.explicitNoReceipt && hasAnyConfirmed;

  // 충돌 안내는 다른 오류와 무관하게 항상 보여준다.
  if (hasGoneReceiptConflict) {
    warnings.push('명시적 미수령 진술과 확인된 입금이 함께 있어 계산을 보류해요 — 진술을 다시 확인해 주세요');
  }

  const hasStatementNoPayments = input.explicitNoReceipt && input.receivedPayments.length === 0 && input.statementAmount.trim() !== '';

  const hasAnyError =
    employmentKeyEmpty ||
    periodStartEmpty ||
    periodEndEmpty ||
    unknownPeriod ||
    (input.statementAmount.trim() !== '' && typeof statementRes !== 'number') ||
    Object.keys(paymentErrors).length > 0 ||
    duplicateById.length > 0 ||
    (duplicateByAmountDate.length > 0 && duplicateById.length === 0 && resolvedGroupKeys.size === 0) ||
    hasGoneReceiptConflict;

  let receivedTotal: number | null = null;

  if (hasAnyError && !hasGoneReceiptConflict) {
    receivedTotal = null;
  } else if (hasStatementNoPayments) {
    receivedTotal = 0;
    warnings.push('전혀 못 받았다는 진술을 직접 확인했어요 — 수령액 0원으로 계산해요');
  } else if (duplicateByAmountDate.length > 0 && duplicateById.length === 0 && resolvedGroupKeys.size === 0) {
    // 미해결 중복 후보: 합산 보류
    receivedTotal = null;
    warnings.push('같은 날짜·금액의 다른 지급기록이 있어요 — 별도 지급이면 둘 다 합산해요');
  } else if (input.explicitNoReceipt && !hasAnyConfirmed) {
    receivedTotal = 0;
  } else if (confirmedSum > 0) {
    receivedTotal = confirmedSum;
  } else {
    receivedTotal = null;
  }

  // ── 차이 계산: 오류/보류 조건 하나라도 있으면 null ──
  let difference: number | null = null;
  if (!hasAnyError && statementAmount !== null && receivedTotal !== null) {
    difference = statementAmount - receivedTotal;
  }

  // ── 경고 ──
  if (unknownPeriod) warnings.push('급여기간이 비어 있어서 귀속 계산은 보류해요');
  if (duplicateByAmountDate.length > 0 && duplicateById.length === 0 && resolvedGroupKeys.size === 0) {
    // 이미 위에서 push
  }
  if (duplicateById.length > 0) {
    warnings.push('ID가 겹쳐 합산에서 제외한 지급기록이 있어요');
  }

  for (const [id, msg] of Object.entries(errors.receivedPayments ?? {})) {
    warnings.push(`지급기록 입력이 올바르지 않아요: ${msg}`);
  }
  if (input.statementAmount.trim() !== '' && typeof statementRes !== 'number') {
    warnings.push(`명세서 금액 입력이 올바르지 않아요: ${(statementRes as { error: string }).error}`);
  }

  const inputHeld = !!(employmentKeyEmpty || periodStartEmpty || periodEndEmpty ||
    unknownPeriod ||
    (input.statementAmount.trim() !== '' && typeof statementRes !== 'number') ||
    Object.keys(errors.receivedPayments ?? {}).length > 0 ||
    duplicateById.length > 0 ||
    (duplicateByAmountDate.length > 0 && duplicateById.length === 0 && resolvedGroupKeys.size === 0) ||
    hasGoneReceiptConflict);

  return {
    employmentKey: input.employmentKey.trim(),
    periodStart: input.periodStart.trim() ? input.periodStart : null,
    periodEnd: input.periodEnd.trim() ? input.periodEnd : null,
    statementAmount,
    receivedTotal,
    difference,
    duplicateBlocked: duplicateBlocked,
    duplicateCandidates,
    errors,
    warnings,
    hasError: Object.keys(errors).length > 0,
    inputHeld,
    unknownPeriod,
    referenceConfirmedSum: confirmedSum,
    hasAnyConfirmed,
  };
}
