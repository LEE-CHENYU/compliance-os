import path from "node:path";

import { expect, type Download, type Page, type Route, test } from "@playwright/test";

import { graphEdgesForDefaultRun, type GraphEdge, type GraphFailureKey } from "./guardian.graph";

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

const dashboardFacts = {
  facts: [
    {
      id: "fact-visa-status",
      fact_key: "current_immigration_status",
      label: "Current immigration status",
      category: "immigration",
      track: "shared",
      value: { v: "F-1" },
      notes: null,
      source_type: "document",
      source_ref: { document_id: "doc-i20", field_name: "class_of_admission" },
      locked_at: "2026-04-01T12:00:00Z",
      is_active: true,
      superseded_by_id: null,
      detected_conflicts: [],
      created_at: "2026-04-01T12:00:00Z",
      updated_at: "2026-04-01T12:00:00Z",
    },
    {
      id: "fact-tax-residency",
      fact_key: "tax_residency_classification",
      label: "Tax residency classification",
      category: "tax",
      track: "shared",
      value: { v: "Nonresident alien" },
      notes: null,
      source_type: "decision_lock",
      source_ref: { ui_path: "/dashboard/facts" },
      locked_at: "2026-04-02T12:00:00Z",
      is_active: true,
      superseded_by_id: null,
      detected_conflicts: [],
      created_at: "2026-04-02T12:00:00Z",
      updated_at: "2026-04-02T12:00:00Z",
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

const emptyDashboardTimeline = {
  ...baseDashboardTimeline,
  events: [],
  advisories: [],
  key_facts: [],
  deadlines: [],
  service_summary: {
    active_orders: [],
    recent_completed: [],
    recommended_services: [],
    service_deadlines: [],
    stats: {
      active_orders: 0,
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
    result: (overrides.result as Record<string, unknown> | undefined) ?? {
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
  opt_advisory: products.optAdvisory,
  student_tax_1040nr: products.studentTax,
};

const orders = [
  marketplaceOrder({ order_id: "order-83b", product_sku: "election_83b" }),
  marketplaceOrder({
    order_id: "order-83b-draft",
    product_sku: "election_83b",
    status: "draft",
    completed_at: null,
    intake_complete: false,
    result_ready: false,
    intake_preview: {},
  }),
  marketplaceOrder({
    order_id: "order-83b-ready",
    product_sku: "election_83b",
    status: "draft",
    completed_at: null,
    intake_complete: true,
    result_ready: false,
    intake_preview: {
      taxpayer_name: "Jessica Chen",
      taxpayer_address: "123 Startup Way, San Francisco, CA",
      company_name: "GraphCo, Inc.",
      property_description: "Restricted common stock",
      grant_date: "2026-04-01",
      share_count: "10000",
      fair_market_value_per_share: "0.02",
      exercise_price_per_share: "0.01",
      vesting_schedule: "25% after 12 months, monthly thereafter",
    },
  }),
  marketplaceOrder({
    order_id: "order-83b-result",
    product_sku: "election_83b",
    status: "completed",
    intake_complete: true,
    result_ready: true,
    mailing_status: "not_mailed",
    intake_preview: {
      taxpayer_name: "Jessica Chen",
      taxpayer_address: "123 Startup Way, San Francisco, CA",
      company_name: "GraphCo, Inc.",
      property_description: "Restricted common stock",
      grant_date: "2026-04-01",
      share_count: "10000",
      fair_market_value_per_share: "0.02",
      exercise_price_per_share: "0.01",
      vesting_schedule: "25% after 12 months, monthly thereafter",
    },
    result: {
      order_id: "order-83b-result",
      product_sku: "election_83b",
      summary: "83(b) packet result ready.",
      findings: [],
      finding_count: 0,
      next_steps: ["Print and mail the election."],
      artifacts: [{ label: "Election packet", filename: "83b-election.pdf", url: "/api/marketplace/orders/order-83b-result/artifacts/packet.pdf" }],
      mailing_instructions: {
        headline: "Mail the election",
        summary: "Mail the signed election to the IRS.",
        steps: ["Print", "Sign", "Mail"],
      },
    },
  }),
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
  marketplaceOrder({
    order_id: "order-opt-draft",
    product_sku: "opt_execution",
    status: "draft",
    completed_at: null,
    intake_complete: false,
    result_ready: false,
    agreement_signed: false,
    questionnaire_response_id: "questionnaire-response",
    intake_preview: {},
  }),
  marketplaceOrder({
    order_id: "order-opt-intake-complete",
    product_sku: "opt_execution",
    status: "draft",
    completed_at: null,
    result_ready: false,
    intake_complete: true,
    agreement_signed: false,
    questionnaire_response_id: "questionnaire-response",
    intake_preview: {
      client_intake: {
        desired_start_date: "2026-05-01",
        employment_plan_text: "Software engineering role related to field of study.",
      },
    },
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

const form8843Order = {
  order_id: "form8843-order",
  status: "completed",
  pdf_url: "/api/form8843/orders/form8843-order/pdf",
  email_status: "skipped",
  user_id: "graph-user",
  delivery_method: "user_mail",
  filing_deadline: "2026-06-15",
  mailing_status: "not_mailed",
  mailed_at: null,
  tracking_number: null,
  mailing_service_available: false,
  filing_instructions: {
    scenario: "standalone",
    headline: "Mail Form 8843",
    summary: "Print, sign, and mail the completed form.",
    filing_deadline: "2026-06-15",
    deadline_label: "June 15, 2026",
    address_block: "Department of the Treasury\nAustin, TX 73301-0215",
    delivery_method: "user_mail",
    mailing_status: "not_mailed",
    mail_required: true,
    can_mark_mailed: true,
    certified_mail_recommended: true,
    steps: ["Print the PDF", "Sign it", "Mail it"],
    mailing_service_available: false,
    mailing_service_price_cents: 0,
    mailing_service_note: "",
  },
};

const professionalSearchComplete = {
  id: "search-complete",
  status: "complete",
  purpose: "H-1B attorney shortlist",
  vertical: "immigration_attorney",
  case_brief: "A detailed attorney search brief for graph tests.",
  uploaded_notes: null,
  persona_status: {
    elite_boutique: { status: "complete", firm_count: 2 },
    startup_focused: { status: "complete", firm_count: 2 },
  },
  tier_report: [
    {
      firm: "Graph Immigration LLP",
      purpose: "H-1B attorney shortlist",
      status: "shortlisted",
      score: 92,
      priority: "high",
      next_action: "Schedule intro call",
      next_action_date: "2026-05-01",
      last_contact_date: null,
      lowest_quote: 3500,
      highest_quote: 5500,
      open_risks: 1,
    },
    {
      firm: "Startup Visa Counsel",
      purpose: "H-1B attorney shortlist",
      status: "shortlisted",
      score: 88,
      priority: "medium",
      next_action: "Ask fee quote",
      next_action_date: "2026-05-02",
      last_contact_date: null,
      lowest_quote: 3000,
      highest_quote: 5000,
      open_risks: 0,
    },
  ],
  error: null,
  created_at: "2026-04-01T12:00:00Z",
  completed_at: "2026-04-01T12:30:00Z",
  paid_at: null,
  is_paid: false,
  is_claimed: false,
  stripe_customer_email: null,
  case_id: "case-graph",
};

const professionalSearchCpaComplete = {
  ...professionalSearchComplete,
  id: "search-cpa",
  purpose: "Nonresident CPA and Form 5472 support",
  vertical: "cpa",
  case_brief: "A detailed CPA search brief for nonresident tax and foreign-owned LLC compliance.",
  persona_status: {
    international_tax: { status: "complete", firm_count: 2 },
    nra_entity_compliance: { status: "complete", firm_count: 2 },
  },
  tier_report: [
    {
      firm: "Graph International CPA",
      purpose: "Nonresident CPA and Form 5472 support",
      status: "shortlisted",
      score: 94,
      priority: "high",
      next_action: "Request fixed-fee quote",
      next_action_date: "2026-05-03",
      last_contact_date: null,
      lowest_quote: 900,
      highest_quote: 1800,
      open_risks: 0,
    },
    {
      firm: "NRA Tax Partners",
      purpose: "Nonresident CPA and Form 5472 support",
      status: "shortlisted",
      score: 89,
      priority: "medium",
      next_action: "Confirm Form 5472 scope",
      next_action_date: "2026-05-04",
      last_contact_date: null,
      lowest_quote: 1200,
      highest_quote: 2200,
      open_risks: 1,
    },
  ],
};

const professionalSearchPaid = {
  ...professionalSearchComplete,
  id: "search-paid",
  paid_at: "2026-04-01T12:35:00Z",
  is_paid: true,
};

const professionalSearchRunning = {
  ...professionalSearchComplete,
  id: "search-running",
  status: "running",
  completed_at: null,
  paid_at: null,
  is_paid: false,
  persona_status: {
    elite_boutique: { status: "complete", firm_count: 2 },
    startup_focused: { status: "running" },
  },
  tier_report: null,
} as const;

const professionalSearchFailed = {
  ...professionalSearchComplete,
  id: "search-failed",
  status: "failed",
  completed_at: "2026-04-01T12:20:00Z",
  paid_at: null,
  is_paid: false,
  error: "Graph search failed while collecting vendor evidence.",
  persona_status: {
    elite_boutique: { status: "failed", error: "Graph search failed" },
  },
  tier_report: null,
} as const;

const professionalSearchPaidUnclaimed = {
  ...professionalSearchPaid,
  is_claimed: false,
  stripe_customer_email: "graph@example.com",
};

const professionalSearchPaidClaimed = {
  ...professionalSearchPaid,
  is_claimed: true,
  stripe_customer_email: "graph@example.com",
};

const caseSearchSummaries = [
  {
    id: "search-complete",
    purpose: "H-1B attorney shortlist",
    vertical: "immigration_attorney",
    status: "complete",
    created_at: "2026-04-01T12:00:00Z",
    paid_at: null,
    firm_count: 2,
    top_firms: [
      { name: "Graph Immigration LLP", confidence: "high" },
      { name: "Startup Visa Counsel", confidence: "medium" },
    ],
  },
];

const caseDocumentSlots = [
  {
    key: "passport",
    label: "Passport",
    description: "Identity page",
    required: true,
    group: "Identity",
    order: 1,
  },
  {
    key: "i94",
    label: "I-94",
    description: "Most recent entry record",
    required: true,
    group: "Immigration",
    order: 2,
  },
];

const caseDocuments = [
  {
    id: "case-doc-passport",
    filename: "passport.pdf",
    classification: "passport",
    file_size: 218,
    slot_key: "passport",
    created_at: "2026-04-01T12:00:00Z",
  },
];

const caseUnassignedDocument = {
  id: "case-doc-unassigned",
  filename: "unassigned.pdf",
  classification: "i94",
  file_size: 218,
  slot_key: null,
  created_at: "2026-04-01T12:00:00Z",
};

const baseEngagement = {
  id: "engagement-graph",
  case_id: "case-graph",
  search_id: "search-complete",
  firm_name: "Graph Immigration LLP",
  firm_emails: ["intake@graphimmigration.example"],
  firm_phone: null,
  firm_website: null,
  firm_lead_attorney: "Graph Partner",
  status: "not_contacted",
  notes: null,
  created_at: "2026-04-01T12:00:00Z",
  last_activity_at: "2026-04-01T12:00:00Z",
};

const attorneyUser = {
  attorney_id: "attorney-graph",
  full_name: "Graph Attorney",
  email: "attorney@example.com",
  bar_state: "CA",
  bar_number: "123456",
  bar_verified: true,
  languages: ["English"],
  location: "San Francisco, CA",
};

const attorneyAssignment = {
  assignment_id: "assignment-graph",
  attorney_id: attorneyUser.attorney_id,
  decision: "pending_review",
  assigned_at: "2026-04-01T12:00:00Z",
  reviewed_at: null,
  completed_at: null,
  checklist_responses: {},
  attorney_notes: null,
  attorney: attorneyUser,
};

const attorneyCaseResponse = {
  order: {
    ...orderById("order-opt-intake-complete"),
    status: "attorney_review",
    attorney_assignment: attorneyAssignment,
  },
  assignment: attorneyAssignment,
  agreement: {
    agreement_id: "agreement-graph",
    signed_at: "2026-04-01T12:00:00Z",
    user_signature: "Jessica Chen",
    agreement_text: "Limited scope agreement for graph testing.",
  },
  checklist: {
    service: "opt_execution",
    checklist: [
      { id: "identity", label: "Identity documents reviewed" },
      { id: "eligibility", label: "Eligibility facts reviewed" },
    ],
    decision: {},
  },
  intake_data: {
    desired_start_date: "2026-05-01",
  },
  result: {},
};

const checkAnswersById: Record<string, Record<string, unknown>> = {
  "student-check": {
    student_status: "enrolled_cpt",
    has_cpt_authorization: "yes",
    cpt_fulltime_months: "1-6",
    income_reporting: "sprintax",
    planning_travel: "no",
  },
  "entity-check": {
    entity_type: "smllc",
    owner_residency: "on_visa",
    visa_type: "f1_opt_stem",
    state_of_formation: "Delaware",
  },
  "stem-check": {
    stage: "stem_opt",
    years_in_us: 3,
    employment_status: "employed",
    employer_changed: "no",
  },
};

function checkFor(id: string, track?: string) {
  const inferredTrack = track || (id.includes("entity") ? "entity" : id.includes("stem") ? "stem_opt" : "student");
  return {
    id,
    track: inferredTrack,
    stage: "intake",
    status: "active",
    answers: checkAnswersById[id] || {},
    created_at: "2026-04-01T12:00:00Z",
    updated_at: "2026-04-01T12:00:00Z",
  };
}

function snapshotFor(id: string, track?: string) {
  const check = checkFor(id, track);
  return {
    check,
    extractions: {
      i983: [
        { id: "field-start", document_id: "doc-i983", field_name: "start_date", field_value: "2026-01-01", confidence: 0.98, raw_text: null },
        { id: "field-end", document_id: "doc-i983", field_name: "end_date", field_value: "2026-12-31", confidence: 0.98, raw_text: null },
      ],
    },
    document_extractions: [],
    comparisons: [
      { id: "cmp-1", check_id: id, field_name: "name", value_a: "Jessica Chen", value_b: "Jessica Chen", match_type: "exact", status: "match", confidence: 0.99, detail: null },
    ],
    findings: [
      { id: "finding-1", check_id: id, rule_id: "graph-advisory", severity: "info", category: "advisory", title: "No blocking issue found", action: "Keep records.", consequence: "Recordkeeping", immigration_impact: false },
    ],
    followups: [],
    advisories: [],
  };
}

const sharePackage = {
  template_name: "H-1B Data Room",
  expires_at: Math.floor(new Date("2026-06-01T00:00:00Z").getTime() / 1000),
  files_scanned: 1,
  summary: {
    title: "Shared case package",
    prepared_for: "Jessica Chen",
    prepared_by: "Guardian",
    date: "2026-04-01",
    overview: "Graph test share package.",
    key_facts: [{ label: "Status", value: "H-1B" }],
    timeline: [],
    issues: [],
    pending_items: [],
    open_questions: [],
  },
  coverage: { identity: 1 },
  recipient: "Jessica Chen",
  issuer: "Guardian",
  missing_required: [],
  missing_optional: [],
  unmatched_files: [],
  lineage_issues: [],
  misplaced: [],
  sections: [
    {
      code: "identity",
      name: "Identity",
      slots: [
        {
          id: "passport",
          title: "Passport",
          description: "Identity document",
          required: true,
          order: 1,
          phase: "identity",
          status: "matched",
          file: "passport.pdf",
          score: 0.98,
        },
      ],
    },
  ],
};

function jsonResponse(body: unknown, status = 200) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

const failureMessages: Record<GraphFailureKey, string> = {
  "auth-login": "Graph forced auth failure",
  "auth-register": "Graph forced registration failure",
  "dashboard-timeline": "Graph forced dashboard timeline failure",
  "dashboard-stats": "Graph forced dashboard stats failure",
  "dashboard-documents": "Graph forced dashboard documents failure",
  "dashboard-openclaw-connection": "Graph forced OpenClaw connection failure",
  "dashboard-openclaw-token": "Graph forced OpenClaw token failure",
  "dashboard-upload-prepare": "Graph forced dashboard upload prepare failure",
  "dashboard-upload-submit": "Graph forced dashboard upload submit failure",
  "dashboard-upload-quota": "Graph forced dashboard upload quota failure",
  "dashboard-document-open": "Graph forced document open failure",
  "dashboard-chat": "Graph forced dashboard chat failure",
  "dashboard-form-fill-extract": "Graph forced form-fill extract failure",
  "dashboard-form-fill-generate": "Graph forced form-fill generate failure",
  "services-list": "Graph forced services list failure",
  "service-detail": "Graph forced service detail failure",
  "service-start-order": "Graph forced service start order failure",
  "questionnaire-load": "Graph forced questionnaire load failure",
  "questionnaire-evaluate": "Graph forced questionnaire evaluate failure",
  "questionnaire-order": "Graph forced questionnaire order failure",
  "find-lawyer-prefill": "Graph forced find lawyer prefill failure",
  "find-lawyer-submit": "Graph forced professional search submit failure",
  "professional-search-status": "Graph forced professional search status failure",
  "professional-search-track": "Graph forced professional search track failure",
  "professional-search-download": "Graph forced professional search download failure",
  "professional-search-paid": "Graph forced professional search paid failure",
  "professional-search-checkout": "Graph forced professional search checkout failure",
  "professional-search-claim": "Graph forced professional search claim failure",
  "professional-search-trial": "Graph forced professional search trial failure",
  "case-load": "Graph forced case load failure",
  "case-gmail-connect": "Graph forced Gmail connect failure",
  "case-gmail-sync": "Graph forced Gmail sync failure",
  "case-gmail-disconnect": "Graph forced Gmail disconnect failure",
  "case-engagement-add": "Graph forced case engagement failure",
  "case-engagement-update": "Graph forced case engagement update failure",
  "case-engagement-delete": "Graph forced case engagement delete failure",
  "case-engagement-draft-email": "Graph forced case engagement email failure",
  "case-document-upload": "Graph forced case document upload failure",
  "case-document-update": "Graph forced case document update failure",
  "case-document-delete": "Graph forced case document delete failure",
  "attorney-dashboard": "Graph forced attorney dashboard failure",
  "attorney-case": "Graph forced attorney case failure",
  "attorney-review": "Graph forced attorney review failure",
  "account-orders": "Graph forced account orders failure",
  "order-detail": "Graph forced order detail failure",
  "order-prefill": "Graph forced order prefill failure",
  "order-save-intake": "Graph forced order intake failure",
  "order-process": "Graph forced order process failure",
  "order-mark-mailed": "Graph forced order mark mailed failure",
  "agreement-load": "Graph forced agreement load failure",
  "agreement-sign": "Graph forced agreement sign failure",
  "form8843-generate": "Graph forced Form 8843 generate failure",
  "form8843-success": "Graph forced Form 8843 success failure",
  "form8843-download": "Graph forced Form 8843 download failure",
  "form8843-mark-mailed": "Graph forced Form 8843 mark mailed failure",
  "check-create": "Graph forced check create failure",
  "check-upload-load": "Graph forced check upload load failure",
  "check-upload-submit": "Graph forced check upload submit failure",
  "check-review-extract": "Graph forced check review extract failure",
  "share-load": "Graph forced share load failure",
};

function failureResponse(key: GraphFailureKey, status = 500) {
  return jsonResponse({ detail: failureMessages[key] }, status);
}

function expectMultipartField(payload: string, field: string, value: string) {
  expect(payload, `multipart request should include ${field}=${value}`).toMatch(
    new RegExp(`name="${field}"[\\s\\S]*?\\r?\\n\\r?\\n${value}(?:\\r?\\n|--)`),
  );
}

function shouldFail(edge: GraphEdge, key: GraphFailureKey) {
  return edge.mockFailure === key;
}

function productBySku(sku: string) {
  return productList.find((product) => product.sku === sku) || products.fbar;
}

function orderById(orderId: string) {
  return orders.find((order) => order.order_id === orderId) || orders[0];
}

async function installGraphMocks(page: Page, edge: GraphEdge) {
  await page.addInitScript((mockProfile) => {
    if (mockProfile === "new-user-signup") {
      if (!window.sessionStorage.getItem("__guardian_graph_signup_initialized")) {
        window.localStorage.removeItem("guardian_token");
        window.localStorage.removeItem("guardian_user_id");
        window.localStorage.removeItem("guardian_email");
        window.localStorage.removeItem("guardian_role");
        window.sessionStorage.setItem("__guardian_graph_signup_initialized", "1");
      }
    } else if (mockProfile === "professional-search-paid-unclaimed") {
      window.localStorage.removeItem("guardian_token");
      window.localStorage.removeItem("guardian_user_id");
      window.localStorage.removeItem("guardian_email");
      window.localStorage.removeItem("guardian_role");
    } else {
      window.localStorage.setItem("guardian_token", "graph-test-token");
      window.localStorage.setItem("guardian_user_id", "graph-test-user");
      window.localStorage.setItem("guardian_email", "graph-test@example.com");
    }
    if (mockProfile === "attorney" || mockProfile === "attorney-approved") {
      window.localStorage.setItem("guardian_role", "attorney");
    } else {
      window.localStorage.removeItem("guardian_role");
    }
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: () => Promise.resolve(),
      },
    });
    const graphWindow = window as typeof window & {
      __guardianGraphVapiFactory?: () => {
        on: (event: string, handler: (payload?: unknown) => void) => void;
        start: () => Promise<void>;
        send: () => void;
        stop: () => Promise<void>;
        removeAllListeners: () => void;
      };
    };
    graphWindow.__guardianGraphVapiFactory = () => {
      const listeners = new Map<string, Array<(payload?: unknown) => void>>();
      const emit = (event: string, payload?: unknown) => {
        for (const handler of listeners.get(event) || []) {
          handler(payload);
        }
      };
      return {
        on: (event, handler) => {
          listeners.set(event, [...(listeners.get(event) || []), handler]);
        },
        start: async () => {
          window.setTimeout(() => {
            emit("call-start");
            emit("message", {
              type: "transcript",
              role: "assistant",
              transcript: "Mock voice review started.",
            });
          }, 0);
        },
        send: () => {},
        stop: async () => {
          emit("call-end");
        },
        removeAllListeners: () => {
          listeners.clear();
        },
      };
    };
  }, edge.mockProfile || null);

  let syntheticHasOnboarded = false;
  const dashboardTimelineForEdge = () => edge.mockProfile === "dashboard-active-order"
    ? activeOrderDashboardTimeline
    : (edge.mockProfile === "new-user" || (edge.mockProfile === "new-user-signup" && !syntheticHasOnboarded))
      ? emptyDashboardTimeline
      : recommendedDashboardTimeline;
  const dashboardDocumentsForEdge = () => edge.mockProfile === "new-user"
    || (edge.mockProfile === "new-user-signup" && !syntheticHasOnboarded)
    || edge.mockProfile === "dashboard-empty-docs"
    ? []
    : dashboardDocuments;
  let trackedEngagements: Array<Record<string, unknown>> = edge.mockProfile === "case-engagements"
    ? [{ ...baseEngagement }]
    : [];
  let graphCaseDocuments = edge.mockProfile === "case-documents-unassigned"
    ? [caseDocuments[0], caseUnassignedDocument]
    : edge.mockProfile === "new-user-signup"
      ? []
    : [...caseDocuments];

  await page.route("**/api/auth/login", (route) => (
    shouldFail(edge, "auth-login")
      ? route.fulfill(failureResponse("auth-login"))
      : route.fulfill(jsonResponse({
        token: "graph-login-token",
        user_id: "graph-user",
        email: "test@123.com",
        role: "user",
      }))
  ));
  await page.route("**/api/auth/register", (route) => (
    shouldFail(edge, "auth-register")
      ? route.fulfill(failureResponse("auth-register"))
      : route.fulfill(jsonResponse({
        token: "graph-register-token",
        user_id: "graph-user",
        email: "graph@example.com",
        role: "user",
      }))
  ));
  await page.route("**/api/auth/google/url**", (route) => route.fulfill(jsonResponse({
    url: "https://accounts.google.com/o/oauth2/v2/auth?graph=1",
  })));

  await page.route("**/api/dashboard/timeline", (route) => (
    shouldFail(edge, "dashboard-timeline")
      ? route.fulfill(failureResponse("dashboard-timeline"))
      : route.fulfill(jsonResponse(dashboardTimelineForEdge()))
  ));
  await page.route("**/api/dashboard/stats", (route) => (
    shouldFail(edge, "dashboard-stats")
      ? route.fulfill(failureResponse("dashboard-stats"))
      : route.fulfill(jsonResponse({
    documents: dashboardDocumentsForEdge().length,
    risks: 1,
    verified: 2,
    next_deadline_days: 51,
  }))
  ));
  await page.route("**/api/facts/summary", (route) => route.fulfill(jsonResponse({
    summary: "Guardian summary: you appear to be in F-1 status with nonresident tax treatment and a Form 8843 deadline coming up.",
    generated_by: "llm",
  })));
  await page.route("**/api/facts", (route) => route.fulfill(jsonResponse(dashboardFacts)));
  await page.route("**/api/facts/*/resolve", (route) => route.fulfill(jsonResponse({ ok: true, facts: [] })));
  await page.route("**/api/dashboard/documents/delete", (route) => route.fulfill(jsonResponse({ ok: true, deleted: ["doc-tax-return", "doc-i20"] })));
  await page.route("**/api/dashboard/documents", (route) => (
    shouldFail(edge, "dashboard-documents")
      ? route.fulfill(failureResponse("dashboard-documents"))
      : route.fulfill(jsonResponse(dashboardDocumentsForEdge()))
  ));
  await page.route("**/api/dashboard/documents/*/view", (route) => (
    shouldFail(edge, "dashboard-document-open")
      ? route.fulfill(failureResponse("dashboard-document-open"))
      : route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "mock document",
      })
  ));
  const preparedDashboardUpload = {
    files: [
      edge.mockProfile === "dashboard-upload-review"
        ? {
          file_name: "graph-document.pdf",
          mime_type: "application/pdf",
          file_size: 220,
          resolved_doc_type: "tax_return",
          classification_source: "mock",
          confidence: "high",
          status: "duplicate",
          message: "Graph duplicate candidate detected",
          content_hash: "graph-hash",
          duplicates: [{
            id: "doc-tax-return",
            check_id: "dashboard",
            filename: "2025-tax-return.pdf",
            doc_type: "tax_return",
            source_path: null,
            uploaded_at: "2026-04-01T12:00:00Z",
            is_active: true,
            content_hash: "graph-hash",
          }],
        }
        : {
          file_name: "graph-document.pdf",
          mime_type: "application/pdf",
          file_size: 220,
          resolved_doc_type: "tax_return",
          classification_source: "mock",
          confidence: "high",
          status: "ready",
          message: null,
          content_hash: "graph-hash",
          duplicates: [],
        },
    ],
  };
  const completedDashboardUpload = {
    id: "uploaded-graph-doc",
    filename: "graph-document.pdf",
    doc_type: "tax_return",
    status: "processed",
  };
  await page.route("**/api/dashboard/upload/prepare", (route) => (
    shouldFail(edge, "dashboard-upload-prepare")
      ? route.fulfill(failureResponse("dashboard-upload-prepare"))
      : route.fulfill(jsonResponse(preparedDashboardUpload))
  ));
  await page.route("**/api/dashboard/upload", (route) => (
    shouldFail(edge, "dashboard-upload-quota")
      ? route.fulfill(jsonResponse({
        detail: {
          code: "extraction_quota_exceeded",
          tier: "free",
          used: 10,
          limit: 10,
          reset_at: "2026-05-01T00:00:00Z",
          upgrade_url: "/pricing",
          message: failureMessages["dashboard-upload-quota"],
        },
      }, 402))
      : shouldFail(edge, "dashboard-upload-submit")
      ? route.fulfill(failureResponse("dashboard-upload-submit"))
      : (syntheticHasOnboarded = true, route.fulfill(jsonResponse(completedDashboardUpload)))
  ));
  await page.route("**/api/upload/prepare", (route) => route.fulfill(jsonResponse(preparedDashboardUpload)));
  await page.route("**/api/upload", (route) => (
    shouldFail(edge, "dashboard-upload-quota")
      ? route.fulfill(jsonResponse({
        detail: {
          code: "extraction_quota_exceeded",
          tier: "free",
          used: 10,
          limit: 10,
          reset_at: "2026-05-01T00:00:00Z",
          upgrade_url: "/pricing",
          message: failureMessages["dashboard-upload-quota"],
        },
      }, 402))
      : shouldFail(edge, "dashboard-upload-submit")
      ? route.fulfill(failureResponse("dashboard-upload-submit"))
      : (syntheticHasOnboarded = true, route.fulfill(jsonResponse(completedDashboardUpload)))
  ));
  await page.route("**/api/chat", (route) => (
    shouldFail(edge, "dashboard-chat")
      ? route.fulfill(failureResponse("dashboard-chat"))
      : route.fulfill(jsonResponse({
        reply: "Graph assistant reply: upload the missing document and review your next deadline.",
        references: [{ id: "doc-tax-return", filename: "2025-tax-return.pdf", doc_type: "tax_return", score: 0.92 }],
      }))
  ));
  await page.route("**/api/chat/answer", (route) => route.fulfill(jsonResponse({ ok: true })));
  await page.route("**/api/form-fill/extract", (route) => (
    shouldFail(edge, "dashboard-form-fill-extract")
      ? route.fulfill(failureResponse("dashboard-form-fill-extract"))
      : route.fulfill(jsonResponse({
        fields: [
          {
            field_name: "full_name",
            field_type: "text",
            field_label: "Full name",
            field_context: "Applicant name",
            page: 1,
            proposed_value: "Jessica Chen",
            confidence: "high",
            source: "Graph fixture",
          },
        ],
        form_field_count: 1,
        filled_count: 1,
        unfilled_count: 0,
      }))
  ));
  await page.route("**/api/form-fill/generate", (route) => (
    shouldFail(edge, "dashboard-form-fill-generate")
      ? route.fulfill(failureResponse("dashboard-form-fill-generate"))
      : route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.4\n%%EOF",
      })
  ));
  const fulfillProfessionalSearch = async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const match = url.pathname.match(/\/api\/professional-search(?:\/([^/]+))?(?:\/([^/]+))?$/);
    if (url.pathname === "/api/professional-search" && request.method() === "POST") {
      if (shouldFail(edge, "find-lawyer-submit")) {
        await route.fulfill(failureResponse("find-lawyer-submit"));
        return;
      }
      if (edge.mockProfile === "professional-search-cpa") {
        const payload = request.postData() ?? "";
        expectMultipartField(payload, "vertical", "cpa");
        expectMultipartField(payload, "purpose", "Nonresident CPA and Form 5472 support");
        await route.fulfill(jsonResponse(professionalSearchCpaComplete));
        return;
      }
      await route.fulfill(jsonResponse(professionalSearchComplete));
      return;
    }
    if (match?.[2] === "checkout") {
      if (shouldFail(edge, "professional-search-checkout")) {
        await route.fulfill(failureResponse("professional-search-checkout"));
        return;
      }
      await route.fulfill(jsonResponse({ url: "/find-lawyer/search-paid/paid?session_id=cs_graph" }));
      return;
    }
    if (match?.[2] === "start-pro-trial") {
      if (shouldFail(edge, "professional-search-trial")) {
        await route.fulfill(failureResponse("professional-search-trial"));
        return;
      }
      await route.fulfill(jsonResponse({ ok: true, trial_days: 30 }));
      return;
    }
    if (match?.[2] === "marketplace-match") {
      await route.fulfill(jsonResponse([
        {
          sku: "opt_execution",
          name: "OPT Filing Support",
          public_name: "OPT Filing Support",
          description: "Attorney-backed filing support.",
          public_description: "Attorney-backed filing support.",
          price_cents: 35000,
          headline: "Attorney-supported OPT packet",
          public_headline: "Attorney-supported OPT packet",
          cta_label: "Open service",
          public_cta_label: "Open service",
          path: "/services/opt_execution",
          match_score: 0.92,
          match_reason: "Matches immigration filing support",
        },
      ]));
      return;
    }
    if (match?.[2] === "download") {
      if (shouldFail(edge, "professional-search-download")) {
        await route.fulfill(failureResponse("professional-search-download"));
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: url.searchParams.get("format") === "pdf" ? "application/pdf" : "text/html",
        body: url.searchParams.get("format") === "pdf" ? "%PDF-1.4\n%%EOF" : "<html><body>Graph report</body></html>",
      });
      return;
    }
    if (match?.[2] === "claim") {
      if (shouldFail(edge, "professional-search-claim")) {
        await route.fulfill(failureResponse("professional-search-claim"));
        return;
      }
      await route.fulfill(jsonResponse(professionalSearchPaidClaimed));
      return;
    }
    if (match?.[1]) {
      if (shouldFail(edge, "professional-search-status") && match[1] === "search-complete") {
        await route.fulfill(failureResponse("professional-search-status"));
        return;
      }
      if (shouldFail(edge, "professional-search-paid") && match[1] === "search-paid") {
        await route.fulfill(failureResponse("professional-search-paid"));
        return;
      }
      if (match[1] === "search-running") {
        await route.fulfill(jsonResponse(professionalSearchRunning));
        return;
      }
      if (match[1] === "search-failed") {
        await route.fulfill(jsonResponse(professionalSearchFailed));
        return;
      }
      if (match[1] === "search-cpa") {
        await route.fulfill(jsonResponse(professionalSearchCpaComplete));
        return;
      }
      if (match[1] === "search-paid") {
        const paidRow = edge.mockProfile === "professional-search-paid-claimed"
          ? professionalSearchPaidClaimed
          : edge.mockProfile === "professional-search-paid-unclaimed"
            ? professionalSearchPaidUnclaimed
            : professionalSearchPaid;
        await route.fulfill(jsonResponse(paidRow));
        return;
      }
      await route.fulfill(jsonResponse(professionalSearchComplete));
      return;
    }
    await route.fulfill(jsonResponse(professionalSearchComplete));
  };
  await page.context().route("**/api/professional-search**", fulfillProfessionalSearch);
  await page.route("**/api/professional-search/mine/list", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/me/engagements", (route) => route.fulfill(jsonResponse([])));
  await page.route("**/api/me/activity-context", (route) => route.fulfill(jsonResponse({ text: "Graph activity context." })));
  await page.route("**/api/cases", (route) => {
    if (route.request().method() === "POST") {
      syntheticHasOnboarded = true;
      route.fulfill(jsonResponse({
        id: "case-graph",
        workflow_type: "immigration",
        status: "active",
        created_at: "2026-04-01T12:00:00Z",
        updated_at: "2026-04-01T12:00:00Z",
        document_count: 0,
        answer_count: 0,
      }));
      return;
    }
    route.fulfill(jsonResponse({ cases: edge.mockProfile === "new-user" || edge.mockProfile === "new-user-signup" ? [] : [{ id: "case-graph", workflow_type: "immigration", status: "active" }] }));
  });
  await page.route("**/api/cases/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/professional-searches")) {
      await route.fulfill(jsonResponse(edge.mockProfile === "case-empty-searches" ? [] : caseSearchSummaries));
      return;
    }
    if (url.pathname.endsWith("/draft-brief")) {
      if (shouldFail(edge, "find-lawyer-prefill")) {
        await route.fulfill(failureResponse("find-lawyer-prefill"));
        return;
      }
      await route.fulfill(jsonResponse({
        brief: "Graph case brief with enough details for a professional search.",
        suggested_vertical: "immigration_attorney",
        suggested_purpose: "Attorney shortlist",
      }));
      return;
    }
    if (url.pathname.endsWith("/documents/checklist")) {
      await route.fulfill(jsonResponse({
        slots: caseDocumentSlots,
        filled: Object.fromEntries(graphCaseDocuments.filter((document) => document.slot_key).map((document) => [document.slot_key, document.id])),
      }));
      return;
    }
    if (url.pathname.endsWith("/documents") && request.method() === "POST") {
      if (shouldFail(edge, "case-document-upload")) {
        await route.fulfill(failureResponse("case-document-upload"));
        return;
      }
      const uploaded = {
        id: "case-doc-uploaded",
        filename: "graph-document.pdf",
        classification: "i94",
        file_size: 218,
        slot_key: null,
        created_at: "2026-04-01T12:00:00Z",
      };
      graphCaseDocuments = [...graphCaseDocuments, uploaded];
      await route.fulfill(jsonResponse(uploaded));
      return;
    }
    if (url.pathname.endsWith("/documents")) {
      await route.fulfill(jsonResponse({ documents: graphCaseDocuments }));
      return;
    }
    const documentMatch = url.pathname.match(/\/api\/cases\/case-graph\/documents\/([^/]+)$/);
    if (documentMatch && request.method() === "PATCH") {
      if (shouldFail(edge, "case-document-update")) {
        await route.fulfill(failureResponse("case-document-update"));
        return;
      }
      const body = request.postDataJSON() as { slot_key?: string };
      graphCaseDocuments = graphCaseDocuments.map((document) => (
        document.id === documentMatch[1]
          ? { ...document, slot_key: body.slot_key ?? document.slot_key }
          : document
      ));
      await route.fulfill(jsonResponse(graphCaseDocuments.find((document) => document.id === documentMatch[1]) || graphCaseDocuments[0]));
      return;
    }
    if (documentMatch && request.method() === "DELETE") {
      if (shouldFail(edge, "case-document-delete")) {
        await route.fulfill(failureResponse("case-document-delete"));
        return;
      }
      graphCaseDocuments = graphCaseDocuments.filter((document) => document.id !== documentMatch[1]);
      await route.fulfill(jsonResponse({ ok: true }));
      return;
    }
    if (url.pathname.endsWith("/discovery/summary")) {
      await route.fulfill(jsonResponse({ summary: { status: "ready" } }));
      return;
    }
    if (url.pathname.endsWith("/discovery") && request.method() === "POST") {
      const body = request.postDataJSON() as { step?: string; question_key?: string; answer?: unknown };
      await route.fulfill(jsonResponse({
        id: "answer-graph",
        case_id: "case-graph",
        step: body.step || "concern_area",
        question_key: body.question_key || "concern_area",
        answer: body.answer ?? [],
        created_at: "2026-04-01T12:00:00Z",
      }));
      return;
    }
    if (url.pathname.endsWith("/discovery")) {
      await route.fulfill(jsonResponse({ answers: [] }));
      return;
    }
    if (url.pathname.endsWith("/chat") && request.method() === "POST") {
      await route.fulfill(jsonResponse({
        messages: [
          { id: "chat-user", role: "user", content: "Graph question", created_at: "2026-04-01T12:00:00Z" },
          { id: "chat-assistant", role: "assistant", content: "Graph answer", created_at: "2026-04-01T12:00:00Z" },
        ],
      }));
      return;
    }
    if (url.pathname.endsWith("/chat")) {
      await route.fulfill(jsonResponse({ messages: [] }));
      return;
    }
    if (url.pathname.endsWith("/threads")) {
      await route.fulfill(jsonResponse([
        {
          id: "thread-graph",
          gmail_thread_id: "gmail-thread-graph",
          subject: "Graph intro",
          last_message_at: "2026-04-02T12:00:00Z",
          last_message_snippet: "Thanks for reaching out.",
          last_message_from: "attorney@example.com",
          last_message_direction: "inbound",
          message_count: 2,
        },
      ]));
      return;
    }
    if (url.pathname.endsWith("/draft-email")) {
      if (shouldFail(edge, "case-engagement-draft-email")) {
        await route.fulfill(failureResponse("case-engagement-draft-email"));
        return;
      }
      await route.fulfill(jsonResponse({
        to: ["intake@graphimmigration.example"],
        subject: "H-1B transfer consultation",
        body: "Hello, I would like to schedule a consultation.",
      }));
      return;
    }
    if (url.pathname.endsWith("/engagements") && request.method() === "POST") {
      if (shouldFail(edge, "professional-search-track")) {
        await route.fulfill(failureResponse("professional-search-track"));
        return;
      }
      if (shouldFail(edge, "case-engagement-add")) {
        await route.fulfill(failureResponse("case-engagement-add"));
        return;
      }
      let firmName = "Graph Immigration LLP";
      try {
        firmName = (request.postDataJSON() as { firm_name?: string }).firm_name || firmName;
      } catch {
        firmName = "Graph Immigration LLP";
      }
      const nextEngagement = {
        id: `engagement-${Date.now()}`,
        case_id: "case-graph",
        search_id: "search-complete",
        firm_name: firmName,
        firm_emails: [],
        firm_phone: null,
        firm_website: null,
        firm_lead_attorney: null,
        status: "not_contacted",
        notes: null,
        created_at: "2026-04-01T12:00:00Z",
        last_activity_at: "2026-04-01T12:00:00Z",
      };
      trackedEngagements = [...trackedEngagements, nextEngagement];
      await route.fulfill(jsonResponse(nextEngagement));
      return;
    }
    if (url.pathname.endsWith("/engagements")) {
      await route.fulfill(jsonResponse(trackedEngagements));
      return;
    }
    const engagementMatch = url.pathname.match(/\/api\/cases\/case-graph\/engagements\/([^/]+)$/);
    if (engagementMatch && request.method() === "PATCH") {
      if (shouldFail(edge, "case-engagement-update")) {
        await route.fulfill(failureResponse("case-engagement-update"));
        return;
      }
      const body = request.postDataJSON() as Partial<typeof baseEngagement>;
      trackedEngagements = trackedEngagements.map((engagement) => (
        engagement.id === engagementMatch[1]
          ? { ...engagement, ...body, last_activity_at: "2026-04-02T12:00:00Z" }
          : engagement
      ));
      await route.fulfill(jsonResponse(trackedEngagements.find((engagement) => engagement.id === engagementMatch[1]) || baseEngagement));
      return;
    }
    if (engagementMatch && request.method() === "DELETE") {
      if (shouldFail(edge, "case-engagement-delete")) {
        await route.fulfill(failureResponse("case-engagement-delete"));
        return;
      }
      trackedEngagements = trackedEngagements.filter((engagement) => engagement.id !== engagementMatch[1]);
      await route.fulfill(jsonResponse({ ok: true }));
      return;
    }
    if (shouldFail(edge, "case-load") && url.pathname === "/api/cases/case-graph") {
      await route.fulfill(failureResponse("case-load", 404));
      return;
    }
    await route.fulfill(jsonResponse({
      id: "case-graph",
      workflow_type: "immigration",
      status: "active",
      created_at: "2026-04-01T12:00:00Z",
      updated_at: "2026-04-01T12:00:00Z",
      document_count: 1,
      answer_count: 2,
    }));
  });
  await page.route("**/api/auth/me/gmail/status", (route) => route.fulfill(jsonResponse({
    connected: shouldFail(edge, "case-gmail-sync") || edge.mockProfile === "case-gmail-connected" || shouldFail(edge, "case-gmail-disconnect"),
    granted_at: "2026-04-01T12:00:00Z",
    email: "graph@example.com",
  })));
  await page.route("**/api/auth/me/gmail/sync**", (route) => (
    shouldFail(edge, "case-gmail-sync")
      ? route.fulfill(failureResponse("case-gmail-sync"))
      : route.fulfill(jsonResponse({
    skipped: false,
    messages_scanned: 2,
    threads_matched: 1,
    threads_new: 1,
    summary: "Graph Gmail sync summary.",
  }))
  ));
  await page.route("**/api/auth/google/connect-gmail/url**", (route) => (
    shouldFail(edge, "case-gmail-connect")
      ? route.fulfill(failureResponse("case-gmail-connect"))
      : route.fulfill(jsonResponse({
    url: "https://accounts.google.com/o/oauth2/v2/auth?graph=1",
  }))
  ));
  await page.route("**/api/auth/me/gmail/disconnect", (route) => (
    shouldFail(edge, "case-gmail-disconnect")
      ? route.fulfill(failureResponse("case-gmail-disconnect"))
      : route.fulfill(jsonResponse({ ok: true }))
  ));
  await page.route("**/api/attorney/dashboard", (route) => (
    shouldFail(edge, "attorney-dashboard")
      ? route.fulfill(failureResponse("attorney-dashboard"))
      : route.fulfill(jsonResponse({
    attorney: attorneyUser,
    pending_cases: [
      {
        order_id: "order-opt-intake-complete",
        product_sku: "opt_execution",
        status: "attorney_review",
        decision: "pending_review",
        assigned_at: "2026-04-01T12:00:00Z",
        client_email: "jessica@example.com",
        client_name: "Jessica Chen",
      },
    ],
    completed_cases: [],
    stats: {
      pending_review: 1,
      completed_reviews: 0,
      total_cases: 1,
    },
  }))
  ));
  await page.route("**/api/attorney/cases/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/review")) {
      if (shouldFail(edge, "attorney-review")) {
        await route.fulfill(failureResponse("attorney-review"));
        return;
      }
      const reviewedAssignment = {
        ...attorneyAssignment,
        decision: (request.postDataJSON() as { decision?: string }).decision || "approve",
        reviewed_at: "2026-04-02T12:00:00Z",
        checklist_responses: { identity: true, eligibility: true },
        attorney_notes: "Graph review notes",
      };
      await route.fulfill(jsonResponse({
        order: { ...attorneyCaseResponse.order, status: "ready_for_filing", attorney_assignment: reviewedAssignment },
        assignment: reviewedAssignment,
      }));
      return;
    }
    if (url.pathname.endsWith("/file")) {
      await route.fulfill(jsonResponse({
        order: { ...attorneyCaseResponse.order, status: "filed" },
        receipt_number: "IOE1234567890",
      }));
      return;
    }
    if (shouldFail(edge, "attorney-case")) {
      await route.fulfill(failureResponse("attorney-case", 404));
      return;
    }
    if (edge.mockProfile === "attorney-approved") {
      const approvedAssignment = {
        ...attorneyAssignment,
        decision: "approve",
        reviewed_at: "2026-04-02T12:00:00Z",
        checklist_responses: { identity: true, eligibility: true },
        attorney_notes: "Approved in graph setup",
      };
      await route.fulfill(jsonResponse({
        ...attorneyCaseResponse,
        order: { ...attorneyCaseResponse.order, status: "ready_for_filing", attorney_assignment: approvedAssignment },
        assignment: approvedAssignment,
      }));
      return;
    }
    await route.fulfill(jsonResponse(attorneyCaseResponse));
  });
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
  await page.route("**/api/auth/openclaw/connection", (route) => (
    shouldFail(edge, "dashboard-openclaw-connection")
      ? route.fulfill(failureResponse("dashboard-openclaw-connection"))
      : route.fulfill(jsonResponse({
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
  }))
  ));
  await page.route("**/api/auth/openclaw/token", (route) => (
    shouldFail(edge, "dashboard-openclaw-token")
      ? route.fulfill(failureResponse("dashboard-openclaw-token"))
      : route.fulfill(jsonResponse({
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
  }))
  ));

  await page.route("**/api/marketplace/products**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const productMatch = url.pathname.match(/\/api\/marketplace\/products\/([^/]+)(?:\/questionnaire)?$/);
    const isQuestionnaire = url.pathname.endsWith("/questionnaire");
    if (productMatch && isQuestionnaire && request.method() === "POST") {
      if (shouldFail(edge, "questionnaire-evaluate")) {
        await route.fulfill(failureResponse("questionnaire-evaluate"));
        return;
      }
      await route.fulfill(jsonResponse(questionnaireResult));
      return;
    }
    if (productMatch && isQuestionnaire) {
      await route.fulfill(jsonResponse(questionnaireConfig));
      return;
    }
    if (productMatch) {
      if (shouldFail(edge, "service-detail")) {
        await route.fulfill(failureResponse("service-detail"));
        return;
      }
      if (shouldFail(edge, "questionnaire-load")) {
        await route.fulfill(failureResponse("questionnaire-load"));
        return;
      }
      await route.fulfill(jsonResponse(productBySku(decodeURIComponent(productMatch[1]))));
      return;
    }
    if (shouldFail(edge, "services-list")) {
      await route.fulfill(failureResponse("services-list"));
      return;
    }
    await route.fulfill(jsonResponse({ products: productList }));
  });

  await page.route("**/api/marketplace/orders**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const artifactMatch = url.pathname.match(/\/api\/marketplace\/orders\/([^/]+)\/artifacts\/(.+)$/);
    if (artifactMatch) {
      await route.fulfill({ status: 200, contentType: "application/pdf", body: "%PDF-1.4\n%%EOF" });
      return;
    }
    const orderMatch = url.pathname.match(/\/api\/marketplace\/orders\/([^/]+)(?:\/([^/]+))?$/);
    if (url.pathname.endsWith("/api/marketplace/orders") && request.method() === "POST") {
      if (shouldFail(edge, "service-start-order")) {
        await route.fulfill(failureResponse("service-start-order"));
        return;
      }
      if (shouldFail(edge, "questionnaire-order")) {
        await route.fulfill(failureResponse("questionnaire-order"));
        return;
      }
      let sku = "fbar_check";
      try {
        sku = (request.postDataJSON() as { sku?: string }).sku || sku;
      } catch {
        sku = "fbar_check";
      }
      await route.fulfill(jsonResponse(marketplaceOrder({
        order_id: "order-created",
        product_sku: sku as keyof typeof orderProducts,
        status: "draft",
        completed_at: null,
        intake_complete: false,
        result_ready: false,
      })));
      return;
    }
    if (url.pathname.endsWith("/api/marketplace/orders")) {
      if (shouldFail(edge, "account-orders")) {
        await route.fulfill(failureResponse("account-orders"));
        return;
      }
      await route.fulfill(jsonResponse({ orders }));
      return;
    }
    if (orderMatch?.[2] === "pull-extracted-info") {
      if (shouldFail(edge, "order-prefill")) {
        await route.fulfill(failureResponse("order-prefill"));
        return;
      }
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        order,
        prefill: {
          coverage: "mocked",
          summary: "mocked prefill applied",
          applied_field_names: [],
          missing_fields: [],
          source_documents: [],
        },
      }));
      return;
    }
    if (orderMatch?.[2] === "intake") {
      if (shouldFail(edge, "order-save-intake")) {
        await route.fulfill(failureResponse("order-save-intake"));
        return;
      }
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        ...order,
        intake_complete: true,
        result_ready: false,
      }));
      return;
    }
    if (orderMatch?.[2] === "process") {
      if (shouldFail(edge, "order-process")) {
        await route.fulfill(failureResponse("order-process"));
        return;
      }
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        ...order,
        status: "completed",
        completed_at: "2026-04-02T12:00:00Z",
        intake_complete: true,
        result_ready: true,
        result: {
          ...(order.result || {}),
          order_id: order.order_id,
          product_sku: order.product_sku,
          summary: `${order.product.public_name || order.product.name} result ready.`,
          findings: [],
          finding_count: 0,
          next_steps: ["Review the generated output."],
          artifacts: [{ label: "Generated packet", filename: "packet.pdf", url: `/api/marketplace/orders/${order.order_id}/artifacts/packet.pdf` }],
        },
      }));
      return;
    }
    if (orderMatch?.[2] === "mark-mailed") {
      if (shouldFail(edge, "order-mark-mailed")) {
        await route.fulfill(failureResponse("order-mark-mailed"));
        return;
      }
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        ...order,
        mailing_status: "mailed",
        mailed_at: "2026-04-02T12:00:00Z",
        tracking_number: "9407100000000000123456",
      }));
      return;
    }
    if (orderMatch?.[2] === "result") {
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse(order.result || {
        order_id: order.order_id,
        product_sku: order.product_sku,
        summary: `${order.product.public_name || order.product.name} result ready.`,
        findings: [],
        finding_count: 0,
        next_steps: ["Review the generated output."],
        artifacts: [],
      }));
      return;
    }
    if (orderMatch?.[2] === "agreement") {
      if (shouldFail(edge, "agreement-load")) {
        await route.fulfill(failureResponse("agreement-load"));
        return;
      }
      await route.fulfill(jsonResponse({
        order_id: orderMatch[1],
        agreement_text: `${"Limited scope agreement.\n".repeat(80)}End of agreement.`,
        signed: false,
        agreement: null,
      }));
      return;
    }
    if (orderMatch?.[2] === "sign-agreement") {
      if (shouldFail(edge, "agreement-sign")) {
        await route.fulfill(failureResponse("agreement-sign"));
        return;
      }
      const order = orderById(orderMatch[1]);
      await route.fulfill(jsonResponse({
        agreement_id: "agreement-graph",
        signed_at: "2026-04-02T12:00:00Z",
        order: { ...order, agreement_signed: true },
        attorney_assignment: null,
      }));
      return;
    }
    if (orderMatch?.[2] === "artifacts") {
      await route.fulfill({ status: 200, contentType: "application/pdf", body: "%PDF-1.4\n%%EOF" });
      return;
    }
    if (orderMatch) {
      if (shouldFail(edge, "order-detail")) {
        await route.fulfill(failureResponse("order-detail", 404));
        return;
      }
      await route.fulfill(jsonResponse(orderById(orderMatch[1])));
      return;
    }
    await route.fulfill(jsonResponse({ orders }));
  });

  await page.route("**/api/form8843/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/api/form8843/generate") && request.method() === "POST") {
      if (shouldFail(edge, "form8843-generate")) {
        await route.fulfill(failureResponse("form8843-generate"));
        return;
      }
      await route.fulfill(jsonResponse(form8843Order));
      return;
    }
    if (url.pathname.endsWith("/mark-mailed")) {
      if (shouldFail(edge, "form8843-mark-mailed")) {
        await route.fulfill(failureResponse("form8843-mark-mailed"));
        return;
      }
      await route.fulfill(jsonResponse({
        ...form8843Order,
        mailing_status: "mailed",
        mailed_at: "2026-04-02T12:00:00Z",
        tracking_number: "9407100000000000123456",
      }));
      return;
    }
    if (url.pathname.endsWith("/mailing-kit")) {
      await route.fulfill(jsonResponse({
        order_id: "form8843-order",
        mailing_status: "not_mailed",
        filing_deadline: "2026-06-15",
        address_block: "Department of the Treasury\nAustin, TX 73301-0215",
        filing_notes: "Print and mail.",
        mailing_label_text: "Mail to IRS",
        envelope_template_text: "Envelope",
        recommended_service: "USPS Certified Mail",
      }));
      return;
    }
    if (url.pathname.endsWith("/pdf")) {
      if (shouldFail(edge, "form8843-download")) {
        await route.fulfill(failureResponse("form8843-download"));
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/pdf", body: "%PDF-1.4\n%%EOF" });
      return;
    }
    if (shouldFail(edge, "form8843-success")) {
      await route.fulfill(failureResponse("form8843-success", 404));
      return;
    }
    await route.fulfill(jsonResponse(form8843Order));
  });

  await page.route("**/api/checks**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/checks" && request.method() === "POST") {
      if (shouldFail(edge, "check-create")) {
        await route.fulfill(failureResponse("check-create"));
        return;
      }
      const body = request.postDataJSON() as { track?: string };
      const id = body.track === "entity" ? "entity-check" : body.track === "stem_opt" ? "stem-check" : "student-check";
      syntheticHasOnboarded = true;
      await route.fulfill(jsonResponse(checkFor(id, body.track)));
      return;
    }
    const match = url.pathname.match(/\/api\/checks\/([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?$/);
    const checkId = match?.[1] || "student-check";
    const action = match?.[2];
    if (action === "documents" && request.method() === "POST") {
      if (shouldFail(edge, "check-upload-submit")) {
        await route.fulfill(failureResponse("check-upload-submit"));
        return;
      }
      await route.fulfill(jsonResponse({
        id: `doc-${checkId}`,
        check_id: checkId,
        doc_type: "i20",
        document_family: null,
        document_series_key: null,
        document_version: 1,
        supersedes_document_id: null,
        is_active: true,
        filename: "graph-document.pdf",
        source_path: null,
        file_size: 220,
        mime_type: "application/pdf",
        content_hash: "graph-hash",
        ocr_engine: null,
        provenance: null,
        uploaded_at: "2026-04-01T12:00:00Z",
      }));
      return;
    }
    if (action === "documents") {
      await route.fulfill(jsonResponse([]));
      return;
    }
    if (action === "extract") {
      if (shouldFail(edge, "check-review-extract")) {
        await route.fulfill(failureResponse("check-review-extract"));
        return;
      }
      await route.fulfill(jsonResponse({ status: "ok", documents: [] }));
      return;
    }
    if (action === "compare" || action === "comparisons") {
      await route.fulfill(jsonResponse([
        { id: "cmp-1", check_id: checkId, field_name: "name", value_a: "Jessica Chen", value_b: "Jessica Chen", match_type: "exact", status: "match", confidence: 0.99, detail: null },
      ]));
      return;
    }
    if (action === "followups") {
      await route.fulfill(jsonResponse([]));
      return;
    }
    if (action === "evaluate" || action === "findings") {
      await route.fulfill(jsonResponse([
        { id: "finding-1", check_id: checkId, rule_id: "graph-advisory", severity: "info", category: "advisory", title: "No blocking issue found", action: "Keep records.", consequence: "Recordkeeping", immigration_impact: false },
      ]));
      return;
    }
    if (action === "snapshot") {
      await route.fulfill(jsonResponse(snapshotFor(checkId)));
      return;
    }
    if (!action && shouldFail(edge, "check-upload-load")) {
      await route.fulfill(failureResponse("check-upload-load", 404));
      return;
    }
    await route.fulfill(jsonResponse(checkFor(checkId)));
  });

  await page.route("**/api/share/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/download")) {
      await route.fulfill({ status: 200, contentType: "application/zip", body: "mock zip" });
      return;
    }
    if (shouldFail(edge, "share-load")) {
      await route.fulfill(failureResponse("share-load", 404));
      return;
    }
    await route.fulfill(jsonResponse(sharePackage));
  });
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function runGraphStep(page: Page, step: NonNullable<GraphEdge["before"]>[number]) {
  const locator = page.locator(step.selector);
  const action = step.action || "click";
  if (action === "waitForSelector") {
    await expect(locator.first()).toBeVisible();
    return;
  }
  if (action === "fill") {
    await expect(locator).toHaveCount(1);
    await locator.fill(step.value || "");
    return;
  }
  if (action === "select") {
    await expect(locator).toHaveCount(1);
    await locator.selectOption(step.value || "");
    return;
  }
  if (action === "setInputFiles") {
    await expect(locator).toHaveCount(1);
    await locator.setInputFiles((step.files || []).map((file) => path.join(process.cwd(), file)));
    return;
  }
  if (action === "scrollToBottom") {
    await expect(locator).toHaveCount(1);
    await locator.evaluate((element) => {
      element.scrollTop = element.scrollHeight;
      element.dispatchEvent(new Event("scroll", { bubbles: true }));
    });
    return;
  }
  await expect(locator).toHaveCount(1);
  await locator.click();
}

