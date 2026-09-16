import { describe, it, expect } from 'vitest';
import { parseAmount, parsePositiveAmount, calculatePaycheck } from '../payroll/calculate';
import { createReceivedPayment, applyReceivedPaymentPatch } from '../payroll/types';
import type { PaycheckInput, ReceivedPayment } from '../payroll/types';

function mkPayment(patch: Partial<ReceivedPayment> = {}): ReceivedPayment {
  return createReceivedPayment(patch);
}

function input(overrides: Partial<PaycheckInput> = {}): PaycheckInput {
  return {
    employmentKey: 'JOB',
    periodStart: '2026-09-01',
    periodEnd: '2026-09-30',
    statementAmount: '2000000',
    receivedPayments: [],
    receiptCompleteness: 'unknown' as const,
    explicitNoReceipt: false,     resolvedDuplicates: [],
    
    ...overrides,
  };
}

describe('parseAmount', () => {
  it('정수는 숫자로', () => {
    expect(parseAmount('1980000')).toBe(1980000);
    expect(parseAmount('0')).toBe(0);
  });
  it('빈칸은 오류를 반환', () => {
    const r = parseAmount('') as { error: string };
    expect(r.error).toBe('빈칸은 0으로 채우지 않아요');
  });
  it('12abc는 오류', () => {
    const r = parseAmount('12abc') as { error: string };
    expect(r.error).toBe('숫자만 입력해 주세요');
  });
  it('소수는 오류', () => {
    const r = parseAmount('1980000.5') as { error: string };
    expect(r.error).toBe('숫자만 입력해 주세요');
  });
  it('범위 초과는 오류', () => {
    const r = parseAmount('1000000000') as { error: string };
    expect(r.error).toBe('금액에 들어갈 수 있는 최대 범위보다 커요');
  });
});

describe('parsePositiveAmount', () => {
  it('양수 정수는 숫자로', () => {
    expect(parsePositiveAmount('20000')).toBe(20000);
    expect(parsePositiveAmount('1980000')).toBe(1980000);
  });
  it('0은 오류', () => {
    const r = parsePositiveAmount('0') as { error: string };
    expect(r.error).toBe('실제로 받은 금액은 0원일 수 없어요');
  });
});

