import { expect, type Page, test } from "@playwright/test";

import { graphEdgesForDefaultRun, type GraphEdge } from "./guardian.graph";

function marketplaceProduct(overrides: Partial<Record<string, unknown>> & { sku: string; name: string }) {
  return {
    sku: overrides.sku,
    name: overrides.name,
    public_name: overrides.name,
    description: `${overrides.name} description`,
    public_description: `${overrides.name} description`,
    price_cents: overrides.price_cents ?? 0,
    tier: "standard",
    requires_attorney: Boolean(overrides.requires_attorney),
    requires_questionnaire: Boolean(overrides.requires_questionnaire),
    active: overrides.active ?? true,
    category: overrides.category ?? "tax",
    filing_method: overrides.filing_method ?? "self_service",
    fulfillment_mode: overrides.fulfillment_mode ?? "automated",
    headline: overrides.headline ?? `${overrides.name} headline`,
    public_headline: overrides.headline ?? `${overrides.name} headline`,
    highlights: overrides.highlights ?? ["Review the facts", "Prepare the next step"],
    public_highlights: overrides.highlights ?? ["Review the facts", "Prepare the next step"],
    cta_label: overrides.cta_label ?? "View service",
    public_cta_label: overrides.public_cta_label ?? overrides.cta_label ?? "View service",
    path: overrides.path ?? `/services/${overrides.sku}`,
  };
}

const products = {
  form8843: marketplaceProduct({
    sku: "form_8843_free",
    name: "Form 8843 (Free)",
    cta_label: "Generate for free",
    path: "/form-8843",
  }),
  studentTax: marketplaceProduct({
    sku: "student_tax_1040nr",
    name: "Student Tax Filing",
    cta_label: "Start student tax package",
  }),
  h1b: marketplaceProduct({
    sku: "h1b_doc_check",
    name: "H-1B Document Check",
    cta_label: "Start document review",
  }),
  fbar: marketplaceProduct({
    sku: "fbar_check",
    name: "FBAR Check",
    cta_label: "Start FBAR check",
  }),
  election83b: marketplaceProduct({
    sku: "election_83b",
    name: "83(b) Election Filing",
    cta_label: "Start 83(b) packet",
  }),
  optExecution: marketplaceProduct({
    sku: "opt_execution",
    name: "OPT Filing Support",
    cta_label: "Check my OPT case",
    category: "immigration",
    requires_attorney: true,
    requires_questionnaire: true,
  }),
  optAdvisory: marketplaceProduct({
    sku: "opt_advisory",
    name: "OPT Strategy Review",
    cta_label: "Check my OPT case",
    category: "immigration",
    requires_attorney: true,
    requires_questionnaire: true,
  }),
};

const productList = [
  products.form8843,
  products.studentTax,
  products.h1b,
  products.fbar,
  products.election83b,
  products.optExecution,
  products.optAdvisory,
];

const dashboardDocuments = [
  {
    id: "doc-tax-return",
    filename: "2025-tax-return.pdf",
    doc_type: "tax_return",
    file_size: 142_000,
    uploaded_at: "2026-04-01T12:00:00Z",
    category: "tax",
  },
  {
    id: "doc-i20",
    filename: "latest-i20.pdf",
    doc_type: "i20",
    file_size: 96_000,
    uploaded_at: "2026-04-03T12:00:00Z",
    category: "student_status",
  },
];

const baseDashboardTimeline = {
  events: [
    {
      date: "2026-04-01",
      title: "Tax return uploaded",
      type: "filing",
      category: "tax",
      chain: null,
      documents: [
        {
          id: "doc-tax-return",
          filename: "2025-tax-return.pdf",
          doc_type: "tax_return",
          category: "tax",
        },
      ],
      risks: [],
    },
    {
      date: "2026-04-03",
      title: "I-20 reviewed",
      type: "milestone",
      category: "student_status",
      chain: null,
      documents: [
        {
          id: "doc-i20",
          filename: "latest-i20.pdf",
          doc_type: "i20",
          category: "student_status",
        },
      ],
      risks: [
        {
          id: "risk-opt-window",
          title: "OPT timing needs review",
          action: "Confirm the EAD and program dates still align.",
          consequence: "Missed deadline",
          immigration_impact: true,
          severity: "warning",
          documents: [
            {
              id: "doc-i20",
              filename: "latest-i20.pdf",
              doc_type: "i20",
              category: "student_status",
            },
          ],
        },
      ],
    },
  ],
  findings: [],
  advisories: [
    {
      id: "advisory-fbar",
      title: "FBAR threshold review",
      action: "Check aggregate foreign account balances.",
      consequence: "Filing may be needed",
    },
  ],
  integrity_issues: [],
  assistant_prompts: [],
  upload_prompts: [],
  key_facts: [
    { label: "Visa status", value: "F-1", category: "student_status" },
    { label: "Tax residency", value: "Nonresident alien", category: "tax" },
  ],
  deadlines: [
    {
      title: "Form 8843 filing deadline",
      date: "2026-06-15",
      days: 51,
      category: "tax",
      severity: "medium",
      action: "Mail the completed Form 8843 packet.",
    },
  ],
};

