import { expect, type Page, test } from "@playwright/test";

import { graphEdgesForDefaultRun, type GraphEdge } from "./guardian.graph";

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

const fbarProduct = {
  sku: "fbar_check",
  name: "FBAR Check",
  public_name: "FBAR Check",
  description: "Review whether an FBAR filing is likely needed.",
  public_description: "Review whether an FBAR filing is likely needed.",
  price_cents: 0,
  tier: "standard",
  requires_attorney: false,
  requires_questionnaire: false,
  active: true,
  category: "tax",
  filing_method: "self_service",
  fulfillment_mode: "automated",
  headline: "Foreign account filing threshold review",
  public_headline: "Foreign account filing threshold review",
  highlights: ["Estimate aggregate balances", "Flag likely filing need"],
  public_highlights: ["Estimate aggregate balances", "Flag likely filing need"],
  cta_label: "Start FBAR check",
  public_cta_label: "Start FBAR check",
  path: "/services/fbar_check",
};

const dashboardTimeline = {
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
  service_summary: {
    active_orders: [],
    recent_completed: [],
    recommended_services: [
      {
        sku: "fbar_check",
        name: "FBAR Check",
        reason: "Tax records indicate a foreign-account review may be useful.",
        priority: 1,
        product: fbarProduct,
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

function jsonResponse(body: unknown) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

async function installDashboardMocks(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("guardian_token", "graph-test-token");
    window.localStorage.setItem("guardian_user_id", "graph-test-user");
    window.localStorage.setItem("guardian_email", "graph-test@example.com");
  });

  await page.route("**/api/dashboard/timeline", (route) => route.fulfill(jsonResponse(dashboardTimeline)));
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
  await page.route("**/api/professional-search/mine/list", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/me/engagements", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/marketplace/products/fbar_check**", (route) => route.fulfill(jsonResponse(fbarProduct)));
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function assertGraphExpectation(page: Page, edge: GraphEdge) {
  if (!edge.expect) return;

  if (edge.expect.urlPath) {
    await expect(page).toHaveURL(new RegExp(`${escapeRegex(edge.expect.urlPath)}(?:$|[?#])`));
  }

  if (edge.expect.testId) {
    const target = page.getByTestId(edge.expect.testId);
    await expect(target).toBeVisible();
    if (edge.expect.text) {
      await expect(target).toContainText(edge.expect.text);
    }
  }

  if (edge.expect.hiddenTestId) {
    await expect(page.getByTestId(edge.expect.hiddenTestId)).toBeHidden();
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

      await installDashboardMocks(page);
      await page.goto(edge.route);
      await expect(page.getByTestId("dashboard-root")).toBeVisible();

      for (const step of edge.before ?? []) {
        await expect(page.locator(step.selector)).toHaveCount(1);
        await page.locator(step.selector).click();
      }

      const transition = page.locator(edge.selector);
      await expect(transition).toHaveCount(1);
      await transition.click();

      await assertGraphExpectation(page, edge);
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
      expect(failedResponses).toEqual([]);
    });
  }
});
