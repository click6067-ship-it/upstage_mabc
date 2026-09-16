import React, { useState, useRef, useMemo, useEffect } from 'react';
import { RowInput, CompareRouteState, CompareResult, CompareError } from './store/types';
import { ItemChangeResult, type FieldValue, type SourceRef } from './api/types';
import { postExplain, buildExplainRequest, ExplainState, type ExplainResult, type ExplainError } from './api/explain';
import ActionBlock from './ActionBlock';
import { formatAmount, formatDetails, formatLabel, formatSourceText } from './actions';

interface Props {
  result: CompareResult | null;
  error: CompareError | null;
  pending: boolean;
  retryCount: number;
  onBack: () => void;
  onRetry: () => void;
  onStartOver: () => void;
}

const summaryLabels: Array<[string, string]> = [
  ['totalKrw', '합계(만원)'],
  ['count', '항목 수'],
  ['diffKrw', '차액(만원)'],
  ['diffPercent', '차액율(%)'],
];

export default function ResultScreen({ result, error, pending, retryCount, onBack, onRetry, onStartOver }: Props) {
  const prevResultRef = useRef<CompareResult | null>(null);
  const [activeResult, setActiveResult] = useState<CompareResult | null>(null);
  const [explanationOpen, setExplanationOpen] = useState(false);

  useEffect(() => {
    if (result) {
      prevResultRef.current = activeResult;
      setActiveResult(result);
    }
  }, [result]);

  const summaryRows = useMemo(() => {
    if (!activeResult) return [];
    const s = activeResult.data.summary;
    const rows: Array<{ key: string; value: string }> = [];
    for (const [k, label] of summaryLabels) {
      const v = s && k in s ? s[k] : undefined;
      let text: string;
      if (v === null || v === undefined) {
        text = '입력 안 됨';
      } else if (typeof v === 'number') {
        if (Number.isInteger(v)) {
          text = `${v.toLocaleString()}원`;
        } else {
          text = `${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
        }
      } else if (typeof v === 'string') {
        text = v;
      } else {
        text = String(v);
      }
      rows.push({ key: label, value: text });
    }
    return rows;
  }, [activeResult]);

  return (
    <section className="result-screen">
      <header className="result-header">
        <h1 className="result-title">비교 결과</h1>
        <p className="result-muted">
          새로고침하면 이 결과도 사라질 수 있어요. 입력 화면으로 돌아가도 지금까지 입력한 값은 남아 있어요.
        </p>
      </header>

      <div className="result-body">
        {pending ? (
          <div className="result-pending">
            <div className="spinner" aria-hidden="true" />
            <p>비교를 요청했어요. 응답을 기다리는 중이에요.</p>
            <p className="hint">입력값을 바꾸면 이 요청은 버려지고, 새 요청이 나가요.</p>
          </div>
        ) : error ? (
          <div className="result-error">
            <h2 className="error-title">비교를 완료하지 못했어요</h2>
            <p className="error-message">
              {error.error.messageKey}
            </p>
            {error.error.retryable ? (
              <ul className="error-hints">
                <li>입력을 바꾸면 다시 시도할 수 있어요.</li>
                <li>입력값이 그대로면 아래 버튼을 눌러 다시 요청할 수 있어요.</li>
              </ul>
            ) : (
              <ul className="error-hints">
                <li>입력값을 확인하면 다시 시도할 수 있어요.</li>
              </ul>
            )}
            {error.error.fieldErrors && error.error.fieldErrors.length > 0 ? (
              <div className="error-fields">
                <p>입력값 확인:</p>
                <ul>
                  {error.error.fieldErrors.map(fe => (
                    <li key={fe.field}>{fe.field}: {fe.messageKey}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <ActionBlock
              title=""
              primaryLabel={error.error.retryable ? '다시 시도' : '입력 다시 보기'}
              primaryOnClick={error.error.retryable ? onRetry : onBack}
              secondaryLabel="처음부터 다시"
              secondaryOnClick={onStartOver}
            />
          </div>
        ) : activeResult ? (
          <>
            <button
              className="result-back-link"
              onClick={onBack}
              type="button"
              aria-label="입력 화면으로 돌아가기"
            >
              ← 다시 입력
            </button>

            <section className="result-section">
              <h2 className="result-section-title">항목별 변경</h2>
              <p className="result-section-sub">
                같은 항목인지 확인한 짝에 대해서만 바뀌었는지 보여줘요.
              </p>
              <ul className="change-list">
                {activeResult.data.itemChanges.map((ic, idx) => (
                  <ItemChangeRow key={idx} ic={ic} latestResult={activeResult} prevResult={prevResultRef.current} />
                ))}
                {activeResult.data.itemChanges.length === 0 ? (
                  <li className="change-empty">
                    <p>같은 항목으로 확인된 변경이 없어요.</p>
                  </li>
                ) : null}
              </ul>
              {activeResult.data.warnings.length > 0 ? (
                <div className="warnings">
                  <h3>주의</h3>
                  <ul>
                    {activeResult.data.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>

            <details className="request-info-details">
              <summary>상세 정보</summary>
              <div className="request-info-body">
                <div className="info-row">
                  <span className="info-key">요청 ID</span>
                  <span className="info-value">{activeResult.requestId}</span>
                </div>
                <div className="info-row">
                  <span className="info-key">버전</span>
                  <span className="info-value">{activeResult.versionKey}</span>
                </div>
              </div>
            </details>

            <section className="explain-section">
              <h2 className="explain-section-title">차이 설명과 질문 만들기</h2>
              <p className="explain-section-sub">
                위 비교 결과 중 금액이 바뀐 항목을 Upstage Solar로 보내 짧은 한국어 설명과 회사 확인 질문을 만들어요.
                요청에는 항목 이름과 바뀐 금액만 담기고, 키나 증빙 원문은 포함되지 않아요.
              </p>
              <button
                className="explain-primary-btn"
                onClick={() => setExplanationOpen(true)}
                type="button"
              >
                차이 설명과 질문 만들기
              </button>
            </section>
          </>
        ) : null}
      </div>

      <footer className="result-footer">
        <span className="hint">이 화면의 결과는 임시로만 표시돼요. 새로고침하면 사라질 수 있어요.</span>
      </footer>

      {explanationOpen && activeResult ? (
        <ExplanationDialog
          result={activeResult}
          onClose={() => setExplanationOpen(false)}
        />
      ) : null}
    </section>
  );
}

function ItemChangeRow({ ic, latestResult, prevResult }: { ic: ItemChangeResult; latestResult: CompareResult; prevResult: CompareResult | null }) {
  const kind = ic.contentKind;
  const moved = ic.moved;
  const changedFields = ic.changedFields;
  const beforeSources = ic.beforeSourceRefs ?? [];
  const afterSources = ic.afterSourceRefs ?? [];
  const previousValue = prevResult && prevResult.data.itemChanges.some(p => sameItemPair(p, ic))
    ? prevResult.data.itemChanges.find(p => sameItemPair(p, ic))
    : null;
  const previousRequestId = prevResult?.requestId;

  return (
    <li className={`change-item kind-${kind}${moved ? ' moved' : ''}`}>
      <div className="change-head">
        <span className="change-kind">{kindBadge(kind)}</span>
        {moved && <span className="move-tag">위치 이동</span>}
        {changedFields.length > 0 && <span className="changed-tag">바뀐 값: {changedFields.join(', ')}</span>}
      </div>
      <dl className="before-after">
        <div>
          <dt className="side-label">기존</dt>
          <dd className="side-amount">{formatAmount(ic.beforeFields)}</dd>
          <dd className="side-details">{formatDetails(ic.beforeFields)}</dd>
          {formatLabel(ic.beforeFields) ? <dd className="side-label">표기: {formatLabel(ic.beforeFields)}</dd> : null}
        </div>
        <div>
          <dt className="side-label">정정</dt>
          <dd className="side-amount">{formatAmount(ic.afterFields)}</dd>
          <dd className="side-details">{formatDetails(ic.afterFields)}</dd>
          {formatLabel(ic.afterFields) ? <dd className="side-label">표기: {formatLabel(ic.afterFields)}</dd> : null}
        </div>
      </dl>
      <div className="item-meta">
        <div className="meta-related">
          <p className="meta-label">관련 자료</p>
          {formatSourceText(beforeSources).trim() !== '' || formatSourceText(afterSources).trim() !== '' ? (
            <p className="source">
              {beforeSources.length > 0 ? `입력 자료(기존): ${formatSourceText(beforeSources)}` : ''}
              {beforeSources.length > 0 && afterSources.length > 0 ? ' · ' : ''}
              {afterSources.length > 0 ? `입력 자료(수정): ${formatSourceText(afterSources)}` : ''}
            </p>
          ) : (
            <p className="source-empty">관련 자료가 아직 정리되지 않았어요.</p>
          )}
        </div>
        <div className="meta-ref">
          <p className="meta-label">참고 문구</p>
          <p className="source-empty">참고 문구가 아직 준비되지 않았어요.</p>
        </div>
      </div>
      {previousValue ? (
        <div className="previous-note">
          <p>이전 결과({previousRequestId}):</p>
          <p>기존 {formatAmount(previousValue.beforeFields)} → 정정 {formatAmount(previousValue.afterFields)}</p>
        </div>
      ) : null}
      <div className="source-row">
        {beforeSources.length > 0 ? <span className="source">입력 자료: {formatSourceText(beforeSources)}</span> : <span className="source-empty">입력 자료: 없음</span>}
        {afterSources.length > 0 ? <span className="source">입력 자료: {formatSourceText(afterSources)}</span> : <span className="source-empty">입력 자료: 없음</span>}
      </div>
      {kind === 'unresolved' ? (
        <div className="note-box"><p>같은 항목인지 아직 확인되지 않았습니다. 어떤 항목끼리 대응되는지 직접 확인해 주세요.</p></div>
      ) : null}
    </li>
  );
}

function sameItemPair(a: ItemChangeResult, b: ItemChangeResult): boolean {
  if (a.beforeItemId && b.beforeItemId && a.beforeItemId === b.beforeItemId) return true;
  if (a.afterItemId && b.afterItemId && a.afterItemId === b.afterItemId) return true;
  return false;
}

function kindBadge(kind: string): string {
  return kindLabel(kind);
}

function kindLabel(kind: string): string {
  if (kind === 'changed') return '바뀜';
  if (kind === 'unchanged') return '같음';
  if (kind === 'unresolved') return '확인 필요';
  return kind;
}

function buildExplainItems(itemChanges: ItemChangeResult[]) {
  const items = [];
  for (const ic of itemChanges) {
    const b = ic.beforeFields ?? {};
    const a = ic.afterFields ?? {};
    const bAmount = b.amountKrw;
    const aAmount = a.amountKrw;
    const label = ic.beforeFields?.text || ic.afterFields?.text || `${ic.beforeItemId || '?'} → ${ic.afterItemId || '?'}`;
    items.push({
      beforeItemId: ic.beforeItemId || '',
      afterItemId: ic.afterItemId || '',
      beforeAmount: bAmount ?? null,
      afterAmount: aAmount ?? null,
      label,
    });
  }
  return items;
}

interface ExplanationDialogProps {
  result: CompareResult;
  onClose: () => void;
}

function ExplanationDialog({ result, onClose }: ExplanationDialogProps) {
  const [explainState, setExplainState] = useState<ExplainState>(null);
  const [consentGiven, setConsentGiven] = useState(false);
  const [copiedMsg, setCopiedMsg] = useState<string | null>(null);
  const pendingTagRef = useRef(0);
  const requestIdRef = useRef<string | null>(null);

  const changeItems = useMemo(() => {
    // 금액 변경이 있는 항목만 추출
    const items = [];
    for (const ic of result.data.itemChanges) {
      if (ic.contentKind !== 'changed') continue;
      const b = ic.beforeFields ?? {};
      const a = ic.afterFields ?? {};
      const bAmount = b.amountKrw;
      const aAmount = a.amountKrw;
      if (bAmount === null || bAmount === undefined || aAmount === null || aAmount === undefined) continue;
      if (bAmount === aAmount) continue;
      const label = ic.beforeFields?.text || ic.afterFields?.text || `${ic.beforeItemId || '?'} → ${ic.afterItemId || '?'}`;
      items.push({ beforeItemId: ic.beforeItemId || '', afterItemId: ic.afterItemId || '', beforeAmount: bAmount, afterAmount: aAmount, label });
    }
    return items;
  }, [result.data.itemChanges]);

  const handleConsent = () => {
    setConsentGiven(true);
    const tag = ++pendingTagRef.current;
    const requestId = crypto.randomUUID();
    requestIdRef.current = requestId;
    setExplainState({ requestId });

    postExplain(buildExplainRequest({ requestId, items: changeItems.slice(0, 30), maxItems: 30 }))
      .then((res) => {
        if (tag !== pendingTagRef.current) return;
        if (res?.error) {
          setExplainState({ message: res.error.message, retryable: res.error.retryable ?? true });
        } else if (res) {
          setExplainState({
            explanations: res.explanations ?? [],
            questions: res.questions ?? [],
          });
        }
      })
      .catch((err) => {
        if (tag !== pendingTagRef.current) return;
        setExplainState({
          message: err instanceof Error ? err.message : '설명 요청을 실패했습니다.',
          retryable: true,
        });
      });
  };

  const handleRetry = () => {
    const tag = ++pendingTagRef.current;
    const requestId = crypto.randomUUID();
    requestIdRef.current = requestId;
    setExplainState({ requestId });

    postExplain(buildExplainRequest({ requestId, items: changeItems.slice(0, 30), maxItems: 30 }))
      .then((res) => {
        if (tag !== pendingTagRef.current) return;
        if (res?.error) {
          setExplainState({ message: res.error.message, retryable: res.error.retryable ?? true });
        } else if (res) {
          setExplainState({
            explanations: res.explanations ?? [],
            questions: res.questions ?? [],
          });
        }
      })
      .catch((err) => {
        if (tag !== pendingTagRef.current) return;
        setExplainState({
          message: err instanceof Error ? err.message : '설명 요청을 실패했습니다.',
          retryable: true,
        });
      });
  };

  const handleCopyQuestions = async () => {
    if (!explainState || !('questions' in explainState) || !Array.isArray(explainState.questions) || explainState.questions.length === 0) {
      setCopiedMsg('복사할 질문이 없어요.');
      setTimeout(() => setCopiedMsg(null), 2000);
      return;
    }
    const text = explainState.questions.map((q, i) => `${i + 1}. ${q}`).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMsg('전체 질문을 클립보드에 복사했어요.');
    } catch {
      setCopiedMsg('복사에 실패했어요. 질문을 직접 선택해 복사해 주세요.');
    }
    setTimeout(() => setCopiedMsg(null), 3000);
  };

  return (
    <div className="explanation-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="explanation-modal" role="dialog" aria-modal="true" aria-label="차이 설명과 질문 만들기">
        <header className="explanation-modal-header">
          <h2 className="explanation-modal-title">차이 설명과 질문 만들기</h2>
          <button className="explanation-modal-close" onClick={onClose} aria-label="닫기">&#10005;</button>
        </header>

        <div className="explanation-modal-body">
          {!explainState && !consentGiven ? (
            <>
              <p className="explanation-intro">
                Upstage Solar가 비교 결과의 차이를 짧은 한국어 설명과 회사에 보낼 확인 질문으로 정리해 줘요.
              </p>
              <div className="explanation-items-preview">
                <h3 className="explanation-preview-title">Upstage로 보낼 항목</h3>
                {changeItems.length === 0 ? (
                  <p className="explanation-empty">설명 요청을 할 수 있는 금액 변경 항목이 없어요.</p>
                ) : (
                  <ul className="explanation-items-list">
                    {changeItems.map((it, i) => (
                      <li key={i}>
                        <strong>{it.label}</strong> — 기존 {it.beforeAmount?.toLocaleString() ?? '금액 없음'}원 → 정정 {it.afterAmount?.toLocaleString() ?? '금액 없음'}원
                      </li>
                    ))}
                  </ul>
                )}
                <p className="explanation-preview-note">
                  Upstage에는 항목 이름과 바뀐 금액만 전달돼요. 키나 증빙 원문은 포함하지 않아요.
                </p>
              </div>
              <div className="explanation-consent-actions">
                <button className="btn btn-primary" onClick={handleConsent}>
                  동의하고 설명하기 요청
                </button>
                <button className="btn btn-secondary" onClick={onClose}>
                  취소
                </button>
              </div>
            </>
          ) : explainState && 'requestId' in explainState ? (
            <div className="explanation-pending">
              <div className="spinner" aria-hidden="true" />
              <p>Upstage에 설명을 요청하고 있어요. 잠시만 기다려 주세요.</p>
              <p className="hint">이전 설명은 새 요청으로 덮어써져요.</p>
              <button className="btn btn-ghost" onClick={onClose}>
                창을 닫고 나중에 다시 보기
              </button>
            </div>
          ) : ExplainError.is(explainState) ? (
            <div className="explanation-error">
              <p className="explanation-error-title">설명 요청을 완료하지 못했어요</p>
              <p className="explanation-error-message">{explainState.message}</p>
              <div className="explanation-error-actions">
                {explainState.retryable ? (
                  <button className="btn btn-primary" onClick={handleRetry}>
                    다시 시도
                  </button>
                ) : null}
                <button className="btn btn-secondary" onClick={onClose}>
                  결과 화면으로 돌아가기
                </button>
              </div>
            </div>
          ) : ExplainResult.is(explainState) ? (
            <div className="explanation-result">
              <h3 className="explanation-result-title">차이 설명</h3>
              <ul className="explanation-result-list">
                {explainState.explanations.map((text, i) => (
                  <li key={i}>{text}</li>
                ))}
                {explainState.explanations.length === 0 ? (
                  <li className="hint">설명을 가져오지 못했어요.</li>
                ) : null}
              </ul>

              <h3 className="explanation-result-title">회사에 보낼 확인 질문</h3>
              <p className="explanation-result-hint">아래 질문을 복사해서 회사에 물어보세요.</p>
              <div className="explanation-questions">
                {explainState.questions.map((q, i) => (
                  <div key={i} className="explanation-question-item">
                    <span className="explanation-question-num">{i + 1}.</span>
                    <span className="explanation-question-text">{q}</span>
                  </div>
                ))}
                {explainState.questions.length === 0 ? (
                  <p className="hint">확인 질문을 가져오지 못했어요.</p>
                ) : null}
                {copiedMsg ? (
                  <p className="explanation-copy-done">{copiedMsg}</p>
                ) : null}
              </div>

              <div className="explanation-result-actions">
                <button className="btn btn-primary" onClick={handleCopyQuestions}>
                  전체 질문 복사
                </button>
                <button className="btn btn-secondary" onClick={onClose}>
                  결과 화면으로 돌아가기
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// TypeScript narrowing helpers
namespace ExplainResult {
  export function is(value: unknown): value is ExplainResult {
    if (value && typeof value === 'object' && 'explanations' in value && 'questions' in value) {
      const v = value as Record<string, unknown>;
      return Array.isArray(v.explanations) && Array.isArray(v.questions);
    }
    return false;
  }
}

namespace ExplainError {
  export function is(value: unknown): value is ExplainError {
    if (value && typeof value === 'object' && 'message' in value && 'retryable' in value) {
      const v = value as Record<string, unknown>;
      return typeof v.message === 'string' && typeof v.retryable === 'boolean';
    }
    return false;
  }
}