async function assertGraphExpectation(page: Page, edge: GraphEdge, popup?: Page, download?: Download) {
  if (!edge.expect) return;

  if (edge.expect.urlPath) {
    await expect(page).toHaveURL(new RegExp(`${escapeRegex(edge.expect.urlPath)}(?:$|[?#])`));
  }

  if (edge.expect.hrefPath) {
    const href = await page.locator(edge.selector).getAttribute("href");
    expect(href, `${edge.id} should expose an href`).toBeTruthy();
    expect(new URL(href!, page.url()).pathname).toBe(edge.expect.hrefPath);
  }

  if (edge.expect.popupUrlPath) {
    expect(popup, `${edge.id} should open a popup`).toBeTruthy();
  }

  if (edge.expect.download) {
    expect(download, `${edge.id} should trigger a browser download`).toBeTruthy();
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
  test.describe.configure({ mode: "default" });

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
        await runGraphStep(page, step);
      }

      const transition = page.locator(edge.selector);
      if (edge.action !== "none") {
        await expect(transition).toHaveCount(1);
      }
      let popup: Page | undefined;
      let download: Download | undefined;
      if (edge.dialogAction) {
        page.once("dialog", async (dialog) => {
          if (edge.dialogAction === "accept") {
            await dialog.accept();
          } else {
            await dialog.dismiss();
          }
        });
      }
      if (edge.expect?.popupUrlPath) {
        const href = await transition.getAttribute("href");
        expect(href, `${edge.id} should point to a target URL`).toBeTruthy();
        expect(new URL(href!, page.url()).pathname).toBe(edge.expect.popupUrlPath);
        [popup] = await Promise.all([
          page.waitForEvent("popup"),
          transition.click(),
        ]);
      } else if (edge.expect?.download) {
        [download] = await Promise.all([
          page.waitForEvent("download"),
          transition.click({ force: edge.force }),
        ]);
      } else if (edge.action !== "none") {
        await transition.click({ force: edge.force });
      } else {
        await expect(page.locator(edge.selector).first()).toBeAttached();
      }

      await assertGraphExpectation(page, edge, popup, download);
      await popup?.close().catch(() => undefined);
      const unexpectedConsoleErrors = edge.expect?.failedResponsePath
        ? consoleErrors.filter((message) => !message.includes("Failed to load resource"))
        : consoleErrors;
      expect(unexpectedConsoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
      if (edge.expect?.failedResponsePath) {
        expect(
          failedResponses.some((response) => response.includes(edge.expect!.failedResponsePath!)),
          `${edge.id} should exercise ${edge.expect.failedResponsePath}`,
        ).toBeTruthy();
        expect(
          failedResponses.filter((response) => !response.includes(edge.expect!.failedResponsePath!)),
        ).toEqual([]);
      } else {
        expect(failedResponses).toEqual([]);
      }
    });
  }
});

