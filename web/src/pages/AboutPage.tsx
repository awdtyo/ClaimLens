import VerdictBadge from "../components/VerdictBadge";

/**
 * About page: what the verdicts mean and the scaled-run rule, in plain
 * factual language.
 */
export default function AboutPage() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">About ClaimLens</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          ClaimLens audits a computer-science paper claim by claim. It
          extracts testable claims, plans a reproduction, runs
          reduced-scale experiments in a Docker sandbox, compares measured
          results to the reported numbers in code, and writes one verdict
          per claim.
        </p>
      </div>

      <section aria-labelledby="verdicts-heading" className="flex flex-col gap-2">
        <h2 id="verdicts-heading" className="text-lg font-semibold">
          Verdict statuses
        </h2>
        <ul className="flex flex-col gap-2 text-sm">
          <li className="flex flex-col gap-1">
            <VerdictBadge status="replicated" className="self-start" />
            <span className="text-gray-600 dark:text-gray-400">
              The measured result matches the reported number within the
              check tolerance.
            </span>
          </li>
          <li className="flex flex-col gap-1">
            <VerdictBadge status="partially replicated" className="self-start" />
            <span className="text-gray-600 dark:text-gray-400">
              The measured result is close but outside tolerance, or the run
              was scaled down so it cannot fully confirm the claim.
            </span>
          </li>
          <li className="flex flex-col gap-1">
            <VerdictBadge status="not replicated" className="self-start" />
            <span className="text-gray-600 dark:text-gray-400">
              The measured result clearly differs from the reported number
              at full scale.
            </span>
          </li>
          <li className="flex flex-col gap-1">
            <VerdictBadge status="untestable" className="self-start" />
            <span className="text-gray-600 dark:text-gray-400">
              The claim could not be tested, for example because required
              data is unavailable. “Untestable at this scale” means the
              reduced-scale run says nothing either way.
            </span>
          </li>
        </ul>
      </section>

      <section aria-labelledby="scaled-heading" className="flex flex-col gap-2">
        <h2 id="scaled-heading" className="text-lg font-semibold">
          The scaled-run rule
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Some experiments run at reduced scale to save time. A scaled run
          cannot refute a paper: it can only say “partially replicated” or
          “untestable at this scale”. The report states what each scaled run
          does and does not show.
        </p>
      </section>

      <section aria-labelledby="limits-heading" className="flex flex-col gap-2">
        <h2 id="limits-heading" className="text-lg font-semibold">
          Limits
        </h2>
        <ul className="list-disc pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>Every claim gets a verdict, including “untestable”.</li>
          <li>Numbers are compared in code with explicit tolerances; no model decides whether results match.</li>
          <li>Every detail the paper omits is logged as an assumption with a reason and a confidence level.</li>
          <li>Tables are read twice (text layer and page images); mismatches are flagged, not resolved.</li>
        </ul>
      </section>
    </div>
  );
}
