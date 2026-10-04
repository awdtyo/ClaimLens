/**
 * Client-side upload validation. Mirrors the backend limits
 * (`MAX_UPLOAD_BYTES = 30 MB`, PDF only) so bad files are rejected
 * before any network request. The backend still enforces its own
 * checks; this is only for fast feedback.
 */

export const MAX_UPLOAD_BYTES = 30 * 1024 * 1024;

export type UploadError = "not-pdf" | "too-large" | "empty";

export interface UploadCheck {
  ok: boolean;
  error?: UploadError;
}

export const UPLOAD_ERROR_MESSAGE: Record<UploadError, string> = {
  "not-pdf": "Only PDF files are accepted.",
  "too-large": "The PDF exceeds the 30 MB limit.",
  empty: "No file was selected.",
};

export function checkUploadFile(file: File | null | undefined): UploadCheck {
  if (!file) return { ok: false, error: "empty" };
  const nameOk = file.name.toLowerCase().endsWith(".pdf");
  const typeOk =
    file.type === "" || file.type === "application/pdf";
  if (!nameOk || !typeOk) return { ok: false, error: "not-pdf" };
  if (file.size > MAX_UPLOAD_BYTES) return { ok: false, error: "too-large" };
  if (file.size === 0) return { ok: false, error: "empty" };
  return { ok: true };
}
