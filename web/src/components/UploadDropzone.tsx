import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { checkUploadFile, UPLOAD_ERROR_MESSAGE } from "../lib/upload";
import { cn } from "../lib/utils";
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
        className={cn(
          "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging
            ? "border-blue-600 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
            : "border-gray-300 hover:border-gray-400 dark:border-gray-700 dark:hover:border-gray-600",
        )}
      >
        <UploadCloud size={28} aria-hidden="true" className="text-gray-500 dark:text-gray-400" />
        <p className="font-medium">
          {uploading ? "Uploading…" : "Drop a paper PDF here, or click to choose one"}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          PDF only, 30 MB maximum.
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
        <p role="alert" className="mt-2 text-sm text-red-700 dark:text-red-300">
          {localError ?? error}
        </p>
      )}
      <div className="mt-3 flex justify-end">
        <Button
          variant="outline"
          size="sm"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          Choose file
        </Button>
      </div>
    </div>
  );
}
