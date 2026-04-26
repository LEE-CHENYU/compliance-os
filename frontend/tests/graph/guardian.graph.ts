export type GraphEdgeRisk = "safe" | "mutating" | "external" | "payment" | "voice";

export interface GraphEdge {
  id: string;
  node: "dashboard";
  route: string;
  selector: string;
  risk: GraphEdgeRisk;
  before?: { selector: string }[];
  expect?: {
    testId?: string;
    hiddenTestId?: string;
    text?: string | RegExp;
    urlPath?: string;
    pressed?: boolean;
  };
}

export const dashboardGraphEdges: GraphEdge[] = [
  {
    id: "dashboard.switch-view.timeline",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-view-timeline']",
    risk: "safe",
    expect: { testId: "dashboard-timeline-view", pressed: true },
  },
  {
    id: "dashboard.switch-view.documents",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-view-documents']",
    risk: "safe",
    expect: { testId: "dashboard-documents-view", pressed: true },
  },
  {
    id: "dashboard.switch-view.deadlines",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-view-deadlines']",
    risk: "safe",
    expect: { testId: "dashboard-deadlines-view", pressed: true },
  },
  {
    id: "dashboard.switch-view.profile",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-view-profile']",
    risk: "safe",
    expect: { testId: "dashboard-profile-view", pressed: true },
  },
  {
    id: "dashboard.filter.category.tax",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-filter-category-tax']",
    risk: "safe",
    expect: { testId: "dashboard-active-filter", text: /Tax/i, pressed: true },
  },
  {
    id: "dashboard.filter.risk.needs_attention",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-filter-risk-needs-attention']",
    risk: "safe",
    expect: { testId: "dashboard-active-filter", text: /Needs attention/i, pressed: true },
  },
  {
    id: "dashboard.filter.risk.potential_risks",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-filter-risk-potential-risks']",
    risk: "safe",
    expect: { testId: "dashboard-active-filter", text: /Potential risks/i, pressed: true },
  },
  {
    id: "dashboard.clear-filter.main",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-clear-filter-main']",
    risk: "safe",
    before: [{ selector: "[data-testid='dashboard-filter-category-tax']" }],
    expect: { hiddenTestId: "dashboard-active-filter" },
  },
  {
    id: "dashboard.open-recommended-service.fbar_check",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-recommended-service-fbar_check']",
    risk: "safe",
    expect: { urlPath: "/services/fbar_check" },
  },
  {
    id: "dashboard.voice.start",
    node: "dashboard",
    route: "/dashboard",
    selector: "[aria-label='Start live voice']",
    risk: "voice",
  },
  {
    id: "dashboard.payment.checkout",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='checkout-submit']",
    risk: "payment",
  },
];

export function graphEdgesForDefaultRun() {
  return dashboardGraphEdges.filter((edge) => edge.risk === "safe");
}
