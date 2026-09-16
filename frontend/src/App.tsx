import React, { useState, useRef, useCallback } from 'react';
import { RowInput, CompareRouteState, CompareResult, CompareError } from './store/types';
import { postCompare, buildComparePayload, itemFromInput } from './api/compare';
import {
  createEmptyRow,
  applyRowPatch,
  addRowToList,
  removeRowFromList,
  addMapping,
  removeMappingsForRow,
  splitMappings,
  type ActionKind,
} from './actions';
import StartScreen from './StartScreen';
import PayrollScreen from './payroll/PaycheckScreen';
import InputScreen from './InputScreen';
import ResultScreen from './ResultScreen';
import UploadReview from './UploadReview';
import { emptyPaycheckInput } from './payroll/types';
import type { PaycheckInput } from './payroll/types';

type Phase = 'start' | 'input' | 'result' | 'paycheck' | 'upload-review';

export type UploadReviewState = {
  phase: 'idle' | 'loading' | 'ready' | 'error' | 'applied';
  side: 'before' | 'after';
  requestId: string;
  documentName: string;
  pdfUrl: string;
  rawText: string;
  parsed: UploadParsedResult | null;
  error: { code: string; message: string; retryable: boolean } | null;
  draft: DraftItems | null;
};

export interface DraftItem {
  id: string;
  checked: boolean;
  category: 'earnings' | 'deductions';
  label: string;
  amount: string;
  page: string;
  excerpt: string;
}

export interface DraftItems {
  items: DraftItem[];
  sourceId: string;
  periodStart: string;
  periodEnd: string;
}

export interface UploadParsedResult {
  items: Array<{
    category: 'earnings' | 'deductions';
    label: string;
    amountKrw: number | null;
    page: number | null;
    excerpt: string;
  }>;
  totals: { grossKrw: number | null; deductionsKrw: number | null; netKrw: number | null };
  warnings: string[];
}

const initialUploadReview: UploadReviewState = {
  phase: 'idle',
  side: 'before',
  requestId: '',
  documentName: '',
  pdfUrl: '',
  rawText: '',
  parsed: null,
  error: null,
  draft: null,
};

const initialRoute: CompareRouteState = {
  employmentKey: '',
  periodStart: '',
  periodEnd: '',
  before: [createEmptyRow('b', 1)],
  after: [createEmptyRow('a', 1)],
  mappings: [],
};

