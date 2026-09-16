export interface ReceivedPayment {
  id: string;
  receivedDate: string;
  receivedAmount: string;
  confirmation: 'unconfirmed' | 'confirmed';
  revision: number;
  note: string;
}

export interface PaycheckInput {
  employmentKey: string;
  periodStart: string;
  periodEnd: string;
  statementAmount: string;
  receivedPayments: ReceivedPayment[];
  receiptCompleteness: 'unknown' | 'partial' | 'complete';
  explicitNoReceipt: boolean;
  resolvedDuplicates: ResolvedDuplicate[];
}

export interface ResolvedDuplicate {
  id: string;
  receivedDate: string;
  receivedAmount: number;
  revision: number;
}

export interface PaycheckErrors {
  employmentKey?: string;
  periodStart?: string;
  periodEnd?: string;
  statementAmount?: string;
  receivedTotal?: string;
  receivedPayments?: Record<string, string>;
  duplicateBlocked?: string;
  duplicateCandidate?: string;
}

export interface PaycheckResult {
  employmentKey: string;
  periodStart: string | null;
  periodEnd: string | null;
  statementAmount: number | null;
  receivedTotal: number | null;
  difference: number | null;
  duplicateBlocked: string[];
  duplicateCandidates: string[];
  errors: PaycheckErrors;
  warnings: string[];
  hasError: boolean;
  inputHeld: boolean;
  unknownPeriod: boolean;
  referenceConfirmedSum: number;
  hasAnyConfirmed: boolean;
}

export function createReceivedPayment(partial?: Partial<ReceivedPayment>): ReceivedPayment {
  return {
    id: crypto.randomUUID(),
    receivedDate: '',
    receivedAmount: '',
    confirmation: 'unconfirmed',
    revision: 0,
    note: '',
    ...partial,
  };
}

export function applyReceivedPaymentPatch(p: ReceivedPayment, patch: Partial<ReceivedPayment>): ReceivedPayment {
  return { ...p, ...patch, id: p.id, revision: p.revision + 1 };
}


export function emptyPaycheckInput(): PaycheckInput {
  return {
    employmentKey: '',
    periodStart: '',
    periodEnd: '',
    statementAmount: '',
    receivedPayments: [],
    receiptCompleteness: 'unknown',
    explicitNoReceipt: false,
    resolvedDuplicates: [],
  };
}