const recommendedDashboardTimeline = {
  ...baseDashboardTimeline,
  service_summary: {
    active_orders: [],
    recent_completed: [],
    recommended_services: [
      {
        sku: "fbar_check",
        name: "FBAR Check",
        reason: "Tax records indicate a foreign-account review may be useful.",
        priority: 1,
        product: products.fbar,
        href: "/services/fbar_check",
        cta_label: "Start FBAR check",
      },
    ],
    service_deadlines: [],
    stats: {
      active_orders: 0,
      recent_completed: 0,
      recommended_services: 1,
    },
  },
};

const activeOrderDashboardTimeline = {
  ...baseDashboardTimeline,
  service_summary: {
    active_orders: [
      {
        order_id: "order-fbar-active",
        product_sku: "fbar_check",
        product_name: "FBAR Check",
        product: products.fbar,
        status: "draft",
        status_label: "Draft",
        attention_state: "active",
        summary: "Review the FinCEN guidance and file if the threshold was met.",
        next_action: "Run FBAR check",
        filing_deadline: null,
        deadline_days: null,
        mailing_status: "not_required",
        href: "/account/orders/order-fbar-active",
        cta_label: "Run FBAR check",
      },
    ],
    recent_completed: [],
    recommended_services: [],
    service_deadlines: [],
    stats: {
      active_orders: 1,
      recent_completed: 0,
      recommended_services: 0,
    },
  },
};

function marketplaceOrder(overrides: Partial<Record<string, unknown>> & { order_id: string; product_sku: keyof typeof orderProducts }) {
  const product = orderProducts[overrides.product_sku];
  return {
    user_id: "graph-user",
    order_id: overrides.order_id,
    product_sku: product.sku,
    status: overrides.status ?? "completed",
    amount_cents: overrides.amount_cents ?? product.price_cents,
    created_at: "2026-04-01T12:00:00Z",
    updated_at: "2026-04-02T12:00:00Z",
    completed_at: overrides.completed_at ?? "2026-04-02T12:00:00Z",
    delivery_method: overrides.delivery_method ?? "user_mail",
    filing_deadline: overrides.filing_deadline ?? null,
    mailing_status: overrides.mailing_status ?? "not_required",
    mailed_at: null,
    tracking_number: null,
    product,
    intake_complete: overrides.intake_complete ?? true,
    result_ready: overrides.result_ready ?? true,
    questionnaire_response_id: overrides.questionnaire_response_id ?? null,
    chosen_mode: overrides.chosen_mode ?? null,
    intake_preview: overrides.intake_preview ?? { seeded: true },
    agreement_signed: overrides.agreement_signed ?? false,
    agreement: null,
    attorney_assignment: null,
    summary: `${product.public_name} summary`,
    finding_count: 0,
    next_steps: ["Review the output"],
    artifacts: [],
    pdf_url: null,
    email_status: null,
    mailing_service_available: false,
    result: {
      order_id: overrides.order_id,
      product_sku: product.sku,
      summary: `${product.public_name} result ready.`,
      findings: [],
      finding_count: 0,
      next_steps: ["Review the output"],
      artifacts: [],
    },
  };
}

const orderProducts = {
  election_83b: products.election83b,
  fbar_check: products.fbar,
  h1b_doc_check: products.h1b,
  opt_execution: products.optExecution,
};

const orders = [
  marketplaceOrder({ order_id: "order-83b", product_sku: "election_83b" }),
  marketplaceOrder({
    order_id: "order-fbar-active",
    product_sku: "fbar_check",
    status: "draft",
    completed_at: null,
    intake_complete: true,
    result_ready: false,
    mailing_status: "not_required",
  }),
  marketplaceOrder({ order_id: "order-h1b", product_sku: "h1b_doc_check" }),
  marketplaceOrder({
    order_id: "order-opt",
    product_sku: "opt_execution",
    status: "draft",
    completed_at: null,
    result_ready: false,
    agreement_signed: false,
    questionnaire_response_id: "questionnaire-response",
  }),
];