export default function App() {
  const [phase, setPhase] = useState<Phase>('start');
  const [route, setRoute] = useState<CompareRouteState>(initialRoute);
  const [action, setAction] = useState<ActionKind | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<CompareError | null>(null);

  // 급여 화면 입력 상태 (앱 레벨 — 뒤로 갔다 와도 유지)
  const [paycheckInput, setPaycheckInput] = useState<PaycheckInput>(emptyPaycheckInput);

  const queuedRef = useRef<{ requestId: string; payload: unknown } | null>(null);
  const requestTagRef = useRef(0);

  const updateRow = useCallback((side: 'before' | 'after', idx: number, patch: Partial<RowInput>) => {
    setRoute(prev => {
      const list = side === 'before' ? prev.before : prev.after;
      const next = list.map((r, i) => (i === idx ? applyRowPatch(r, patch) : r));
      return side === 'before'
        ? { ...prev, before: next as RowInput[] }
        : { ...prev, after: next as RowInput[] };
    });
  }, []);

  const updateCommon = useCallback((patch: { employmentKey?: string; periodStart?: string; periodEnd?: string }) => {
    setRoute(prev => ({ ...prev, ...patch }));
  }, []);

  const addBefore = useCallback(() => {
    setRoute(prev => ({
      ...prev,
      before: addRowToList(prev.before, createEmptyRow('b', prev.before.length + 1)),
    }));
  }, []);

  const addAfter = useCallback(() => {
    setRoute(prev => ({
      ...prev,
      after: addRowToList(prev.after, createEmptyRow('a', prev.after.length + 1)),
    }));
  }, []);

  const removeRow = useCallback((side: 'before' | 'after', idx: number) => {
    setRoute(prev => {
      const list = side === 'before' ? prev.before : prev.after;
      if (list.length <= 1) return prev;
      const removed = list[idx];
      const next = removeRowFromList(list, idx);
      return side === 'before'
        ? { ...prev, before: next as RowInput[], mappings: removeMappingsForRow(prev.mappings, removed.id) }
        : { ...prev, after: next as RowInput[], mappings: removeMappingsForRow(prev.mappings, removed.id) };
    });
  }, []);

  const setMapping = useCallback((beforeId: string, afterId: string) => {
    setRoute(prev => ({
      ...prev,
      mappings: addMapping(prev.mappings, beforeId, afterId),
    }));
  }, []);

  const clearMappings = useCallback(() => {
    setRoute(prev => ({ ...prev, mappings: [] }));
  }, []);

  const setActionChoice = useCallback((kind: ActionKind) => {
    setAction(kind);
  }, []);

  const runCompare = useCallback(async () => {
    const beforeItems = route.before.map((r, idx) => itemFromInput(r, idx + 1, 'before'));
    const afterItems = route.after.map((r, idx) => itemFromInput(r, idx + 1, 'after'));
    const { valid: validMappings, invalid: invalidMappings } = splitMappings(route.mappings, beforeItems, afterItems);

    let errorFields: Array<{ field: string; code: string; messageKey: string }> = [];
    for (const inv of invalidMappings) {
      const [bId, aId] = inv.split(' → ');
      const bRow = route.before.find(r => r.id === bId);
      const aRow = route.after.find(r => r.id === aId);
      if (bRow && !aRow) {
        errorFields.push({ field: 'mapping', code: 'MISSING_AFTER', messageKey: '확인되지_않은_짝_수정측' });
      } else if (!bRow && aRow) {
        errorFields.push({ field: 'mapping', code: 'MISSING_BEFORE', messageKey: '확인되지_않은_짝_기존측' });
      } else {
        errorFields.push({ field: 'mapping', code: 'INVALID_PAIR', messageKey: '확인되지_않은_짝' });
      }
    }

    if (invalidMappings.length > 0) {
      setError({
        requestId: crypto.randomUUID(),
        error: {
          code: 'INVALID_MAPPINGS',
          messageKey: '확인되지_않은_짝이_있습니다',
          retryable: true,
          fieldErrors: errorFields,
        },
      });
      setPhase('result');
      setResult(null);
      setPending(false);
      queuedRef.current = null;
      return;
    }

    const payload = buildComparePayload(
      route.employmentKey,
      route.periodStart,
      route.periodEnd,
      beforeItems,
      afterItems,
      validMappings,
      'v1',
      crypto.randomUUID(),
    );

    const requestId = (payload as { requestId: string }).requestId;
    const thisTag = ++requestTagRef.current;
    queuedRef.current = { requestId, payload };
    setPhase('result');
    setPending(true);
    setResult(null);
    setError(null);

    try {
      const res = await postCompare(payload as Parameters<typeof postCompare>[0]);
      if (thisTag !== requestTagRef.current) return;
      if ('error' in res) {
        setError({
          requestId: res.requestId,
          error: res.error,
        });
        setResult(null);
      } else {
        setResult(res);
        setError(null);
      }
    } catch {
      if (thisTag !== requestTagRef.current) return;
      setError({
        requestId,
        error: {
          code: 'NETWORK',
          messageKey: 'NETWORK',
          retryable: true,
          fieldErrors: [],
        },
      });
      setResult(null);
    } finally {
      if (thisTag === requestTagRef.current) setPending(false);
    }
  }, [route]);

  const onBack = useCallback(() => {
    requestTagRef.current += 1;
    setPending(false);
    if (phase === 'result') {
      setPhase('input');
    } else {
      setPhase('start');
    }
  }, [phase]);

  const onChoice = useCallback((kind: ActionKind) => {
    setAction(kind);
    if (kind === 'never-paid' || kind === 'changed') {
      setPhase('paycheck');
    } else {
      setPhase('input');
    }
  }, []);

  const onRetry = useCallback(() => {
    if (queuedRef.current) {
      runCompare();
    }
  }, [runCompare]);

  const onStartOver = useCallback(() => {
    requestTagRef.current += 1;
    setPhase('start');
    setAction(null);
    setRoute(initialRoute);
    setResult(null);
    setError(null);
    setPending(false);
    queuedRef.current = null;
  }, []);

  const [upReview, setUpReview] = useState<UploadReviewState>(initialUploadReview);

  const enterUploadReview = useCallback((side: 'before' | 'after') => {
    setPhase('upload-review');
    setUpReview({
      ...initialUploadReview,
      side,
    });
  }, [setUpReview]);

  const cancelUploadReview = useCallback(() => {
    setUpReview(initialUploadReview);
    setPhase('input');
  }, [setUpReview]);

  const applyUploadReview = useCallback(() => {
    const draft = upReview.draft;
    if (!draft || draft.items.length === 0) {
      setUpReview(prev => ({
        ...prev,
        phase: 'error',
        error: { code: 'EMPTY_DRAFT', message: '적용할 항목이 없어요.', retryable: false },
      }));
      return;
    }

    const side = upReview.side;
    const list = side === 'before' ? route.before : route.after;

    try {
      const newList: RowInput[] = [...list];
      const updates: Array<{ idx: number; patch: Partial<RowInput> }> = [];

      for (const item of draft.items) {
        if (!item.checked) continue;
        const existing = newList.find(r => r.label === item.label);
        const row: Partial<RowInput> = {
          key: item.label,
          label: item.label,
          amount: item.amount,
          sourcePage: item.page,
          sourceExcerpt: item.excerpt,
          sourceId: draft.sourceId,
        };
        if (existing) {
          updates.push({ idx: newList.indexOf(existing), patch: row });
        } else {
          const newRow: RowInput = {
            id: crypto.randomUUID(),
            key: item.label,
            label: item.label,
            amount: item.amount,
            minutes: '',
            rate: '',
            text: '',
            sourceId: draft.sourceId,
            sourcePage: item.page,
            sourceExcerpt: item.excerpt,
          };
          newList.push(newRow);
        }
      }

      for (const u of updates) {
        newList[u.idx] = applyRowPatch(newList[u.idx], u.patch);
      }

      const nextPeriodStart = draft.periodStart ? draft.periodStart : route.periodStart;
      const nextPeriodEnd = draft.periodEnd ? draft.periodEnd : route.periodEnd;

      const newRoute: CompareRouteState = {
        ...route,
        periodStart: nextPeriodStart,
        periodEnd: nextPeriodEnd,
        [side]: newList as RowInput[],
      };

      setRoute(newRoute);
      setUpReview(prev => ({ ...prev, phase: 'applied' }));
    } catch {
      setUpReview(prev => ({
        ...prev,
        phase: 'error',
        error: { code: 'APPLY_FAILED', message: '적용하지 못했어요. 입력을 보존했어요.', retryable: false },
      }));
    }
  }, [upReview, route, setRoute, setUpReview, applyRowPatch]);

  if (phase === 'start') {
    return <StartScreen onChoice={onChoice} onPdfCompare={() => enterUploadReview('before')} />;
  }

  if (phase === 'paycheck') {
    return (
      <PayrollScreen
        input={paycheckInput}
        onInputChange={setPaycheckInput}
        onBack={onBack}
        onStartOver={() => {
          requestTagRef.current += 1;
          setPaycheckInput(emptyPaycheckInput());
          onStartOver();
        }}
      />
    );
  }

  if (phase === 'input') {
    return (
      <InputScreen
        route={route}
        action={action ?? null}
        pending={pending}
        error={error}
        updateRow={updateRow}
        updateCommon={updateCommon}
        addBefore={addBefore}
        addAfter={addAfter}
        removeRow={removeRow}
        setMapping={setMapping}
        clearMappings={clearMappings}
        setActionChoice={setActionChoice}
        onRun={runCompare}
        onBack={onBack}
        onUploadBefore={() => enterUploadReview('before')}
        onUploadAfter={() => enterUploadReview('after')}
      />
    );
  }

  if (phase === 'upload-review') {
    return (
      <UploadReview
        state={upReview}
        side={upReview.side}
        onUpdate={setUpReview}
        onCancel={cancelUploadReview}
        onApply={applyUploadReview}
      />
    );
  }

  return (
    <ResultScreen
      result={result}
      error={error}
      pending={pending}
      retryCount={0}
      onBack={onBack}
      onRetry={onRetry}
      onStartOver={onStartOver}
    />
  );
}
