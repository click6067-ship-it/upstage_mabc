import type { ItemChangeResult } from '../api/types';

export interface ExplainSummary {
  /** Upstage로 보낼 항목 요약 (간단 텍스트) */
  items: string[];
  /** Upstage로 보낼 금액 목록 (바뀐 항목의 기존→정정 금액) */
  amounts: Array<{ beforeItemId: string; afterItemId: string; beforeAmount: string; afterAmount: string; label: string }>;
  /** 요청 대상 항목 수 (전체 중 몇 개) */
  totalItems: number;
  /** 실제로 설명 요청 대상에 포함되는 항목 수 */
  includedItems: number;
}

/** Solar 응답이 정상일 때의 결과 */
export interface ExplainResult {
  explanations: string[];
  questions: string[];
}

/** 요청 중 상태 */
export interface ExplainPending {
  /** 현재 요청 ID (중복 클릭 방지용) */
  requestId: string;
}

/** 오류 결과 */
export interface ExplainError {
  message: string;
  retryable: boolean;
}

export type ExplainState = ExplainResult | ExplainPending | ExplainError | null;

/**
 * POST /api/explain 요청 페이오드.
 *
 * - Solar 설명/질문 생성에 필요한 최소 정보만 담는다.
 * - 비교 결과 전체를 그대로 보내지 않고, 변경 항목의 값과 항목 ID만 추려서 보낸다.
 * - 본문에 키/문서 원문/증빙을 넣지 않는다.
 */
export interface ExplainRequest {
  /** 비교 결과의 requestId (추적/중복 방지용, PII 아님) */
  requestId: string;
  /** Solar에 전달할 항목 요약. 각 항목: 항목ID(기존/정정), amountKrw(기존/정정), label */
  items: Array<{
    beforeItemId: string;
    afterItemId: string;
    beforeAmount: number | null;
    afterAmount: number | null;
    label: string;
  }>;
  /** 요청할 최대 항목 수 (서버에서 제한 적용) */
  maxItems: number;
}

/**
 * POST /api/explain 응답.
 *
 * - Solar 응답이 정상 파싱되면 explanations/questions를 담는다.
 * - 실패 시 error를 담는다.
 */
export interface ExplainResponse {
  requestId: string;
  versionKey: string;
  explanations: string[];
  questions: string[];
  error: { message: string; retryable: boolean } | null;
}

/**
 * POST /api/explain 호출.
 *
 * - 중복 클릭 방지/무효화/타임아웃은 서버 및 클라이언트 양쪽에서 적용된다.
 * - 실패 시 기존 비교 결과는 그대로 둔다.
 */
export async function postExplain(request: ExplainRequest): Promise<ExplainResponse> {
  const res = await fetch('/api/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    keepalive: true,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '{"requestId":"?","versionKey":"?","explanations":[],"questions":[],"error":{"message":"NETWORK","retryable":true}}');
    try {
      return JSON.parse(raw) as ExplainResponse;
    } catch {
      return {
        requestId: '?',
        versionKey: '?',
        explanations: [],
        questions: [],
        error: { message: 'NETWORK', retryable: true },
      };
    }
  }

  const json = (await res.json()) as ExplainResponse;
  return json;
}

/**
 * POST /api/explain 요청 바디를 만든다.
 */
export function buildExplainRequest(params: {
  requestId: string;
  items: Array<{
    beforeItemId: string;
    afterItemId: string;
    beforeAmount: number | null;
    afterAmount: number | null;
    label: string;
  }>;
  maxItems: number;
}): ExplainRequest {
  return {
    requestId: params.requestId,
    items: params.items.slice(0, params.maxItems).map((it) => ({
      beforeItemId: it.beforeItemId,
      afterItemId: it.afterItemId,
      beforeAmount: it.beforeAmount,
      afterAmount: it.afterAmount,
      label: it.label,
    })),
    maxItems: params.maxItems,
  };
}
