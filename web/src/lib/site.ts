/** Shared site content: workflow steps used on the landing page. */

export interface WorkflowStep {
  n: string;
  title: string;
  text: string;
}

export const HOW_IT_WORKS: WorkflowStep[] = [
  { n: "01", title: "Extract", text: "Identify testable claims" },
  { n: "02", title: "Plan", text: "Build reproduction strategy" },
  { n: "03", title: "Reproduce", text: "Run reduced-scale experiments" },
  { n: "04", title: "Verify", text: "Compare reported and measured evidence" },
];