describe('calculatePaycheck', () => {
  it('명세서 2000000 / 확인된 지급 1980000 이면 차이 20000', () => {
    const r = calculatePaycheck(input({
      receivedPayments: [
        mkPayment({ receivedDate: '2026-09-10', receivedAmount: '1980000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.statementAmount).toBe(2000000);
    expect(r.receivedTotal).toBe(1980000);
    expect(r.difference).toBe(20000);
  });

  it('확인된 지급 20000 추가하면 차이 0', () => {
    const r = calculatePaycheck(input({
      receivedPayments: [
        mkPayment({ receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.receivedTotal).toBe(20000);
    expect(r.difference).toBe(1980000);
  });

  it('명세서 2000000 / 확인된 지급 1980000 + 추가 20000 = 차이 0', () => {
    const r = calculatePaycheck(input({
      statementAmount: '2000000',
      receivedPayments: [
        mkPayment({ receivedDate: '2026-09-10', receivedAmount: '1980000', confirmation: 'confirmed' }),
        mkPayment({ receivedDate: '2026-09-15', receivedAmount: '20000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.receivedTotal).toBe(2000000);
    expect(r.difference).toBe(0);
  });

  it('더 받았으면 음수 차이 그대로 표시', () => {
    const r = calculatePaycheck(input({
      statementAmount: '1000000',
      receivedPayments: [
        mkPayment({ receivedDate: '2026-09-10', receivedAmount: '1200000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.receivedTotal).toBe(1200000);
    expect(r.difference).toBe(-200000);
  });

  it('같은 ID 이중 합산 막음', () => {
    const r = calculatePaycheck(input({
      receivedPayments: [
        mkPayment({ id: 'dup-id', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' }),
        mkPayment({ id: 'dup-id', receivedDate: '2026-09-11', receivedAmount: '50000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.errors.receivedPayments).toBeDefined();
    expect(r.errors.receivedPayments?.['dup-id']).toContain('같은 ID');
  });

  it('같은 날짜·금액 다른 ID 미해결이면 차이 null + candidates', () => {
    const r = calculatePaycheck(input({
      receivedPayments: [
        mkPayment({ id: 'a1', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' }),
        mkPayment({ id: 'a2', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' }),
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.duplicateCandidates[0]).toContain('2026-09-10');
    expect(r.duplicateCandidates[0]).toContain("'a1'");
    expect(r.duplicateCandidates[0]).toContain("'a2'");
    expect(r.receivedTotal).toBeNull();
    expect(r.difference).toBeNull();
  });

  it('같은 날짜·금액 다른 ID라도 둘 다 확인하면 합산', () => {
    const a1 = mkPayment({ id: 'a1', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const a2 = mkPayment({ id: 'a2', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [a1, a2],
      resolvedDuplicates: [
        { id: a1.id, receivedDate: a1.receivedDate, receivedAmount: 100000, revision: a1.revision },
        { id: a2.id, receivedDate: a2.receivedDate, receivedAmount: 100000, revision: a2.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(0);
    expect(r.receivedTotal).toBe(200000);
    expect(r.difference).toBe(1800000);
  });

  it('중복 그룹 하나는 확인해도 다른 그룹 미해결이면 합산 보류', () => {
    const p1 = mkPayment({ id: 'p1', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const p2 = mkPayment({ id: 'p2', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const p3 = mkPayment({ id: 'p3', receivedDate: '2026-09-11', receivedAmount: '100000', confirmation: 'confirmed' });
    const p4 = mkPayment({ id: 'p4', receivedDate: '2026-09-11', receivedAmount: '100000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [p1, p2, p3, p4],
      resolvedDuplicates: [
        { id: p1.id, receivedDate: p1.receivedDate, receivedAmount: 100000, revision: p1.revision },
        { id: p2.id, receivedDate: p2.receivedDate, receivedAmount: 100000, revision: p2.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.receivedTotal).toBeNull();
  });

  it('중복 그룹 3건 모두 확인해야 합산', () => {
    const g1 = mkPayment({ id: 'g1', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g2 = mkPayment({ id: 'g2', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g3 = mkPayment({ id: 'g3', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [g1, g2, g3],
      resolvedDuplicates: [
        { id: g1.id, receivedDate: g1.receivedDate, receivedAmount: 100000, revision: g1.revision },
        { id: g2.id, receivedDate: g2.receivedDate, receivedAmount: 100000, revision: g2.revision },
        { id: g3.id, receivedDate: g3.receivedDate, receivedAmount: 100000, revision: g3.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(0);
    expect(r.receivedTotal).toBe(300000);
  });

  it('중복 3건 중 한 건만 확인하면 그룹 미해제로 합산 보류 + 후보 유지', () => {
    const g1 = mkPayment({ id: 'g1', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g2 = mkPayment({ id: 'g2', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g3 = mkPayment({ id: 'g3', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [g1, g2, g3],
      resolvedDuplicates: [
        { id: g1.id, receivedDate: g1.receivedDate, receivedAmount: 100000, revision: g1.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.duplicateCandidates[0]).toContain("'g1'");
    expect(r.receivedTotal).toBeNull();
  });

  it('ID 중복은 계속 차단하고 중복 후보에서 제외', () => {
    const dup = mkPayment({ id: 'same-id', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const other = mkPayment({ id: 'other', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [dup, dup, other],
    }));
    expect(r.errors.receivedPayments?.['same-id']).toContain('같은 ID');
    expect(r.duplicateCandidates.length).toBe(0);
    expect(r.errors.receivedPayments?.['same-id']).not.toContain('별도 지급');
  });

  it('수정된 기록이면 resolved로 풀려도 revision 불일치로 다시 보류', () => {
    const p1 = mkPayment({ id: 'p1', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const p2 = mkPayment({ id: 'p2', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    // 실제 화면 수정으로 revision이 올라갈 수 있음
    const patched = applyReceivedPaymentPatch(p1, { confirmation: 'confirmed', receivedAmount: '20000' });
    const r = calculatePaycheck(input({
      receivedPayments: [patched, p2],
      resolvedDuplicates: [
        // 예전 확인 기록: 예전 revision을 그대로 두고 다시 확인
        { id: p1.id, receivedDate: p1.receivedDate, receivedAmount: 20000, revision: p1.revision },
        { id: p2.id, receivedDate: p2.receivedDate, receivedAmount: 20000, revision: p2.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.duplicateCandidates[0]).toContain("'p1'");
    expect(r.receivedTotal).toBeNull();
  });

  it('수정 후 새 확인으로 revision 맞춰야 합산', () => {
    const p1 = mkPayment({ id: 'p1', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const p2 = mkPayment({ id: 'p2', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const patched = applyReceivedPaymentPatch(p1, { confirmation: 'confirmed', receivedAmount: '20000' });
    const r = calculatePaycheck(input({
      receivedPayments: [patched, p2],
      resolvedDuplicates: [
        { id: p1.id, receivedDate: patched.receivedDate, receivedAmount: 20000, revision: patched.revision },
        { id: p2.id, receivedDate: p2.receivedDate, receivedAmount: 20000, revision: p2.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(0);
    expect(r.receivedTotal).toBe(40000);
  });

  it('새 ID 지급 추가 시 중복 그룹은 현재 기록 기준 그대로 판단', () => {
    const a1 = mkPayment({ id: 'a1', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const a2 = mkPayment({ id: 'a2', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const a3 = mkPayment({ id: 'a3', receivedDate: '2026-09-10', receivedAmount: '20000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [a1, a2, a3],
      resolvedDuplicates: [
        { id: a1.id, receivedDate: a1.receivedDate, receivedAmount: 20000, revision: a1.revision },
        { id: a2.id, receivedDate: a2.receivedDate, receivedAmount: 20000, revision: a2.revision },
      ],
    }));
    // 새 a3가 미해결이라 그룹 미해결 유지, 후보에는 3건 모두 노출
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.duplicateCandidates[0]).toContain("'a1'");
    expect(r.duplicateCandidates[0]).toContain("'a2'");
    expect(r.duplicateCandidates[0]).toContain("'a3'");
    expect(r.receivedTotal).toBeNull();
  });

  it('서로 다른 중복 그룹 2개가 있으면 한 그룹만 풀어도 나머지 그룹 때문에 합산 보류', () => {
    const g1a = mkPayment({ id: 'g1a', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g1b = mkPayment({ id: 'g1b', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g2a = mkPayment({ id: 'g2a', receivedDate: '2026-09-11', receivedAmount: '200000', confirmation: 'confirmed' });
    const g2b = mkPayment({ id: 'g2b', receivedDate: '2026-09-11', receivedAmount: '200000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [g1a, g1b, g2a, g2b],
      resolvedDuplicates: [
        { id: g1a.id, receivedDate: g1a.receivedDate, receivedAmount: 100000, revision: g1a.revision },
        { id: g1b.id, receivedDate: g1b.receivedDate, receivedAmount: 100000, revision: g1b.revision },
        { id: g2a.id, receivedDate: g2a.receivedDate, receivedAmount: 200000, revision: g2a.revision },
        { id: g2b.id, receivedDate: g2b.receivedDate, receivedAmount: 200000, revision: g2b.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(0);
    expect(r.receivedTotal).toBe(600000);
  });

  it('서로 다른 중복 그룹 중 하나만 미해결이면 합산 보류 + 미해결 그룹만 후보 노출', () => {
    const g1a = mkPayment({ id: 'g1a', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g1b = mkPayment({ id: 'g1b', receivedDate: '2026-09-10', receivedAmount: '100000', confirmation: 'confirmed' });
    const g2a = mkPayment({ id: 'g2a', receivedDate: '2026-09-11', receivedAmount: '200000', confirmation: 'confirmed' });
    const g2b = mkPayment({ id: 'g2b', receivedDate: '2026-09-11', receivedAmount: '200000', confirmation: 'confirmed' });
    const r = calculatePaycheck(input({
      receivedPayments: [g1a, g1b, g2a, g2b],
      resolvedDuplicates: [
        { id: g1a.id, receivedDate: g1a.receivedDate, receivedAmount: 100000, revision: g1a.revision },
        { id: g1b.id, receivedDate: g1b.receivedDate, receivedAmount: 100000, revision: g1b.revision },
      ],
    }));
    expect(r.duplicateCandidates.length).toBe(1);
    expect(r.duplicateCandidates[0]).toContain("'g2a'");
    expect(r.duplicateCandidates[0]).toContain("'g2b'");
    expect(r.receivedTotal).toBeNull();
  });
});