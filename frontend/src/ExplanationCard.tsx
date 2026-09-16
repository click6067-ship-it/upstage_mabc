import React, { useMemo } from 'react';
import { FieldValue, ItemChangeResult } from './api/types';

/**
 * 변경 항목 목록을 읽고, Upstage Solar 설명/질문에 보낼 요약 텍스트를 만든다.
 *
 * - 실제 요청 대상이 되는 항목과 금액을 화면에 먼저 보여 준다.
 * - Solar에는 requestId + 항목 요약 ID/금액만 전달된다(본문/키/증빙 아님).
 * - Solar가 생성한 한국어 설명과 복사 가능 질문을 표시하는 것은 이 컴포넌트의 위쪽에서 처리한다.
 */

export interface ExplanationSummaryProps {
  itemChanges: ItemChangeResult[];
  maxItems: number;
}

export default function ExplanationSummary({ itemChanges, maxItems }: ExplanationSummaryProps) {
  const { lines, totalItems, includedItems } = useMemo(() => {
    const lines: string[] = [];
    const amounts: Array<{ beforeItemId: string; afterItemId: string; beforeAmount: number | null; afterAmount: number | null; label: string }> = [];
    const shown = Math.min(maxItems, itemChanges.length);
    for (let i = 0; i < shown; i++) {
      const ic = itemChanges[i];
      const b = ic.beforeFields ?? {};
      const a = ic.afterFields ?? {};
      const bAmount = b.amountKrw;
      const aAmount = a.amountKrw;
      const label = ic.beforeFields?.text || ic.afterFields?.text || `${ic.beforeItemId || '?'} → ${ic.afterItemId || '?'}`;
      lines.push(
        `${i + 1}. ${label} — 기존 ${bAmount !== null && bAmount !== undefined ? bAmount.toLocaleString() + '원' : '금액 없음'} → 정정 ${aAmount !== null && aAmount !== undefined ? aAmount.toLocaleString() + '원' : '금액 없음'}`
      );
      amounts.push({
        beforeItemId: ic.beforeItemId || '',
        afterItemId: ic.afterItemId || '',
        beforeAmount: bAmount ?? null,
        afterAmount: aAmount ?? null,
        label,
      });
    }
    if (itemChanges.length > shown) {
      lines.push(`... 외 ${itemChanges.length - shown}개 항목은 요청에 포함되지 않음`);
    }
    return {
      lines,
      totalItems: itemChanges.length,
      includedItems: shown,
      amounts,
    };
  }, [itemChanges, maxItems]);

  return (
    <div className="explain-summary">
      <div className="explain-summary-head">
        <span className="explain-summary-title">Upstage로 보낼 비교 항목</span>
        <span className="explain-summary-meta">
          전체 {totalItems}개 중 {includedItems}개 항목만 설명에 사용됨
        </span>
      </div>
      <ol className="explain-summary-list">
        {lines.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ol>
    </div>
  );
}
