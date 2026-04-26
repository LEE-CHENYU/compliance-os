export type GraphEdgeRisk = "safe" | "mutating" | "external" | "payment" | "voice";

export type GraphNode =
  | "dashboard"
  | "account-orders"
  | "services"
  | "service-detail"
  | "service-questionnaire"
  | "connect"
  | "find-lawyer";

export type GraphMockProfile =
  | "dashboard-recommended"
  | "dashboard-active-order"
  | "account-orders"
  | "services"
  | "service-detail"
  | "connect"
  | "service-questionnaire";

export interface GraphStep {
  selector: string;
}

export interface GraphEdge {
  id: string;
  node: GraphNode;
  route: string;
  selector: string;
  risk: GraphEdgeRisk;
  mockProfile?: GraphMockProfile;
  before?: GraphStep[];
  defaultRun?: boolean;
  viewport?: {
    width: number;
    height: number;
  };
  expect?: {
    testId?: string;
    hiddenTestId?: string;
    selector?: string;
    text?: string | RegExp;
    urlPath?: string;
    popupUrlPath?: string;
    pressed?: boolean;
  };
}

export const graphEdges: GraphEdge[] = [
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
    id: "dashboard.mobile.switch-view.documents",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-mobile-view-documents']",
    risk: "safe",
    viewport: { width: 390, height: 844 },
    expect: { testId: "dashboard-documents-view", pressed: true },
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
    id: "dashboard.upload.open",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-open-upload-panel']",
    risk: "safe",
    expect: { testId: "dashboard-upload-panel", text: /Upload documents/i },
  },
  {
    id: "dashboard.upload.close",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-upload-panel-close']",
    risk: "safe",
    before: [{ selector: "[data-testid='dashboard-open-upload-panel']" }],
    expect: { hiddenTestId: "dashboard-upload-panel" },
  },
  {
    id: "dashboard.openclaw.open",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-openclaw-toggle']",
    risk: "safe",
    expect: { testId: "dashboard-openclaw-popover", text: /OpenClaw/i },
  },
  {
    id: "dashboard.service-center.recommended.fbar",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-recommended-service-fbar_check']",
    risk: "safe",
    mockProfile: "dashboard-recommended",
    expect: { urlPath: "/services/fbar_check" },
  },
  {
    id: "dashboard.service-center.active-order.fbar",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-service-order-fbar_check']",
    risk: "safe",
    mockProfile: "dashboard-active-order",
    expect: { urlPath: "/account/orders/order-fbar-active" },
  },
  {
    id: "dashboard.service-center.open-orders",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-open-orders']",
    risk: "safe",
    mockProfile: "dashboard-active-order",
    expect: { urlPath: "/account/orders" },
  },
  {
    id: "dashboard.service-center.browse-services",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='dashboard-browse-services']",
    risk: "safe",
    mockProfile: "dashboard-active-order",
    expect: { urlPath: "/services" },
  },
  {
    id: "account-orders.browse-services",
    node: "account-orders",
    route: "/account/orders",
    selector: "[data-testid='account-orders-browse-services']",
    risk: "safe",
    expect: { urlPath: "/services" },
  },
  {
    id: "account-orders.primary.83b",
    node: "account-orders",
    route: "/account/orders",
    selector: "[data-testid='account-order-primary-order-83b']",
    risk: "safe",
    expect: { urlPath: "/account/orders/order-83b" },
  },
  {
    id: "account-orders.service-link.83b",
    node: "account-orders",
    route: "/account/orders",
    selector: "[data-testid='account-order-service-order-83b']",
    risk: "safe",
    expect: { urlPath: "/services/election_83b" },
  },
  {
    id: "services.catalog.form8843",
    node: "services",
    route: "/services",
    selector: "[data-testid='services-product-form_8843_free']",
    risk: "safe",
    expect: { urlPath: "/form-8843" },
  },
  {
    id: "services.catalog.fbar",
    node: "services",
    route: "/services",
    selector: "[data-testid='services-product-fbar_check']",
    risk: "safe",
    expect: { urlPath: "/services/fbar_check" },
  },
  {
    id: "services.catalog.opt-execution",
    node: "services",
    route: "/services",
    selector: "[data-testid='services-product-opt_execution']",
    risk: "safe",
    expect: { urlPath: "/services/opt_execution" },
  },
  {
    id: "service-detail.opt-execution.start-questionnaire",
    node: "service-detail",
    route: "/services/opt_execution",
    selector: "[data-testid='service-start-opt_execution']",
    risk: "safe",
    expect: { urlPath: "/services/opt_execution/questionnaire" },
  },
  {
    id: "service-detail.fbar.start-order",
    node: "service-detail",
    route: "/services/fbar_check",
    selector: "[data-testid='service-start-fbar_check']",
    risk: "mutating",
    defaultRun: false,
  },
  {
    id: "service-questionnaire.evaluate",
    node: "service-questionnaire",
    route: "/services/opt_execution/questionnaire",
    selector: "[data-testid='service-questionnaire-evaluate']",
    risk: "mutating",
    expect: { text: /Recommended plan/i },
  },
  {
    id: "service-questionnaire.rerun",
    node: "service-questionnaire",
    route: "/services/opt_execution/questionnaire",
    selector: "[data-testid='service-questionnaire-rerun']",
    risk: "mutating",
    before: [{ selector: "[data-testid='service-questionnaire-evaluate']" }],
    expect: { selector: "[data-testid='service-questionnaire-evaluate']", text: /See recommendation/i },
  },
  {
    id: "connect.select-codex",
    node: "connect",
    route: "/connect",
    selector: "[data-testid='connect-app-codex']",
    risk: "safe",
    mockProfile: "connect",
    expect: { text: /~\/\.codex\/config\.toml/i },
  },
  {
    id: "connect.generate-token",
    node: "connect",
    route: "/connect",
    selector: "[data-testid='connect-token-button']",
    risk: "mutating",
    mockProfile: "connect",
    before: [{ selector: "[data-testid='connect-app-codex']" }],
    expect: { testId: "connect-copy-token", text: /Copy token/i },
  },
  {
    id: "find-lawyer.sample-report",
    node: "find-lawyer",
    route: "/find-lawyer",
    selector: "[data-testid='find-lawyer-sample-report']",
    risk: "safe",
    expect: { popupUrlPath: "/samples/lawyer-search-eb5-sample.pdf" },
  },
  {
    id: "dashboard.voice.start",
    node: "dashboard",
    route: "/dashboard",
    selector: "[aria-label='Start live voice']",
    risk: "voice",
    defaultRun: false,
  },
  {
    id: "dashboard.payment.checkout",
    node: "dashboard",
    route: "/dashboard",
    selector: "[data-testid='checkout-submit']",
    risk: "payment",
    defaultRun: false,
  },
];

export function graphEdgesForDefaultRun() {
  return graphEdges.filter((edge) => (
    edge.defaultRun !== false
    && edge.risk !== "payment"
    && edge.risk !== "voice"
    && edge.risk !== "external"
  ));
}
