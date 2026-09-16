import React, { useState, useCallback } from 'react';
import type { UploadReviewState, DraftItem, DraftItems, UploadParsedResult } from './App';
import { postParseUpload, type ParseUploadResponse } from './api/upload';
interface Props {
  state: UploadReviewState;
  side: 'before' | 'after';
  onUpdate: (next: UploadReviewState) => void;
  onCancel: () => void;
  onApply: () => void;
}

function excerptTrunc(excerpt: string, max = 160): string {
  if (!excerpt) return '';
  return excerpt.length > max ? excerpt.slice(0, max) + '…' : excerpt;
}

function initials(name: string): string {
  return name
    .replace(/[_-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');
}

function formatAmount(amountKrw: number | null): string {
  if (amountKrw === null) return '—';
  return `${amountKrw.toLocaleString()}원`;
}

export default function UploadReview({ state, side, onUpdate, onCancel, onApply }: Props) {
  const { phase, documentName, pdfUrl, parsed, error, draft } = state;

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const toggleItemChecked = useCallback(
    (id: string) => {
      if (!draft) return;
      const nextItems = draft.items.map((it: DraftItem) =>
        it.id === id ? { ...it, checked: !it.checked } : it,
      );
      onUpdate({
        ...state,
        draft: { ...draft, items: nextItems },
      });
    },
    [draft, state, onUpdate],
  );

  const updateDraftItem = useCallback(
    (id: string, patch: Partial<DraftItem>) => {
      if (!draft) return;
      const nextItems = draft.items.map((it: DraftItem) => (it.id === id ? { ...it, ...patch } : it));
      onUpdate({ ...state, draft: { ...draft, items: nextItems } });
    },
    [draft, state, onUpdate],
  );

  const startEdit = useCallback((id: string, field: keyof DraftItem, value: string) => {
    setEditingId(id);
    setEditValue(value);
  }, []);

  const commitEdit = useCallback(
    (id: string, field: keyof DraftItem) => {
      if (!editingId || editingId !== id) return;
      const v = editValue.trim();
      if (field === 'amount' && v !== '' && !/^\d+$/.test(v)) {
        return;
      }
      updateDraftItem(id, { [field]: field === 'amount' ? v : v } as Partial<DraftItem>);
      setEditingId(null);
      setEditValue('');
    },
    [editingId, editValue, updateDraftItem],
  );

  const proposePairings = useCallback(() => {
    if (!parsed) return [];
    const earnings: UploadParsedResult['items'] = parsed.items.filter((it: UploadParsedResult['items'][0]) => it.category === 'earnings');
    const deductions: UploadParsedResult['items'] = parsed.items.filter((it: UploadParsedResult['items'][0]) => it.category === 'deductions');
    return [
      ...buildUniquePairs(earnings),
      ...buildUniquePairs(deductions),
    ];
  }, [parsed]);

  const renderDetail = useCallback(
    (item: UploadParsedResult['items'][0]) => {
      const amountText = formatAmount(item.amountKrw);
      const pageText = item.page ? `p.${item.page}` : '—';
      return (
        <div className="upload-review-row-detail">
          <span className="upload-review-badge" data-category={item.category}>
            {item.category === 'earnings' ? '지급' : '공제'}
          </span>
          <span className="upload-review-label">{item.label}</span>
          <span className="upload-review-amount">{amountText}</span>
          <span className="upload-review-page">{pageText}</span>
        </div>
      );
    },
    [],
  );

  const checkedCount = draft ? draft.items.filter((it: DraftItem) => it.checked).length : 0;
  const totalCount = draft ? draft.items.length : 0;

  return (
    <div className="upload-review-root">
      <header className="upload-review-header">
        <div className="upload-review-title-block">
          <h1 className="upload-review-title">명세서 PDF 비교 — 검토</h1>
          <p className="upload-review-sub">
            {side === 'before' ? '정정 전' : '정정 후'} 명세서를 올리면 초안을 보여주고, 사용자가 직접 확인한 뒤 기존 입력에 반영해요.
          </p>
        </div>
        <div className="upload-review-side-badge" data-side={side}>
          {side === 'before' ? '정정 전' : '정정 후'}
        </div>
      </header>

      <nav className="upload-review-nav" aria-label="업로드 검토 단계">
        <ol className="upload-review-steps">
          <li className={`upload-review-step${phase === 'loading' || phase === 'ready' || phase === 'error' || phase === 'applied' ? ' active' : ''}`}>
            <span className="upload-review-step-num">1</span>
            <span className="upload-review-step-label">PDF 올리기</span>
          </li>
          <li className={`upload-review-step${phase === 'ready' || phase === 'error' || phase === 'applied' ? ' active' : ''}`}>
            <span className="upload-review-step-num">2</span>
            <span className="upload-review-step-label">초안 확인·수정</span>
          </li>
          <li className={`upload-review-step${phase === 'applied' ? ' active' : ''}`}>
            <span className="upload-review-step-num">3</span>
            <span className="upload-review-step-label">입력에 적용</span>
          </li>
        </ol>
      </nav>

      {phase === 'idle' && (
        <div className="upload-review-idle">
          <div className="upload-review-idle-card">
            <h2 className="upload-review-idle-title">PDF를 올리면 초안을 만들어줘요</h2>
            <p className="upload-review-idle-desc">
              업스테이지 문서 파싱과 Solar Pro4 추출을 거쳐 항목별 초안이 만들어져요.
              먼저 직접 PDF를 올리거나, 준비된 예시 명세서를 써볼 수 있어요.
            </p>

            <div className="upload-review-upload-area">
              <label className="upload-review-dropzone">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (file.size > 3 * 1024 * 1024) {
                      onUpdate({
                        ...state,
                        phase: 'error',
                        error: {
                          code: 'TOO_LARGE',
                          message: 'PDF는 3MB 이하만 올릴 수 있어요.',
                          retryable: true,
                        },
                      });
                      return;
                    }
                    onUpdate({ ...state, phase: 'loading', requestId: crypto.randomUUID(), documentName: file.name, pdfUrl: '' });
                    callUpload(file);
                  }}
                  className="upload-review-file-input"
                />
                <span className="upload-review-dropzone-inner">
                  <span className="upload-review-dropzone-icon">{side === 'before' ? '📄' : '📑'}</span>
                  <span className="upload-review-dropzone-text">
                    <strong>PDF 올리기</strong>
                    <small>정정 {side === 'before' ? '전' : '후'} 명세서 PDF 1개 (최대 3MB)</small>
                  </span>
                </span>
              </label>
              {side === 'before' ? (
                <button
                  className="upload-review-sample-btn"
                  type="button"
                  onClick={() => useSample('01_2026-08_임금명세서_기존.pdf')}
                >
                  예시 명세서 사용 — 정정 전
                </button>
              ) : (
                <button
                  className="upload-review-sample-btn"
                  type="button"
                  onClick={() => useSample('02_2026-08_임금명세서_정정.pdf')}
                >
                  예시 명세서 사용 — 정정 후
                </button>
              )}
            </div>

            <div className="upload-review-hint">
              예시 명세서는 로컬 샘플 파일이에요. 실제 업로드 API로 보내고, 결과를 그대로 보여줘요.
            </div>
          </div>
        </div>
      )}

      {phase === 'loading' && (
        <div className="upload-review-pending">
          <div className="upload-review-spinner" aria-hidden="true" />
          <p>PDF를 올리고 초안을 만드는 중이에요.</p>
          <p className="upload-review-pending-hint">문서 파싱 → Solar 추출 순서로 진행돼요.</p>
        </div>
      )}

      {(phase === 'ready' || phase === 'error' || phase === 'applied') && (
        <div className="upload-review-body">
          {phase === 'error' && (
            <div className="upload-review-error-banner" role="alert">
              <h2 className="upload-review-error-title">초안을 만들지 못했어요</h2>
              <p className="upload-review-error-message">{error?.message ?? '알 수 없는 오류가 났어요.'}</p>
              {error?.retryable !== false && (
                <ul className="upload-review-error-hints">
                  <li>PDF가 맞는지, 3MB 이하인지 확인해 주세요.</li>
                  <li>다시 올리면 새로 시도할 수 있어요.</li>
                </ul>
              )}
              <button className="upload-review-secondary-btn" type="button" onClick={onCancel}>
                처음으로 돌아가기
              </button>
            </div>
          )}

          {phase === 'applied' && (
            <div className="upload-review-applied-banner" role="status">
              <h2 className="upload-review-applied-title">입력에 반영했어요</h2>
              <p className="upload-review-applied-message">
                {side === 'before' ? '정정 전' : '정정 후'} 항목의 초안이 기존 입력에 반영됐어요.
              </p>
              <button className="upload-review-primary-btn" type="button" onClick={onCancel}>
                입력으로 돌아가기
              </button>
            </div>
          )}

          {(phase === 'ready' || phase === 'error') && parsed && (
            <div className="upload-review-main">
              <section className="upload-review-left">
                <div className="upload-review-document-card">
                  <div className="upload-review-document-head">
                    <h2 className="upload-review-document-title">원문 PDF</h2>
                    <span className="upload-review-document-name">{documentName}</span>
                  </div>
                  <div className="upload-review-pdf-viewer">
                    <object
                      data={pdfUrl}
                      type="application/pdf"
                      className="upload-review-pdf-object"
                      aria-label="업로드한 PDF 원문"
                    >
                      <a className="upload-review-pdf-fallback" href={pdfUrl} target="_blank" rel="noopener noreferrer">
                        PDF를 새 창에서 열기
                      </a>
                    </object>
                  </div>
                  <p className="upload-review-pdf-hint">
                    미리보기가 보이지 않으면 위 링크로 원문을 열 수 있어요.
                  </p>
                </div>

                {parsed.warnings.length > 0 && (
                  <div className="upload-review-warnings" role="note">
                    <h3 className="upload-review-warnings-title">추출 참고</h3>
                    <ul>
                      {parsed.warnings.map((w: string, i: number) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="upload-review-totals">
                  <h3 className="upload-review-totals-title">합계(참고)</h3>
                  <dl className="upload-review-totals-grid">
                    <div>
                      <dt>총 지급</dt>
                      <dd>{formatAmount(parsed.totals.grossKrw)}</dd>
                    </div>
                    <div>
                      <dt>총 공제</dt>
                      <dd>{formatAmount(parsed.totals.deductionsKrw)}</dd>
                    </div>
                    <div>
                      <dt>실지급 액</dt>
                      <dd>{formatAmount(parsed.totals.netKrw)}</dd>
                    </div>
                  </dl>
                  <p className="upload-review-totals-note">
                    합계는 참고용이에요. 항목에 직접 추가되지 않아요.
                  </p>
                </div>
              </section>

              <section className="upload-review-right">
                <div className="upload-review-draft-card">
                  <div className="upload-review-draft-head">
                    <h2 className="upload-review-draft-title">추출 초안</h2>
                    <span className="upload-review-draft-meta">
                      {checkedCount}/{totalCount} 선택
                    </span>
                  </div>

                  <p className="upload-review-draft-sub">
                    같은 분류·같은 항목명의 유일한 1:1 짝만 제안했어요.
                    체크하고 내용을 고친 뒤 &apos;입력에 적용&apos;을 눌러야 기존 입력에 반영돼요.
                  </p>

                  <ul className="upload-review-draft-list">
                    {draft?.items.map((item: DraftItem) => (
                      <li key={item.id} className={`upload-review-draft-item${item.checked ? ' checked' : ''}`}>
                        <label className="upload-review-item-check">
                          <input
                            type="checkbox"
                            checked={item.checked}
                            onChange={() => toggleItemChecked(item.id)}
                            className="upload-review-checkbox"
                          />
                          <span className="upload-review-checkbox-label">반영할 항목</span>
                        </label>

                        <div className="upload-review-item-body">
                          <div className="upload-review-item-top">
                            <span className="upload-review-item-category" data-category={item.category}>
                              {item.category === 'earnings' ? '지급' : '공제'}
                            </span>
                            <span className="upload-review-item-label">{item.label}</span>
                          </div>

                          <div className="upload-review-item-grid">
                            <div className="upload-review-field">
                              <span className="upload-review-field-label">항목명</span>
                              <input
                                className="upload-review-field-input"
                                type="text"
                                value={item.label}
                                onChange={e => updateDraftItem(item.id, { label: e.target.value })}
                                onFocus={e => startEdit(item.id, 'label', e.target.value)}
                                onBlur={() => commitEdit(item.id, 'label')}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') {
                                    e.currentTarget.blur();
                                  }
                                }}
                              />
                            </div>
                            <div className="upload-review-field">
                              <span className="upload-review-field-label">금액(원)</span>
                              <input
                                className="upload-review-field-input"
                                type="text"
                                inputMode="numeric"
                                value={item.amount}
                                onChange={e => {
                                  const v = e.target.value;
                                  if (v === '' || /^\d*$/.test(v)) {
                                    updateDraftItem(item.id, { amount: v });
                                  }
                                }}
                                onFocus={e => startEdit(item.id, 'amount', e.target.value)}
                                onBlur={() => commitEdit(item.id, 'amount')}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') {
                                    e.currentTarget.blur();
                                  }
                                }}
                              />
                            </div>
                            <div className="upload-review-field">
                              <span className="upload-review-field-label">페이지</span>
                              <input
                                className="upload-review-field-input upload-review-field-input-small"
                                type="text"
                                inputMode="numeric"
                                value={item.page}
                                onChange={e => {
                                  const v = e.target.value;
                                  if (v === '' || /^\d*$/.test(v)) {
                                    updateDraftItem(item.id, { page: v });
                                  }
                                }}
                                onFocus={e => startEdit(item.id, 'page', e.target.value)}
                                onBlur={() => commitEdit(item.id, 'page')}
                              />
                            </div>
                            <div className="upload-review-field upload-review-field-excerpt">
                              <span className="upload-review-field-label">근거 문구</span>
                              <input
                                className="upload-review-field-input"
                                type="text"
                                value={item.excerpt}
                                onChange={e => updateDraftItem(item.id, { excerpt: e.target.value })}
                                onFocus={e => startEdit(item.id, 'excerpt', e.target.value)}
                                onBlur={() => commitEdit(item.id, 'excerpt')}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') {
                                    e.currentTarget.blur();
                                  }
                                }}
                              />
                            </div>
                          </div>

                          {item.excerpt && (
                            <p className="upload-review-excerpt-preview">
                              원문 문장: {excerptTrunc(item.excerpt)}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>

                  {proposePairings().length > 0 && (
                    <div className="upload-review-pairing">
                      <h3 className="upload-review-pairing-title">제안 짝 (같은 분류·같은 항목명)</h3>
                      <ul className="upload-review-pairing-list">
                        {proposePairings().map(([a, b], i) => (
                          <li key={i} className="upload-review-pairing-row">
                            <span className="upload-review-pairing-left">
                              <span className="upload-review-badge" data-category={a.category}>
                                {a.category === 'earnings' ? '지급' : '공제'}
                              </span>
                              {a.label}
                            </span>
                            <span className="upload-review-pairing-arrow" aria-hidden="true">→</span>
                            <span className="upload-review-pairing-right">
                              <span className="upload-review-badge" data-category={b.category}>
                                {b.category === 'earnings' ? '지급' : '공제'}
                              </span>
                              {b.label}
                            </span>
                          </li>
                        ))}
                      </ul>
                      <p className="upload-review-pairing-note">
                        위 짝은 제안일 뿐이에요. 비교 화면에서 직접 확인한 뒤 사용해야 해요.
                      </p>
                    </div>
                  )}

                  <div className="upload-review-actions">
                    <button
                      className="upload-review-primary-btn"
                      type="button"
                      disabled={checkedCount === 0}
                      onClick={onApply}
                    >
                      입력에 적용
                    </button>
                    <button className="upload-review-secondary-btn" type="button" onClick={onCancel}>
                      취소
                    </button>
                  </div>
                  <p className="upload-review-actions-note">
                    적용 전 취소하거나 적용이 실패하면 기존 입력은 그대로 보존돼요.
                  </p>
                </div>
              </section>
            </div>
          )}
        </div>
      )}

      <script
        type="application/json"
        dangerouslySetInnerHTML={{ __html: '' }}
      />
    </div>
  );

  function callUpload(file: File) {
    const rid = crypto.randomUUID();
    postParseUpload(file, rid)
      .then((res: ParseUploadResponse) => {
        if ('error' in res) {
          onUpdate({
            ...state,
            phase: 'error',
            requestId: res.requestId,
            documentName: file.name,
            pdfUrl: URL.createObjectURL(file),
            parsed: null,
            error: {
              code: res.error.code,
              message: res.error.messageKey,
              retryable: res.error.retryable,
            },
            draft: null,
          });
          return;
        }
        const data = res.data as UploadParsedResult;
        onUpdate({
          ...state,
          phase: 'ready',
          requestId: res.requestId,
          documentName: res.documentName || file.name,
          pdfUrl: URL.createObjectURL(file),
          rawText: '',
          parsed: data,
          error: null,
          draft: buildDraftFromParsed(data, file.name),
        });
      })
      .catch(() => {
        onUpdate({
          ...state,
          phase: 'error',
          requestId: rid,
          documentName: file.name,
          pdfUrl: URL.createObjectURL(file),
          parsed: null,
          error: { code: 'NETWORK', message: 'NETWORK', retryable: true },
          draft: null,
        });
      });
  }

  function useSample(filename: string) {
    const sampleUrl = `/samples/${filename}`;
    fetch(sampleUrl, { cache: 'no-store' })
      .then(async r => {
        if (!r.ok) throw new Error(r.statusText);
        const blob = await r.blob();
        if (blob.size > 3 * 1024 * 1024) throw new Error('TOO_LARGE');
        const file = new File([blob], filename, { type: 'application/pdf' });
        onUpdate({ ...state, phase: 'loading', requestId: crypto.randomUUID(), documentName: filename, pdfUrl: '' });
        callUpload(file);
      })
      .catch(() => {
        onUpdate({
          ...state,
          phase: 'error',
          requestId: crypto.randomUUID(),
          documentName: filename,
          pdfUrl: sampleUrl,
          parsed: null,
          error: { code: 'SAMPLE_UNAVAILABLE', message: '예시 명세서를 가져오지 못했어요.', retryable: true },
          draft: null,
        });
      });
  }

  function buildDraftFromParsed(data: UploadParsedResult, sourceName: string): DraftItems {
    const items: DraftItem[] = data.items.map((it: UploadParsedResult['items'][0], idx: number) => ({
      id: `draft-${idx}`,
      category: it.category,
      label: it.label,
      amount: it.amountKrw != null ? String(it.amountKrw) : '',
      page: it.page != null ? String(it.page) : '',
      excerpt: it.excerpt || '',
      checked: true,
    }));
    return {
      items,
      sourceId: sourceName,
      periodStart: '',
      periodEnd: '',
    };
  }

  function buildUniquePairs(list: UploadParsedResult['items']): Array<[UploadParsedResult['items'][0], UploadParsedResult['items'][0]]> {
    const byKey = new Map<string, UploadParsedResult['items'][0]>();
    for (const it of list) {
      const k = `${it.category}||${it.label.trim().toLowerCase()}`;
      if (byKey.has(k)) {
        continue;
      }
      byKey.set(k, it);
    }
    const result: Array<[UploadParsedResult['items'][0], UploadParsedResult['items'][0]]> = [];
    for (const [k, v] of byKey) {
      // 1:1 제안이므로 같은 항목을 양쪽에서 한 번씩 보여주는 형태로 표시
      result.push([v, v]);
    }
    return result;
  }
}