const questionnaireConfig = {
  service: "opt_execution",
  title: "Find the right OPT lane",
  description: "Guardian uses this checklist to route the case toward the right attorney-backed workflow.",
  sections: [
    {
      id: "eligibility",
      title: "Eligibility basics",
      required_for_execution: "all_checked",
      items: [
        { id: "has_i20", label: "I have an OPT-recommended I-20." },
        { id: "has_passport", label: "My passport is valid." },
      ],
    },
    {
      id: "complexity",
      title: "Complexity flags",
      required_for_execution: "all_unchecked",
      items: [
        { id: "prior_denial", label: "I have a prior OPT denial." },
      ],
    },
  ],
};

const questionnaireResult = {
  questionnaire_response_id: "questionnaire-response",
  recommendation: "execution",
  advisory_reason: null,
  execution_reason: "The checked facts fit the filing-support lane.",
  missing_required_items: [],
  complexity_flags: [],
};

function jsonResponse(body: unknown, status = 200) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

function productBySku(sku: string) {
  return productList.find((product) => product.sku === sku) || products.fbar;
}

function orderById(orderId: string) {
  return orders.find((order) => order.order_id === orderId) || orders[0];
}

async function installGraphMocks(page: Page, edge: GraphEdge) {
  await page.addInitScript(() => {
    window.localStorage.setItem("guardian_token", "graph-test-token");
    window.localStorage.setItem("guardian_user_id", "graph-test-user");
    window.localStorage.setItem("guardian_email", "graph-test@example.com");
  });

  const timeline = edge.mockProfile === "dashboard-active-order"
    ? activeOrderDashboardTimeline
    : recommendedDashboardTimeline;

  await page.route("**/api/dashboard/timeline", (route) => route.fulfill(jsonResponse(timeline)));
  await page.route("**/api/dashboard/stats", (route) => route.fulfill(jsonResponse({
    documents: dashboardDocuments.length,
    risks: 1,
    verified: 2,
    next_deadline_days: 51,
  })));
  await page.route("**/api/dashboard/documents", (route) => route.fulfill(jsonResponse(dashboardDocuments)));
  await page.route("**/api/dashboard/documents/*/view", (route) => route.fulfill({
    status: 200,
    contentType: "application/pdf",
    body: "mock document",
  }));
  await page.route("**/api/dashboard/upload/prepare", (route) => route.fulfill(jsonResponse({ files: [] })));
  await page.route("**/api/professional-search/mine/list", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/me/engagements", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/cases", (route) => route.fulfill(jsonResponse({ cases: [] })));
  await page.route("**/api/subscription/me", (route) => route.fulfill(jsonResponse({
    tier: "free",
    is_pro: false,
    subscription: null,
    extraction_quota: {
      used: 1,
      limit: 10,
      remaining: 9,
      at_limit: false,
      reset_at: "2026-05-01T00:00:00Z",
    },
    pro_search_quota: {
      used: 0,
      limit: null,
      has_free_search: false,
      period_end: null,
    },
    limits: {
      free_extractions_per_month: 10,
      pro_free_searches_per_period: 1,
    },
  })));
  await page.route("**/api/auth/openclaw/connection", (route) => route.fulfill(jsonResponse({
    api_url: "https://guardiancompliance.app/mcp/sse",
    install_command: "openclaw skills install guardian-compliance",
    env_var: "GUARDIAN_TOKEN",
    token_type: "openclaw",
    scope: "read_write",
    active_token: {
      label: "OpenClaw",
      token_prefix: "gdn_oc_mock",
      created_at: "2026-04-01T12:00:00Z",
    },
  })));
  await page.route("**/api/auth/openclaw/token", (route) => route.fulfill(jsonResponse({
    api_url: "https://guardiancompliance.app/mcp/sse",
    install_command: "openclaw skills install guardian-compliance",
    env_var: "GUARDIAN_TOKEN",
    token_type: "openclaw",
    scope: "read_write",
    active_token: {
      label: "OpenClaw",
      token_prefix: "gdn_oc_mock2",
      created_at: "2026-04-02T12:00:00Z",
    },
    token: "gdn_oc_mock_token_value_for_graph_tests",
  })));

  await page.route("**/api/marketplace/products**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const productMatch = url.pathname.match(/\/api\/marketplace\/products\/([^/]+)(?:\/questionnaire)?$/);
    const isQuestionnaire = url.pathname.endsWith("/questionnaire");
    if (productMatch && isQuestionnaire && request.method() === "POST") {
      await route.fulfill(jsonResponse(questionnaireResult));
      return;
    }
    if (productMatch && isQuestionnaire) {
      await route.fulfill(jsonResponse(questionnaireConfig));
      return;
    }
    if (productMatch) {
      await route.fulfill(jsonResponse(productBySku(decodeURIComponent(productMatch[1]))));
      return;
    }
    await route.fulfill(jsonResponse({ products: productList }));
  });

  await page.route("**/api/marketplace/orders**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const orderMatch = url.pathname.match(/\/api\/marketplace\/orders\/([^/]+)(?:\/([^/]+))?$/);
    if (url.pathname.endsWith("/api/marketplace/orders") && request.method() === "POST") {
      await route.fulfill(jsonResponse(marketplaceOrder({
        order_id: "order-created",
        product_sku: "fbar_check",
        status: "draft",
        completed_at: null,
        result_ready: false,
      })));
      return;
    }
    if (url.pathname.endsWith("/api/marketplace/orders")) {
      await route.fulfill(jsonResponse({ orders }));
      return;
    }
    if (orderMatch?.[2] === "pull-extracted-info") {
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        order,
        prefill: {
          coverage: "mocked",
          summary: "No extracted fields were needed for this graph test.",
          applied_field_names: [],
          missing_fields: [],
          source_documents: [],
        },
      }));
      return;
    }
    if (orderMatch) {
      await route.fulfill(jsonResponse(orderById(orderMatch[1])));
      return;
    }
    await route.fulfill(jsonResponse({ orders }));
  });
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function assertGraphExpectation(page: Page, edge: GraphEdge, popup?: Page) {
  if (!edge.expect) return;

  if (edge.expect.urlPath) {
    await expect(page).toHaveURL(new RegExp(`${escapeRegex(edge.expect.urlPath)}(?:$|[?#])`));
  }

  if (edge.expect.popupUrlPath) {
    expect(popup, `${edge.id} should open a popup`).toBeTruthy();
  }

  if (edge.expect.testId) {
    const target = page.getByTestId(edge.expect.testId);
    await expect(target).toBeVisible();
    if (edge.expect.text) {
      await expect(target).toContainText(edge.expect.text);
    }
  }

  if (edge.expect.selector) {
    const target = page.locator(edge.expect.selector);
    await expect(target).toBeVisible();
    if (edge.expect.text) {
      await expect(target).toContainText(edge.expect.text);
    }
  }

  if (edge.expect.hiddenTestId) {
    await expect(page.getByTestId(edge.expect.hiddenTestId)).toBeHidden();
  }

  if (edge.expect.text && !edge.expect.testId && !edge.expect.selector) {
    await expect(page.locator("body")).toContainText(edge.expect.text);
  }

  if (edge.expect.pressed) {
    await expect(page.locator(edge.selector)).toHaveAttribute("aria-pressed", "true");
  }
}