const syntheticFixture = (name: string) => path.join(process.cwd(), "tests/fixtures/synthetic", name);

const syntheticNewUserEdge: GraphEdge = {
  id: "synthetic.new-user.signup-documents-processes",
  node: "dashboard",
  route: "/login?next=/dashboard",
  selector: "body",
  risk: "mutating",
  action: "none",
  mockProfile: "new-user-signup",
};

async function attachBrowserErrorCollectors(page: Page) {
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
  return { consoleErrors, pageErrors, failedResponses };
}

async function clickByTestId(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

async function fillByTestId(page: Page, testId: string, value: string) {
  await page.getByTestId(testId).fill(value);
}

async function uploadByTestId(page: Page, testId: string, ...files: string[]) {
  await page.getByTestId(testId).setInputFiles(files.map(syntheticFixture));
}

async function completeStudentCheck(page: Page) {
  await page.goto("/check/student");
  await clickByTestId(page, "student-intake-student_status-enrolled_cpt");
  await clickByTestId(page, "student-intake-has_cpt_authorization-yes");
  await clickByTestId(page, "student-intake-cpt_fulltime_months-1-6");
  await clickByTestId(page, "student-intake-income_reporting-sprintax");
  await clickByTestId(page, "student-intake-planning_travel-no");
  await clickByTestId(page, "student-intake-continue");
  await expect(page).toHaveURL(/\/check\/student\/upload\?id=student-check/);
  await uploadByTestId(page, "student-upload-input-i20", "synthetic-i20.pdf");
  await expect(page.getByText(/Uploaded/i).first()).toBeVisible();
  await clickByTestId(page, "student-upload-continue");
  await expect(page).toHaveURL(/\/check\/student\/review\?id=student-check/);
  await expect(page.locator("body")).toContainText(/No blocking issue found|Based on your I-20/i);
}

async function completeEntityCheck(page: Page) {
  await page.goto("/check/entity");
  await clickByTestId(page, "entity-intake-entity_type-smllc");
  await clickByTestId(page, "entity-intake-owner_residency-on_visa");
  await clickByTestId(page, "entity-intake-visa_type-f1_opt_stem");
  await fillByTestId(page, "entity-intake-state-of-formation", "Delaware");
  await clickByTestId(page, "entity-intake-separate_bank_account-yes");
  await clickByTestId(page, "entity-intake-foreign_capital_transfer-yes");
  await clickByTestId(page, "entity-intake-formation_age-this_year");
  await clickByTestId(page, "entity-intake-tax_software_used-sprintax");
  await clickByTestId(page, "entity-intake-continue");
  await expect(page).toHaveURL(/\/check\/entity\/upload\?id=entity-check/);
  await uploadByTestId(page, "entity-upload-input-tax-return", "synthetic-tax-return.pdf");
  await expect(page.getByText(/Uploaded/i).first()).toBeVisible();
  await clickByTestId(page, "entity-upload-continue");
  await expect(page).toHaveURL(/\/check\/entity\/review\?id=entity-check/);
  await expect(page.locator("body")).toContainText(/No blocking issue found|Snapshot|Looks Good/i);
}

async function completeStemCheck(page: Page) {
  await page.goto("/check/stem-opt");
  await clickByTestId(page, "stem-intake-stage-stem_opt");
  await fillByTestId(page, "stem-intake-years", "4");
  await clickByTestId(page, "stem-intake-employment_status-employed");
  await clickByTestId(page, "stem-intake-employer_changed-no");
  await clickByTestId(page, "stem-intake-tax_software_used-sprintax");
  await clickByTestId(page, "stem-intake-continue");
  await expect(page).toHaveURL(/\/check\/stem-opt\/upload\?id=stem-check/);
  await uploadByTestId(page, "stem-upload-input-employment_letter", "synthetic-employment-letter.pdf");
  await uploadByTestId(page, "stem-upload-input-i983", "synthetic-i983.pdf");
  await expect(page.getByText(/Uploaded/i).first()).toBeVisible();
  await clickByTestId(page, "stem-upload-continue");
  await expect(page).toHaveURL(/\/check\/stem-opt\/review\?id=stem-check/);
  await expect(page.locator("body")).toContainText(/No blocking issue found|Snapshot|Looks Good/i);
}

async function completeForm8843(page: Page) {
  await page.goto("/form-8843");
  await fillByTestId(page, "form8843-field-full_name", "Synthetic Newuser");
  await clickByTestId(page, "form8843-wizard-continue");
  await fillByTestId(page, "form8843-field-visa_type", "F-1");
  await fillByTestId(page, "form8843-field-arrival_date", "2024-08-15");
  await fillByTestId(page, "form8843-field-current_status", "F-1 student");
  await clickByTestId(page, "form8843-wizard-continue");
  await fillByTestId(page, "form8843-field-school_name", "Synthetic University");
  await fillByTestId(page, "form8843-field-school_address", "123 Campus Way");
  await clickByTestId(page, "form8843-wizard-continue");
  await fillByTestId(page, "form8843-field-citizenship_country", "Canada");
  await fillByTestId(page, "form8843-field-passport_country", "Canada");
  await fillByTestId(page, "form8843-field-passport_number", "SYN123456");
  await clickByTestId(page, "form8843-wizard-continue");
  await fillByTestId(page, "form8843-field-2025", "120");
  await fillByTestId(page, "form8843-field-2024", "140");
  await fillByTestId(page, "form8843-field-2023", "0");
  await clickByTestId(page, "form8843-wizard-continue");
  await fillByTestId(page, "form8843-field-home_country_address", "1 Synthetic Road, Toronto");
  await fillByTestId(page, "form8843-field-us_address", "123 Campus Way, Boston");
  await clickByTestId(page, "form8843-wizard-generate");
  await expect(page).toHaveURL(/\/form-8843\/success\?orderId=form8843-order/);
  await expect(page.locator("body")).toContainText(/Department of the Treasury|Download PDF/i);
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    clickByTestId(page, "form8843-success-download"),
  ]);
  expect(download).toBeTruthy();
  await clickByTestId(page, "form8843-copy-mailing-address");
  await expect(page.getByTestId("form8843-copy-mailing-address")).toContainText(/Copied/i);
  await clickByTestId(page, "form8843-success-start-another");
  await expect(page).toHaveURL(/\/form-8843$/);
}

