import React, { useMemo } from 'react';
import {
 
  calculatePaycheck,
  parseAmount,
  parsePositiveAmount,
  isValidDate,
  parseReceivedPayments,
} from './calculate';
import { createReceivedPayment, applyReceivedPaymentPatch } from './types';
import type { PaycheckInput, PaycheckResult, ReceivedPayment, ResolvedDuplicate } from './types';

function PaymentRow({
  payment,
  idx,
  onPatch,
  onRemove,
}: {
  payment: ReceivedPayment;
  idx: number;
  onPatch: (idx: number, patch: Partial<{ receivedDate: string; receivedAmount: string; note: string; confirmation: 'unconfirmed' | 'confirmed' }>) => void;
  onRemove: (idx: number) => void;
}) {
  const amountErr = parsePositiveAmount(payment.receivedAmount);
  const amountError = typeof amountErr !== 'number' ? (amountErr as { error: string }).error : '';

  return (
    <li className="row-item">
      <fieldset className="row-field">
        <legend className="row-legend">지급 기록 {idx + 1}</legend>
        <div className="row-grid">
          <div>
            <label className="field-label">받은 날짜</label>
            <input
              className="input-field"
              type="date"
              value={payment.receivedDate}
              onChange={e => onPatch(idx, { receivedDate: e.target.value })}
            />
            {payment.receivedDate.trim() !== '' && !isValidDate(payment.receivedDate) ? (
              <p className="field-help" style={{ color: 'var(--danger)' }}>날짜 형식이 올바르지 않아요</p>
            ) : null}
          </div>
          <div>
            <label className="field-label">받은 금액(원)</label>
            <input
              className="input-field"
              type="text"
              inputMode="numeric"
              value={payment.receivedAmount}
              onChange={e => onPatch(idx, { receivedAmount: e.target.value })}
              placeholder="실제로 받은 금액"
            />
            {amountError ? <p className="field-help" style={{ color: 'var(--danger)' }}>{amountError}</p> : null}
          </div>
        </div>
        <div className="row-grid">
          <div>
            <label className="field-label">이 급여에 실제로 들어왔는지 확인</label>
            <div className="choice-row">
              <button
                className={`choice-btn${payment.confirmation === 'confirmed' ? ' choice-btn-selected' : ''}`}
                onClick={() => onPatch(idx, { confirmation: 'confirmed' })}
                type="button"
              >
                확인함
              </button>
              <button
                className={`choice-btn${payment.confirmation === 'unconfirmed' ? ' choice-btn-selected' : ''}`}
                onClick={() => onPatch(idx, { confirmation: 'unconfirmed' })}
                type="button"
              >
                확인 안 함
              </button>
            </div>
          </div>
        </div>
        <div className="row-grid">
          <div>
            <label className="field-label">참고</label>
            <input
              className="input-field"
              type="text"
              value={payment.note}
              onChange={e => onPatch(idx, { note: e.target.value })}
              placeholder="받은 방법 등 참고"
            />
          </div>
        </div>
        {payment.confirmation !== 'unconfirmed' ? (
          <button className="btn-ghost-small danger" onClick={() => onPatch(idx, { confirmation: 'unconfirmed' })} type="button">
            확인 상태 지우기
          </button>
        ) : null}
        {onRemove ? (
          <button className="btn-ghost-small danger" onClick={() => onRemove(idx)} type="button">
            이 지급 기록 제거
          </button>
        ) : null}
      </fieldset>
    </li>
  );
}