test.describe("Guardian graph transitions", () => {
  for (const edge of graphEdgesForDefaultRun()) {
    test(edge.id, async ({ page }) => {
      const consoleErrors: string[] = [];
      const pageErrors: string[] = [];
      const failedResponses: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") {
          consoleErrors.push(message.text());
        }
      });
      page.on("pageerror", (error) => pageErrors.push(error.message));
      page.on("response", (response) => {
        const resourceType = response.request().resourceType();
        if (response.status() >= 400 && ["document", "fetch", "xhr"].includes(resourceType)) {
          failedResponses.push(`${response.status()} ${response.url()}`);
        }
      });

      if (edge.viewport) {
        await page.setViewportSize(edge.viewport);
      }
      await installGraphMocks(page, edge);
      await page.goto(edge.route);
      await page.waitForLoadState("domcontentloaded");

      for (const step of edge.before ?? []) {
        const beforeTransition = page.locator(step.selector);
        await expect(beforeTransition).toHaveCount(1);
        await beforeTransition.click();
      }

      const transition = page.locator(edge.selector);
      await expect(transition).toHaveCount(1);
      let popup: Page | undefined;
      if (edge.expect?.popupUrlPath) {
        const href = await transition.getAttribute("href");
        expect(href, `${edge.id} should point to a target URL`).toBeTruthy();
        expect(new URL(href!, page.url()).pathname).toBe(edge.expect.popupUrlPath);
        [popup] = await Promise.all([
          page.waitForEvent("popup"),
          transition.click(),
        ]);
      } else {
        await transition.click();
      }

      await assertGraphExpectation(page, edge, popup);
      await popup?.close().catch(() => undefined);
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
      expect(failedResponses).toEqual([]);
    });
  }
});
