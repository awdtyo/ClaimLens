import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { checkUploadFile, UPLOAD_ERROR_MESSAGE } from "../lib/upload";
import { Button } from "./ui";

interface UploadDropzoneProps {
  /** Called with a validated file. */
  onFile: (file: File) => void;
  uploading: boolean;
  /** Server-side or upload error to display. */
  error?: string | null;
}

/**
 * Drag-and-drop PDF upload. Client-side checks: PDF only, 30 MB max.
 * Fully keyboard accessible: the dropzone is a labelled file input.
 */
export default function UploadDropzone({ onFile, uploading, error }: UploadDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = (file: File | null | undefined) => {
    const check = checkUploadFile(file);
    if (!check.ok || !file) {
      setLocalError(
        check.error ? UPLOAD_ERROR_MESSAGE[check.error] : "No file was selected.",
      );
      return;
    }
    setLocalError(null);
    onFile(file);
  };

  return (
    <div>
      <div
        role="presentation"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          submit(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        tabIndex={0}
        aria-label="Upload a paper PDF"
        data-dragging={dragging}
        className="cl-dropzone flex cursor-pointer flex-col items-center gap-2 px-6 py-10 text-center"
      >
        <UploadCloud size={24} aria-hidden="true" className="text-[var(--text-2)]" />
        <p className="text-[0.9375rem] font-medium">
          {uploading ? "Uploading…" : "Drag & drop your PDF here or browse files"}
        </p>
        <p className="cl-meta">
          PDF · Up to 30 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          aria-label="Choose a paper PDF"
          className="sr-only"
          tabIndex={-1}
          disabled={uploading}
          onChange={(e) => {
            submit(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
      {(localError || error) && (
        <p role="alert" className="mt-2 text-sm text-[var(--bad)]">
          {localError ?? error}
        </p>
      )}
      <div className="mt-3 flex justify-center">
        <Button
          variant="outline"
          size="sm"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          Choose PDF
        </Button>
      </div>
    </div>
  );
}