export default function PayrollScreen({ input, onInputChange, onBack, onStartOver }: {
  input: PaycheckInput;
  onInputChange: (next: PaycheckInput) => void;
  onBack: () => void;
  onStartOver: () => void;
}) {
  const result = useMemo(() => calculatePaycheck(input), [input]);

  const patchPayment = (idx: number, patch: Partial<{ receivedDate: string; receivedAmount: string; note: string; confirmation: 'unconfirmed' | 'confirmed' }>) => {
    const list = [...input.receivedPayments];
    if (idx < 0 || idx >= list.length) return;
    list[idx] = applyReceivedPaymentPatch(list[idx], patch);
    onInputChange({ ...input, receivedPayments: list });
  };

  const removePayment = (idx: number) => {
    const removed = input.receivedPayments[idx];
    if (!removed) return;
    onInputChange({
      ...input,
      receivedPayments: input.receivedPayments.filter((_, i) => i !== idx),
      resolvedDuplicates: input.resolvedDuplicates.filter(r => r.id !== removed.id),
    });
  };

  const confirmDuplicateForGroup = (groupIdx: number) => {
    const group = duplicatePairOptions[groupIdx];
    if (!group) return;
    const nextResolved: ResolvedDuplicate[] = [];
    for (let i = 0; i < input.receivedPayments.length; i++) {
      const p = input.receivedPayments[i];
      if (!group.indices.includes(i)) continue;
      const parsed = parsePositiveAmount(p.receivedAmount);
      if (typeof parsed !== 'number') continue;
      if (p.receivedDate.trim() !== group.date || parsed !== group.amount) continue;
      const rd = input.resolvedDuplicates.find(r => r.id === p.id);
      if (rd && rd.receivedDate === p.receivedDate.trim() && rd.receivedAmount === parsed && rd.revision === p.revision) {
        // 이미 유효한 확인이 있으면 중복 추가하지 않음
        nextResolved.push(rd);
        continue;
      }
      nextResolved.push({ id: p.id, receivedDate: p.receivedDate.trim(), receivedAmount: parsed, revision: p.revision });
    }
    if (nextResolved.length === 0) return;
    onInputChange({
      ...input,
      resolvedDuplicates: [
        ...input.resolvedDuplicates.filter(r => !nextResolved.some(n => n.id === r.id)),
        ...nextResolved,
      ],
    });
  };

  const clearResolvedDuplicatesForPayment = (paymentId: string) => {
    onInputChange({
      ...input,
      resolvedDuplicates: input.resolvedDuplicates.filter(r => r.id !== paymentId),
    });
  };

  const setReceiptCompleteness = (value: 'unknown' | 'partial' | 'complete') => {
    onInputChange({ ...input, receiptCompleteness: value });
  };

  const onExplicitNoReceiptChange = (checked: boolean) => {
    if (checked && result.hasAnyConfirmed) {
      if (window.confirm('명시적으로 전혀 못 받았다고 진술을 바꾸면, 이미 확인된 입금이 있어도 미수령 진술로 다시 처리돼요. 진술을 바꾸고 계속하시겠습니까?')) {
        onInputChange({ ...input, explicitNoReceipt: true });
      }
      // 취소하면 원래 상태 유지
    } else {
      onInputChange({ ...input, explicitNoReceipt: checked });
    }
  };

  const addPayment = () => {
    onInputChange({
      ...input,
      receivedPayments: [...input.receivedPayments, createReceivedPayment()],
    });
  };

  // 필드 파서 결과 (화면 표시용)
  const statementParse = parseAmount(input.statementAmount);
  const statementError = input.statementAmount.trim() !== '' && typeof statementParse !== 'number'
    ? (statementParse as { error: string }).error
    : '';

  const paymentErrMap: Record<string, string> = {};
  for (const p of input.receivedPayments) {
    const res = parsePositiveAmount(p.receivedAmount);
    if (p.receivedDate.trim() !== '' && typeof res !== 'number') {
      paymentErrMap[p.id] = (res as { error: string }).error;
    }
  }

  // 중복 후보 중 아직 resolved 되지 않은 것 추출
  // resolvedDuplicate는 기록의 id/날짜/금액/revision이 현재 상태 그대로 일치할 때만 유효
  const unresolvedDuplicates = useMemo(() => {
    const { duplicateByAmountDate } = parseReceivedPayments(input.receivedPayments);
    const resolvedGroupKeys = new Set<string>();
    for (const d of duplicateByAmountDate) {
      const groupKey = `${d.date}|${d.amount}`;
      const allValid = input.receivedPayments.every(p => {
        if (p.receivedDate.trim() !== d.date) return false;
        const parsed = parsePositiveAmount(p.receivedAmount);
        if (typeof parsed !== 'number') return false;
        if (parsed !== d.amount) return false;
        const rd = input.resolvedDuplicates.find(r => r.id === p.id);
        if (!rd) return false;
        if (rd.receivedDate !== d.date) return false;
        if (rd.receivedAmount !== parsed) return false;
        if (rd.revision !== p.revision) return false;
        return true;
      });
      if (allValid) resolvedGroupKeys.add(groupKey);
    }
    return duplicateByAmountDate.filter(d => !resolvedGroupKeys.has(`${d.date}|${d.amount}`));
  }, [input]);

  // 중복 후보별 지급 인덱스 매핑 (현재 기록 기준으로 유효한 후보만 노출)
  const duplicatePairOptions = useMemo(() => {
    const options: { date: string; amount: number; indices: number[]; id: string[] }[] = [];
    for (const d of unresolvedDuplicates) {
      const indices: number[] = [];
      const id: string[] = [];
      for (let i = 0; i < input.receivedPayments.length; i++) {
        const p = input.receivedPayments[i];
        if (p.receivedDate.trim() !== d.date) continue;
        const parsed = parsePositiveAmount(p.receivedAmount);
        if (typeof parsed !== 'number') continue;
        if (parsed !== d.amount) continue;
        indices.push(i);
        id.push(p.id);
      }
      if (indices.length >= 2) {
        options.push({ date: d.date, amount: d.amount, indices, id });
      }
    }
    return options;
  }, [input, unresolvedDuplicates]);

  const hasResult = input.statementAmount.trim() !== '' || result.receivedTotal !== null || result.difference !== null || result.referenceConfirmedSum > 0;

  return (
    <main className="paycheck-screen">
      <section className="card">
        <header className="card-head">
          <h1 className="title">급여 확인</h1>
          <button className="btn btn-ghost" onClick={onBack} type="button">뒤로</button>
        </header>

        <p className="section-muted">
          명세서에 적힌 금액과 실제로 받은 돈을 비교해 정리해요.
          확인한 입금 기록을 모아 총액을 가늠해요.
        </p>

        <section className="input-section">
          <h2 className="section-title">공통 정보</h2>
          <dl className="field-grid">
            <div>
              <dt>같은 일자리</dt>
              <dd>
                <input
                  className="input-field"
                  type="text"
                  value={input.employmentKey}
                  onChange={e => onInputChange({ ...input, employmentKey: e.target.value })}
                  placeholder="예: OO사업장 A팀"
                />
                {result.errors.employmentKey ? <p className="field-help" style={{ color: 'var(--danger)' }}>{result.errors.employmentKey}</p> : null}
              </dd>
            </div>
            <div>
              <dt>급여기간 시작</dt>
              <dd>
                <input
                  className="input-field"
                  type="date"
                  value={input.periodStart}
                  onChange={e => onInputChange({ ...input, periodStart: e.target.value })}
                />
                {result.errors.periodStart ? <p className="field-help" style={{ color: 'var(--danger)' }}>{result.errors.periodStart}</p> : null}
              </dd>
            </div>
            <div>
              <dt>급여기간 끝</dt>
              <dd>
                <input
                  className="input-field"
                  type="date"
                  value={input.periodEnd}
                  onChange={e => onInputChange({ ...input, periodEnd: e.target.value })}
                />
                {result.errors.periodEnd ? <p className="field-help" style={{ color: 'var(--danger)' }}>{result.errors.periodEnd}</p> : null}
              </dd>
            </div>
          </dl>
        </section>

        <section className="input-section">
          <h2 className="section-title">명세서 정보</h2>
          <dl className="field-grid">
            <div>
              <dt>명세서상 금액(원)</dt>
              <dd>
                <input
                  className="input-field"
                  type="text"
                  inputMode="numeric"
                  value={input.statementAmount}
                  onChange={e => onInputChange({ ...input, statementAmount: e.target.value })}
                  placeholder="계약서에 적힌 월급"
                />
                {statementError ? <p className="field-help" style={{ color: 'var(--danger)' }}>{statementError}</p> : null}
                <p className="hint">빈칸이면 계산 보류, 12abc·소수·범위 초과도 옆에 안내해요.</p>
              </dd>
            </div>
          </dl>
        </section>

        <section className="input-section">
          <h2 className="section-title">확인 상태 설정</h2>
          <dl className="field-grid">
            <div>
              <dt>전체 내역 확인 정도</dt>
              <dd>
                <div className="choice-row">
                  <button
                    className={`choice-btn${input.receiptCompleteness === 'unknown' ? ' choice-btn-selected' : ''}`}
                    onClick={() => setReceiptCompleteness('unknown')}
                    type="button"
                  >
                    모름
                  </button>
                  <button
                    className={`choice-btn${input.receiptCompleteness === 'partial' ? ' choice-btn-selected' : ''}`}
                    onClick={() => setReceiptCompleteness('partial')}
                    type="button"
                  >
                    일부만 확인
                  </button>
                  <button
                    className={`choice-btn${input.receiptCompleteness === 'complete' ? ' choice-btn-selected' : ''}`}
                    onClick={() => setReceiptCompleteness('complete')}
                    type="button"
                  >
                    전부 확인
                  </button>
                </div>
                <p className="hint">전체 지급기록 중 얼마나 확인했는지 나타내는 상태예요.</p>
              </dd>
            </div>
            <div>
              <dt>전혀 못 받았다는 진술</dt>
              <dd>
                <label className="choice-row" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={input.explicitNoReceipt}
                    onChange={e => onExplicitNoReceiptChange(e.target.checked)}
                  />
                  <span>명시적으로 전혀 못 받았다고 진술함</span>
                </label>
                {input.explicitNoReceipt ? (
          <p className="field-help" style={{ color: 'var(--warning)' }}>
            {result.hasAnyConfirmed
              ? '명시적으로 전혀 못 받았다고 진술했는데, 확인된 입금이 있어요. 진술을 다시 확인해 주세요. 새 입금을 확인할 때 기존 미수령 진술을 변경할지 묻고, 취소하면 원래 상태로 유지돼요. 반대로 입금이 있는데 미수령을 선택해도 이 충돌이 안내돼요.'
              : '명시적으로 전혀 못 받았다고 진술했어요. 확인된 입금이 없으면 수령액 0원으로 계산해요.'}
          </p>
        ) : null}
              </dd>
            </div>
          </dl>
        </section>

        <section className="input-section">
          <h2 className="section-title">실제 입금 기록</h2>
          <p className="section-muted">
            날짜를 아는 실제 입금만 적어 주세요. 받은 날짜·금액을 여러 건 넣을 수 있어요.
            각 기록이 정말 입금됐는지 확인한 뒤 상태를 골라요.
          </p>
          <ul className="row-list">
            {input.receivedPayments.map((p, idx) => (
              <PaymentRow
                key={p.id}
                payment={p}
                idx={idx}
                onPatch={patchPayment}
                onRemove={removePayment}
              />
            ))}
          </ul>
          <button className="add-row-btn" onClick={addPayment} type="button">
            지급 기록 추가
          </button>
          <p className="hint" style={{ marginTop: 8 }}>
            날짜·금액이 같은 기록이 둘이면 중복 후보로 봐요.
          </p>
        </section>

        {duplicatePairOptions.length > 0 ? (
          <section className="input-section">
            <h2 className="section-title">중복 후보 확인</h2>
            <p className="section-muted">
              같은 날짜·금액의 기록이 둘 이상 있어요. 서로 다른 실제 지급이 맞으면 아래 버튼으로 그룹 전체를 확인해 주세요.
            </p>
            <ul className="row-list">
              {duplicatePairOptions.map((opt, idx) => {
                const allResolved = opt.indices.every(i => {
                  const p = input.receivedPayments[i];
                  if (!p) return false;
                  const parsed = parsePositiveAmount(p.receivedAmount);
                  if (typeof parsed !== 'number') return false;
                  if (p.receivedDate.trim() !== opt.date || parsed !== opt.amount) return false;
                  const rd = input.resolvedDuplicates.find(r => r.id === p.id);
                  return rd && rd.receivedDate === p.receivedDate.trim() && rd.receivedAmount === parsed && rd.revision === p.revision;
                });
                return (
                  <li key={idx} className="row-item">
                    <fieldset className="row-field">
                      <legend className="row-legend">중복 후보 {idx + 1}: {opt.date} {opt.amount.toLocaleString()}원</legend>
                      <div className="row-grid">
                        {opt.id.map((id, i) => (
                          <div key={id}>
                            <label className="field-label">기록 {i + 1}</label>
                            <p className="small muted">ID {id}</p>
                          </div>
                        ))}
                      </div>
                      <button
                        className="btn btn-secondary"
                        onClick={() => confirmDuplicateForGroup(idx)}
                        type="button"
                        disabled={allResolved}
                      >
                        {allResolved ? '이미 확인함' : '서로 다른 실제 지급이 맞음'}
                      </button>
                    </fieldset>
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}

        {result.warnings.length > 0 ? (
          <div className="card" style={{ borderLeft: '4px solid var(--muted)', padding: '12px 14px' }}>
            <h3 className="subhead" style={{ margin: '0 0 6px' }}>안내</h3>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {result.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
            </ul>
          </div>
        ) : null}

        <section className="actions-section">
          <button className="primary-btn" onClick={onStartOver} type="button">
            처음부터 다시
          </button>
          <button className="secondary-btn" onClick={onBack} type="button">
            처음으로 돌아가기
          </button>
        </section>

        <p className="note">
          입력한 내용은 이 창에서만 임시로 기억해요. 새로고침하면 사라질 수 있어요.
        </p>
      </section>

      {hasResult ? (
        <section className="card">
          <h2 className="section-title">계산 결과</h2>
          <dl className="field-grid">
            <div>
              <dt>명세서상 금액</dt>
              <dd>{result.statementAmount !== null ? `${result.statementAmount.toLocaleString()}원` : '입력 안 됨'}</dd>
            </div>
            <div>
              <dt>확인한 수령액</dt>
              <dd>
                {result.receivedTotal === null
                  ? '미확인/보류'
                  : result.receivedTotal === 0 && input.explicitNoReceipt
                    ? '사용자 진술 기준 0원'
                    : `${result.receivedTotal.toLocaleString()}원`}
              </dd>
            </div>
            <div>
              <dt>현재 자료 기준 차이</dt>
              <dd className={result.difference !== null && result.difference < 0 ? 'danger-amount' : ''}>
                {result.difference !== null
                  ? (result.difference < 0
                      ? `차이: ${result.difference.toLocaleString()}원 (더 받음)`
                      : result.difference === 0
                        ? '명세서와 받은 총액이 같아요'
                        : `덜 받음: ${result.difference.toLocaleString()}원`)
                  : '계산 보류'}
              </dd>
            </div>
          </dl>
          <dl className="field-grid" style={{ marginTop: 6 }}>
            <div>
              <dt>전체 확인 상태</dt>
              <dd>
                {input.receiptCompleteness === 'unknown' ? '모름' :
                 input.receiptCompleteness === 'partial' ? '일부 확인' :
                 input.receiptCompleteness === 'complete' ? '전부 확인' : '-'}
              </dd>
            </div>
            <div>
              <dt>명시적 미수령 진술</dt>
              <dd>{input.explicitNoReceipt ? '있음' : '없음'}</dd>
            </div>
            <div>
              <dt>참고: 확인된 지급 합산</dt>
              <dd>{result.referenceConfirmedSum > 0 ? `${result.referenceConfirmedSum.toLocaleString()}원` : '없음'}</dd>
            </div>
          </dl>
          {result.duplicateCandidates.length > 0 ? (
            <div className="note-box" style={{ marginTop: 10 }}>
              <p>중복 후보 있음: {result.duplicateCandidates.join(', ')}</p>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
