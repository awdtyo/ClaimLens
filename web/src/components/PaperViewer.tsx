import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./ui";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

interface PaperViewerProps {
  /** Relative artifact URL of the paper PDF. */
  pdfUrl: string;
  /** 1-based page to show; jumps when the selected claim changes. */
  targetPage: number | null;
}

/**
 * Paper viewer (react-pdf). Jumps to the selected claim's page.
 * Keyboard accessible page controls; loading, empty and error states.
 */
export default function PaperViewer({ pdfUrl, targetPage }: PaperViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [page, setPage] = useState(1);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setPage(targetPage ?? 1);
  }, [targetPage, pdfUrl]);

  useEffect(() => {
    setNumPages(0);
    setLoadError(null);
    setPage(targetPage ?? 1);
  }, [pdfUrl, targetPage]);

  const clamp = (p: number) => Math.min(Math.max(1, p), Math.max(1, numPages));

  return (
    <div className="flex flex-col gap-2" aria-label="Paper viewer">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-gray-600 dark:text-gray-400" role="status">
          {targetPage ? `Claim cited on page ${targetPage}` : "Paper"}
          {numPages > 0 && ` · page ${page} of ${numPages}`}
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            aria-label="Previous page"
            disabled={page <= 1}
            onClick={() => setPage((p) => clamp(p - 1))}
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </Button>
          <label className="sr-only" htmlFor="paper-page">
            Page number
          </label>
          <input
            id="paper-page"
            type="number"
            min={1}
            max={Math.max(1, numPages)}
            value={page}
            onChange={(e) => setPage(clamp(Number(e.target.value) || 1))}
            className="h-8 w-16 rounded-md border border-gray-300 bg-white px-2 text-center text-sm dark:border-gray-700 dark:bg-gray-900"
          />
          <Button
            variant="outline"
            size="sm"
            aria-label="Next page"
            disabled={numPages > 0 && page >= numPages}
            onClick={() => setPage((p) => clamp(p + 1))}
          >
            <ChevronRight size={16} aria-hidden="true" />
          </Button>
        </div>
      </div>
      <div className="overflow-auto rounded-lg border border-gray-200 bg-gray-100 dark:border-gray-800 dark:bg-gray-900">
        <Document
          file={pdfUrl}
          onLoadSuccess={({ numPages: n }) => {
            setNumPages(n);
            setPage(clamp(targetPage ?? 1));
          }}
          onLoadError={(err) => setLoadError(err.message)}
          loading={<p className="p-6 text-sm text-gray-600 dark:text-gray-400">Loading paper…</p>}
          error=""
          noData={<p className="p-6 text-sm text-gray-600 dark:text-gray-400">No paper available.</p>}
        >
          {!loadError && (
            <Page
              pageNumber={page}
              width={560}
              renderTextLayer
              renderAnnotationLayer
              loading={<p className="p-6 text-sm text-gray-600 dark:text-gray-400">Loading page…</p>}
            />
          )}
        </Document>
        {loadError && (
          <p role="alert" className="p-6 text-sm text-red-700 dark:text-red-300">
            Could not load the paper PDF: {loadError}
          </p>
        )}
      </div>
    </div>
  );
}
