import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom has no matchMedia; ThemeProvider only needs the fallback.
// Framer Motion also calls the deprecated addListener/removeListener APIs.
if (typeof window !== "undefined" && !window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      // Modern API
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      // Deprecated API used by Framer Motion's useReducedMotion
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
} else if (typeof window !== "undefined" && window.matchMedia) {
  // Patch existing matchMedia stub to add the deprecated methods if absent
  const orig = window.matchMedia;
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      const mq = orig(query);
      if (!mq.addListener) {
        (mq as MediaQueryList & { addListener: unknown; removeListener: unknown }).addListener = vi.fn();
        (mq as MediaQueryList & { addListener: unknown; removeListener: unknown }).removeListener = vi.fn();
      }
      return mq;
    }),
  });
}

// jsdom has no IntersectionObserver; Framer Motion's whileInView uses it.
if (typeof window !== "undefined" && !window.IntersectionObserver) {
  const mockIntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
    takeRecords: vi.fn(() => []),
    root: null,
    rootMargin: "",
    thresholds: [],
  }));
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    value: mockIntersectionObserver,
  });
  Object.defineProperty(global, "IntersectionObserver", {
    writable: true,
    value: mockIntersectionObserver,
  });
}

afterEach(() => {
  cleanup();
});