test.describe("Guardian synthetic new-user process", () => {
  test("synthetic new user signs up and works through non-payment processes with fake documents", async ({ page }) => {
    test.setTimeout(180_000);
    const { consoleErrors, pageErrors, failedResponses } = await attachBrowserErrorCollectors(page);
    await installGraphMocks(page, syntheticNewUserEdge);

    await page.goto("/login?next=/dashboard");
    await clickByTestId(page, "login-toggle-register");
    await fillByTestId(page, "login-email", `synthetic+${Date.now()}@example.test`);
    await fillByTestId(page, "login-password", "synthetic123");
    await clickByTestId(page, "login-submit");
    await expect(page).toHaveURL(/\/(dashboard|check)(?:$|[?#])/);
    if (new URL(page.url()).pathname === "/check") {
      await expect(page.locator("body")).toContainText(/What do you want to check/i);
    }

    await completeStudentCheck(page);

    await page.goto("/dashboard");
    await expect(page.getByTestId("dashboard-open-upload-panel")).toBeVisible();
    await clickByTestId(page, "dashboard-open-upload-panel");
    await uploadByTestId(page, "dashboard-upload-file-input", "synthetic-i20.pdf");
    await expect(page.locator("body")).toContainText(/Dashboard updated|uploaded/i);

    await clickByTestId(page, "dashboard-view-profile");
    await clickByTestId(page, "dashboard-profile-ask-guardian");
    await fillByTestId(page, "dashboard-chat-input", "Use my synthetic documents to tell me the next compliance action.");
    await clickByTestId(page, "dashboard-chat-submit");
    await expect(page.getByTestId("dashboard-chat-messages")).toContainText(/Graph assistant reply/i);

    await clickByTestId(page, "chat-mode-form-filler");
    await uploadByTestId(page, "form-filler-file-input", "synthetic-brief.txt");
    await expect(page.getByTestId("form-filler-error")).toContainText(/Please upload a PDF file/i);
    await uploadByTestId(page, "form-filler-file-input", "synthetic-i20.pdf");
    await fillByTestId(page, "form-filler-instruction", "Fill the synthetic applicant name and status fields.");
    await clickByTestId(page, "form-filler-submit");
    await expect(page.getByTestId("form-preview-card")).toBeVisible();
    const [filledFormDownload] = await Promise.all([
      page.waitForEvent("download"),
      clickByTestId(page, "form-preview-generate"),
    ]);
    expect(filledFormDownload).toBeTruthy();

    await page.goto("/connect");
    await clickByTestId(page, "connect-app-codex");
    await clickByTestId(page, "connect-token-button");
    await expect(page.getByTestId("connect-copy-token")).toContainText(/Copy token/i);
    await clickByTestId(page, "connect-copy-config");
    await expect(page.getByTestId("connect-copy-config")).toContainText(/Copied/i);

    await completeEntityCheck(page);
    await completeStemCheck(page);

    await page.goto("/services");
    await clickByTestId(page, "services-product-opt_execution");
    await expect(page).toHaveURL(/\/services\/opt_execution/);
    await clickByTestId(page, "service-start-opt_execution");
    await expect(page).toHaveURL(/\/services\/opt_execution\/questionnaire/);
    await clickByTestId(page, "service-questionnaire-evaluate");
    await expect(page.locator("body")).toContainText(/Recommended plan/i);
    await clickByTestId(page, "service-questionnaire-mode-execution");
    await clickByTestId(page, "service-questionnaire-continue");
    await expect(page).toHaveURL(/\/account\/orders\/order-created/);

    await page.goto("/account/orders/order-83b-draft");
    await fillByTestId(page, "order-83b-taxpayer-name", "Synthetic Newuser");
    await fillByTestId(page, "order-83b-taxpayer-address", "123 Synthetic Way");
    await fillByTestId(page, "order-83b-company-name", "SyntheticCo, Inc.");
    await fillByTestId(page, "order-83b-grant-date", "2026-04-01");
    await fillByTestId(page, "order-83b-property-description", "Restricted common stock");
    await fillByTestId(page, "order-83b-share-count", "10000");
    await fillByTestId(page, "order-83b-fmv", "0.02");
    await fillByTestId(page, "order-83b-exercise-price", "0.01");
    await fillByTestId(page, "order-83b-vesting-schedule", "25% after 12 months, monthly thereafter");
    await clickByTestId(page, "order-detail-save-intake");
    await expect(page.locator("body")).toContainText(/83\(b\) intake saved/i);
    await page.goto("/account/orders/order-83b-ready");
    await clickByTestId(page, "order-detail-run-now");
    await expect(page.locator("body")).toContainText(/Processing complete/i);
    await page.goto("/account/orders/order-83b-result");
    const [artifactDownload] = await Promise.all([
      page.waitForEvent("download"),
      clickByTestId(page, "order-detail-artifact-83b-election-pdf"),
    ]);
    expect(artifactDownload).toBeTruthy();
    await fillByTestId(page, "order-detail-tracking-number", "9407100000000000123456");
    await clickByTestId(page, "order-detail-mark-mailed");
    await expect(page.locator("body")).toContainText(/Mailing confirmation saved/i);

    await page.goto("/account/orders/order-opt-draft");
    await fillByTestId(page, "order-opt-start-date", "2026-05-15");
    await fillByTestId(page, "order-opt-employment-plan", "Software engineering role related to degree program.");
    await uploadByTestId(page, "order-opt-file-i20", "synthetic-i20.pdf");
    await uploadByTestId(page, "order-opt-file-employment_plan", "synthetic-employment-letter.pdf");
    await clickByTestId(page, "order-detail-opt-save-intake");
    await expect(page.locator("body")).toContainText(/OPT intake saved/i);

    await page.goto("/case/new");
    await expect(page).toHaveURL(/\/case\/case-graph\/discovery/);
    await clickByTestId(page, "case-discovery-next");
    await expect(page.getByTestId("case-discovery-back")).toBeVisible();
    await clickByTestId(page, "case-discovery-back");
    await page.goto("/case/case-graph/documents");
    await uploadByTestId(page, "case-doc-general-upload-input", "synthetic-bank-statement.pdf");
    await expect(page.getByTestId("case-doc-row-case-doc-uploaded")).toBeVisible();
    await page.locator("[data-testid='case-doc-assign-case-doc-uploaded']").selectOption("i94");
    await expect(page.getByTestId("case-doc-slot-i94")).toBeVisible();
    await page.goto("/case/case-graph");
    await clickByTestId(page, "case-engagement-add-open");
    await fillByTestId(page, "case-engagement-new-name", "Synthetic Immigration LLP");
    await clickByTestId(page, "case-engagement-add-submit");
    await expect(page.locator("body")).toContainText(/Synthetic Immigration LLP/i);
    await page.locator("[data-testid^='case-engagement-status-']").first().selectOption("in_discussion");
    await expect(page.locator("body")).toContainText(/in discussion/i);

    await page.goto("/find-lawyer?case_id=case-graph");
    await fillByTestId(page, "find-lawyer-purpose", "Synthetic immigration counsel search");
    await fillByTestId(
      page,
      "find-lawyer-brief",
      "Synthetic user needs immigration counsel for STEM OPT and related tax/document issues. They have an I-20, I-983, employment letter, tax return, and bank statement. They need counsel to verify timing, status consistency, filing readiness, and document cleanup across immigration and tax workflows before any paid engagement is executed.",
    );
    await uploadByTestId(page, "find-lawyer-files", "synthetic-brief.txt", "synthetic-i20.pdf");
    await clickByTestId(page, "find-lawyer-submit");
    await expect(page).toHaveURL(/\/find-lawyer\/search-complete/);
    await expect(page.locator("body")).toContainText(/Graph Immigration LLP/i);
    await clickByTestId(page, "find-lawyer-track-top-3");
    await expect(page.locator("body")).toContainText(/Tracked|tracking/i);

    await completeForm8843(page);

    await page.goto("/share/share-token");
    await clickByTestId(page, "share-slot-passport");
    await expect(page.getByTestId("share-preview-drawer")).toBeVisible();
    await clickByTestId(page, "share-preview-close");
    await expect(page.getByTestId("share-preview-drawer")).toBeHidden();
    const [shareDownload] = await Promise.all([
      page.waitForEvent("download"),
      clickByTestId(page, "share-download-all"),
    ]);
    expect(shareDownload).toBeTruthy();

    expect(consoleErrors.filter((message) => (
      !message.includes("Failed to load resource")
      && !message.includes("Failed to fetch RSC payload")
    ))).toEqual([]);
    expect(pageErrors).toEqual([]);
    expect(failedResponses).toEqual([]);
  });
});
