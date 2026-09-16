import React, { useState, useRef, useCallback } from 'react';
import { RowInput, CompareRouteState } from './store/types';
import { createEmptyRow, type ActionKind } from './actions';
import { CompareError } from './store/types';

interface Props {
  route: CompareRouteState;
  action: ActionKind | null;
  pending: boolean;
  error: CompareError | null;
  updateRow: (side: 'before' | 'after', idx: number, patch: Partial<RowInput>) => void;
  updateCommon: (patch: { employmentKey?: string; periodStart?: string; periodEnd?: string }) => void;
  addBefore: () => void;
  addAfter: () => void;
  removeRow: (side: 'before' | 'after', idx: number) => void;
  setMapping: (beforeId: string, afterId: string) => void;
  clearMappings: () => void;
  setActionChoice: (kind: ActionKind) => void;
  onRun: () => void;
  onBack: () => void;
  onUploadBefore?: () => void;
  onUploadAfter?: () => void;
}

export default function InputScreen({
  route,
  action,
  pending,
  error,
  updateRow,
  updateCommon,
  addBefore,
  addAfter,
  removeRow,
  setMapping,
  clearMappings,
  setActionChoice,
  onRun,
  onBack,
  onUploadBefore,
  onUploadAfter,
}: Props) {
  const matchesChoice = (value: ActionKind) => action === value;

  const choices = [
    { value: 'never-paid', label: '월급 못 받음' },
    { value: 'changed', label: '적거나 달라짐' },
    { value: 'understand', label: '명세서 이해' },
    { value: 'empty', label: '직접 입력' },
  ] as const;

  return (
    <section className="input-panel">
      {error ? (
        <div className="input-error-banner">
          <h2 className="error-title">{error.error.messageKey}</h2>
          <p className="error-message">입력값을 고쳐서 다시 비교할 수 있어요.</p>
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
          {error.error.retryable ? (
            <ul className="error-hints">
              <li>입력을 바꾸면 다시 시도할 수 있어요.</li>
              <li>입력값을 그대로 두면 아래에서 다시 요청할 수 있어요.</li>
            </ul>
          ) : null}
        </div>
      ) : null}
      <header className="input-header">
        <h1 className="input-title">정정 전후 비교 — 직접 입력</h1>
        <p className="input-muted">
          파일 업로드나 로그인 없이 시작할 수 있어요. 입력한 내용은 이 창에서만 임시로 유지되며, 새로고침하면 지워져요.
          선택을 바꿔도 입력한 값은 남아 있고, 뒤로 가도 입력이 유지돼요.
        </p>
      </header>

      <div className="input-sides">
        <section className="input-section side-section">
          <h2 className="section-title">공통 정보</h2>
          <p className="section-muted">같은 일자리/같은 기간의 공통 정보를 입력해요.</p>
          <dl className="field-grid">
            <div>
              <dt>같은 일자리</dt>
              <dd>
                <input
                  className="input-field"
                  type="text"
                  value={route.employmentKey}
                  onChange={e => updateCommon({ employmentKey: e.target.value })}
                  placeholder="예: OO사업장 A팀"
                />
              </dd>
              <dd className="hint">같은 일자리/기간인지 확인할 때 사용해요.</dd>
            </div>
            <div>
              <dt>기간 시작</dt>
              <dd>
                <input
                  className="input-field"
                  type="date"
                  value={route.periodStart}
                  onChange={e => updateCommon({ periodStart: e.target.value })}
                />
              </dd>
              <dd className="hint">몰라도 비워 둘 수 있어요. 필요한 정보만 안내해요.</dd>
            </div>
            <div>
              <dt>기간 끝</dt>
              <dd>
                <input
                  className="input-field"
                  type="date"
                  value={route.periodEnd}
                  onChange={e => updateCommon({ periodEnd: e.target.value })}
                />
              </dd>
              <dd className="hint">전월/당월 비교는 아직 지원하지 않아요.</dd>
            </div>
          </dl>
        </section>

        <div className="side-columns">
          <section className="input-section side-section">
            <h2 className="section-title">기존 항목 (정정 전)</h2>
            <p className="section-muted">같은 일자리/같은 기간의 기존 항목을 직접 입력해요.</p>
            <div className="upload-entry-row">
              <button className="upload-entry-btn" type="button" onClick={() => onUploadBefore?.()}>
                PDF 올리기 — 정정 전
              </button>
              <button className="upload-entry-sample-btn" type="button" onClick={() => onUploadBefore?.()}>
                예시 명세서 사용 — 정정 전
              </button>
            </div>
            <ul className="row-list">
              {route.before.map((row, idx) => (
                <RowField
                  key={row.id}
                  side="기존"
                  index={idx}
                  row={row}
                  isRemovable={route.before.length > 1}
                  onChange={patch => updateRow('before', idx, patch)}
                  onRemove={() => removeRow('before', idx)}
                />
              ))}
            </ul>
            <button className="add-row-btn-fixed" onClick={addBefore} type="button">항목 추가</button>
          </section>

          <section className="input-section side-section">
            <h2 className="section-title">수정 항목 (정정 후)</h2>
            <p className="section-muted">같은 일자리/같은 기간의 수정 항목을 직접 입력해요.</p>
            <div className="upload-entry-row">
              <button className="upload-entry-btn" type="button" onClick={() => onUploadAfter?.()}>
                PDF 올리기 — 정정 후
              </button>
              <button className="upload-entry-sample-btn" type="button" onClick={() => onUploadAfter?.()}>
                예시 명세서 사용 — 정정 후
              </button>
            </div>
            <ul className="row-list">
              {route.after.map((row, idx) => (
                <RowField
                  key={row.id}
                  side="수정"
                  index={idx}
                  row={row}
                  isRemovable={route.after.length > 1}
                  onChange={patch => updateRow('after', idx, patch)}
                  onRemove={() => removeRow('after', idx)}
                />
              ))}
            </ul>
            <button className="add-row-btn-fixed" onClick={addAfter} type="button">항목 추가</button>
          </section>
        </div>
      </div>

      <section className="input-section">
        <h2 className="section-title">무엇부터 해볼까요?</h2>
        <p className="section-muted">원하는 시작점을 고르면 예시 입력이 채워져요. 선택을 바꿔도 입력한 값은 남아 있어요.</p>
        <div className="choice-row">
          {choices.map(c => (
            <button
              key={c.value}
              className={`choice-btn${matchesChoice(c.value) ? ' choice-btn-selected' : ''}`}
              onClick={() => setActionChoice(c.value as ActionKind)}
              type="button"
            >
              {c.label}
            </button>
          ))}
        </div>
      </section>

      <section className="input-section">
        <h2 className="section-title">같은 항목인지 확인</h2>
        <p className="section-muted">기존 항목과 수정 항목이 같은 항목이라고 확인한 짝을 보여줘요. 필요하면 직접 바꿀 수 있어요.</p>
        <div className="mapping-area">
          {route.before.length === 0 && route.after.length === 0 ? (
            <p className="hint">양쪽에 항목이 있어야 짝을 만들 수 있어요.</p>
          ) : route.after.length === 0 ? (
            <p className="hint">수정 측 항목을 먼저 입력해주세요.</p>
          ) : (
            <ul className="mapping-list">
              {route.before.map((b, bi) => {
                const matchedAfterId = route.mappings.find(m => m.beforeId === b.id)?.afterId;
                const matchedAfter = matchedAfterId ? route.after.find(a => a.id === matchedAfterId) : undefined;
                const usedAfterIds = new Set(route.mappings.filter(m => m.beforeId !== b.id).map(m => m.afterId));
                const availableAfter = route.after.filter(a => !usedAfterIds.has(a.id));
                return (
                  <li key={b.id} className="mapping-row">
                    <span className="mapping-before">{b.key || b.label || `기존 ${bi + 1}`}</span>
                    <select
                      className="mapping-select"
                      value={matchedAfter?.id ?? ''}
                      onChange={e => {
                        const chosen = e.target.value;
                        if (chosen) {
                          setMapping(b.id, chosen);
                        } else {
                          setMapping(b.id, '');
                        }
                      }}
                    >
                      <option value="">짝 없음</option>
                      {availableAfter.map(a => (
                        <option key={a.id} value={a.id}>
                          {a.key || a.label || `수정 ${route.after.indexOf(a) + 1}`} {a.amount ? `(${a.amount}원)` : ''}
                        </option>
                      ))}
                    </select>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <section className="actions-section">
        <button className="primary-btn" onClick={onRun} type="button" disabled={pending}>
          {pending ? '비교 중…' : '비교하기'}
        </button>
        <button className="secondary-btn" onClick={onBack} type="button">
          처음으로 돌아가기
        </button>
      </section>

      <p className="note">
        이 화면의 입력값은 임시 메모리로만 저장돼요. 새로고침하면 지워질 수 있어요.
      </p>
    </section>
  );
}

function RowField({
  side,
  index,
  row,
  isRemovable,
  onChange,
  onRemove,
}: {
  side: string;
  index: number;
  row: RowInput;
  isRemovable: boolean;
  onChange: (patch: Partial<RowInput>) => void;
  onRemove: () => void;
}) {
  const patch = (changes: Partial<RowInput>) => onChange(changes);

  return (
    <li className="row-item">
      <fieldset className="row-field">
        <legend className="row-legend">{side} {index + 1}</legend>
        <div className="row-grid">
          <div>
            <label className="field-label">항목 이름</label>
            <input
              className="input-field small"
              type="text"
              value={row.key}
              onChange={e => patch({ key: e.target.value })}
              placeholder="예: 식대"
            />
          </div>
          <div>
            <label className="field-label">화면 이름</label>
            <input
              className="input-field small"
              type="text"
              value={row.label}
              onChange={e => patch({ label: e.target.value })}
              placeholder="예: 월 식대"
            />
          </div>
        </div>
        <div className="row-grid">
          <div>
            <label className="field-label">금액</label>
            <input
              className="input-field"
              type="text"
              inputMode="numeric"
              value={row.amount}
              onChange={e => patch({ amount: e.target.value })}
              placeholder="원 단위. 빈칸은 0으로 채우지 않아요"
            />
          </div>
          <div>
            <label className="field-label">근무(분)</label>
            <input
              className="input-field"
              type="text"
              inputMode="numeric"
              value={row.minutes}
              onChange={e => patch({ minutes: e.target.value })}
              placeholder="모르겠으면 비워 두세요"
            />
          </div>
          <div>
            <label className="field-label">시급</label>
            <input
              className="input-field"
              type="text"
              inputMode="numeric"
              value={row.rate}
              onChange={e => patch({ rate: e.target.value })}
              placeholder="모르겠으면 비워 두세요"
            />
          </div>
        </div>
        <div className="row-grid">
          <div>
            <label className="field-label">설명 메모</label>
            <input
              className="input-field"
              type="text"
              value={row.text}
              onChange={e => patch({ text: e.target.value })}
              placeholder="예: 식대"
            />
          </div>
        </div>
        <div className="row-grid source-grid">
          <div>
            <label className="field-label">자료 이름</label>
            <input
              className="input-field small"
              type="text"
              value={row.sourceId}
              onChange={e => patch({ sourceId: e.target.value })}
              placeholder="예: 9월 명세서"
            />
          </div>
          <div>
            <label className="field-label">위치</label>
            <input
              className="input-field small"
              type="text"
              value={row.sourcePage}
              onChange={e => patch({ sourcePage: e.target.value })}
              placeholder="예: 1"
            />
          </div>
          <div>
            <label className="field-label">참고 문구</label>
            <input
              className="input-field small"
              type="text"
              value={row.sourceExcerpt}
              onChange={e => patch({ sourceExcerpt: e.target.value })}
              placeholder="예: 식대 50000원"
            />
          </div>
        </div>
        <p className="source-hint">출처는 입력한 자료/항목으로 돌아가요.</p>
        {isRemovable ? (
          <button className="danger-btn small" onClick={onRemove} type="button">
            이 항목 제거
          </button>
        ) : (
          <span className="hint">항목이 하나만 남으면 제거할 수 없어요.</span>
        )}
      </fieldset>
    </li>
  );
}
