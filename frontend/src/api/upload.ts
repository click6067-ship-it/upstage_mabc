import type { UploadParsedResult } from '../App';

export interface ParseUploadSuccess {
  requestId: string;
  documentName: string;
  data: UploadParsedResult;
}

export interface ParseUploadError {
  requestId: string;
  error: {
    code: string;
    messageKey: string;
    retryable: boolean;
    fieldErrors: Array<{ field: string; code: string; messageKey: string }>;
  };
}

export type ParseUploadResponse = ParseUploadSuccess | ParseUploadError;

/**
 * POST /api/parse-upload
 * - multipart/form-data, FormData의 `document` 필드(PDF 1개), 최대 3MB
 * - 성공 응답: { requestId, documentName, data: { documentName, periodStart, periodEnd, items, totals, warnings } }
 */
export async function postParseUpload(
  file: File,
  requestId: string,
): Promise<ParseUploadResponse> {
  const form = new FormData();
  form.append('document', file);

  const res = await fetch('/api/parse-upload', {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const raw = await res.text().catch(() => '{}');
    try {
      const parsed = JSON.parse(raw) as ParseUploadResponse;
      if ('error' in parsed) {
        return parsed;
      }
    } catch {
      // fall through
    }
    return {
      requestId,
      error: {
        code: 'NETWORK',
        messageKey: 'NETWORK',
        retryable: true,
        fieldErrors: [],
      },
    };
  }

  const json = (await res.json()) as ParseUploadResponse;
  return json;
}
