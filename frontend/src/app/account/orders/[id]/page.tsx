"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import FilingChecklistCard from "@/components/form8843/FilingChecklistCard";
import { isLoggedIn } from "@/lib/auth";
import {
  acceptMarketplaceUpgrade,
  downloadForm8843Pdf,
  downloadMarketplaceArtifact,
  getMarketplaceOrder,
  markMarketplaceOrderMailed,
  processMarketplaceOrder,
  pullMarketplaceOrderPrefill,
  saveMarketplaceOrderFileIntake,
  saveMarketplaceOrderJsonIntake,
  type Form8843OrderResponse,
  type MarketplaceOrder,
} from "@/lib/marketplace";


export const dynamic = "force-dynamic";

const H1B_FILE_INPUTS = [
  { name: "h1b_registration_file", label: "H-1B registration notice" },
  { name: "h1b_status_summary_file", label: "Status summary or petition timeline" },
  { name: "h1b_g28_file", label: "G-28 or representative form" },
  { name: "h1b_filing_invoice_file", label: "Attorney invoice or filing invoice" },
  { name: "h1b_filing_fee_receipt_file", label: "Fee receipt or payment confirmation" },
] as const;

type FbarAccountForm = {
  institution_name: string;
  country: string;
  account_type: string;
  max_balance_usd: string;
  account_number_last4: string;
};

type FbarFormState = {
  tax_year: string;
  owner_name: string;
  accounts: FbarAccountForm[];
};

type Election83BFormState = {
  taxpayer_name: string;
  taxpayer_address: string;
  company_name: string;
  property_description: string;
  grant_date: string;
  share_count: string;
  fair_market_value_per_share: string;
  exercise_price_per_share: string;
  vesting_schedule: string;
};

type StudentTaxFormState = {
  tax_year: string;
  full_name: string;
  visa_type: string;
  school_name: string;
  country_citizenship: string;
  arrival_date: string;
  days_present_current: string;
  days_present_year_1_ago: string;
  days_present_year_2_ago: string;
  wage_income_usd: string;
  scholarship_income_usd: string;
  other_income_usd: string;
  federal_withholding_usd: string;
  state_withholding_usd: string;
  claim_treaty_benefit: boolean;
  treaty_country: string;
  treaty_article: string;
  used_resident_software: boolean;
};

type OptIntakeFormState = {
  desired_start_date: string;
  employment_plan_text: string;
  passport_file: File | null;
  i20_file: File | null;
  photo_file: File | null;
  employment_plan_file: File | null;
};

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatMoney(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "Not available";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ");
}

function displayProductName(order: MarketplaceOrder): string {
  return order.product.public_name || order.product.name;
}

function displayProductSummary(order: MarketplaceOrder): string {
  return order.product.public_headline || order.product.headline || order.product.public_description || order.product.description;
}

function asText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function createEmptyFbarAccount(): FbarAccountForm {
  return {
    institution_name: "",
    country: "",
    account_type: "",
    max_balance_usd: "",
    account_number_last4: "",
  };
}

function createInitialFbarForm(): FbarFormState {
  return {
    tax_year: String(new Date().getFullYear() - 1),
    owner_name: "",
    accounts: [createEmptyFbarAccount()],
  };
}

function createInitial83BForm(): Election83BFormState {
  return {
    taxpayer_name: "",
    taxpayer_address: "",
    company_name: "",
    property_description: "Restricted common stock",
    grant_date: "",
    share_count: "",
    fair_market_value_per_share: "",
    exercise_price_per_share: "",
    vesting_schedule: "",
  };
}

function createInitialStudentTaxForm(): StudentTaxFormState {
  return {
    tax_year: String(new Date().getFullYear() - 1),
    full_name: "",
    visa_type: "F-1",
    school_name: "",
    country_citizenship: "",
    arrival_date: "",
    days_present_current: "",
    days_present_year_1_ago: "",
    days_present_year_2_ago: "",
    wage_income_usd: "",
    scholarship_income_usd: "",
    other_income_usd: "",
    federal_withholding_usd: "",
    state_withholding_usd: "",
    claim_treaty_benefit: false,
    treaty_country: "",
    treaty_article: "",
    used_resident_software: false,
  };
}

function createInitialOptIntakeForm(): OptIntakeFormState {
  return {
    desired_start_date: "",
    employment_plan_text: "",
    passport_file: null,
    i20_file: null,
    photo_file: null,
    employment_plan_file: null,
  };
}

function toForm8843Order(order: MarketplaceOrder | null): Form8843OrderResponse | null {
  if (!order?.filing_instructions) {
    return null;
  }

  return {
    order_id: order.order_id,
    status: order.status,
    pdf_url: order.pdf_url ?? null,
    email_status: order.email_status ?? null,
    delivery_method: order.delivery_method,
    filing_deadline: order.filing_deadline,
    mailing_status: order.mailing_status,
    mailed_at: order.mailed_at,
    tracking_number: order.tracking_number,
    filing_instructions: order.filing_instructions,
    mailing_service_available: Boolean(order.mailing_service_available),
  };
}

export default function AccountOrderDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const orderId = typeof params?.id === "string" ? params.id : "";
  const [order, setOrder] = useState<MarketplaceOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNote, setActionNote] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"save" | "process" | "mail" | "upgrade" | "prefill" | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [h1bFiles, setH1bFiles] = useState<Record<string, File | null>>({});
  const [fbarForm, setFbarForm] = useState<FbarFormState>(() => createInitialFbarForm());
  const [election83BForm, setElection83BForm] = useState<Election83BFormState>(() => createInitial83BForm());
  const [studentTaxForm, setStudentTaxForm] = useState<StudentTaxFormState>(() => createInitialStudentTaxForm());
  const [optIntakeForm, setOptIntakeForm] = useState<OptIntakeFormState>(() => createInitialOptIntakeForm());
  const autoPrefillAttemptedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setError("Missing order ID");
      setLoading(false);
      return;
    }

    if (!isLoggedIn()) {
      router.replace(`/login?next=${encodeURIComponent(`/account/orders/${orderId}`)}`);
      return;
    }

    let cancelled = false;
    getMarketplaceOrder(orderId)
      .then((nextOrder) => {
        if (!cancelled) {
          hydrateFromOrder(nextOrder);
          setOrder(nextOrder);
          setTrackingNumber(nextOrder.tracking_number ?? "");
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load order");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [orderId, router]);

  const form8843Order = toForm8843Order(order);
  const result = order?.result ?? null;
  const isSlice3Sku = order ? ["student_tax_1040nr", "h1b_doc_check", "fbar_check", "election_83b"].includes(order.product_sku) : false;
  const isOptSku = order ? ["opt_execution", "opt_advisory"].includes(order.product_sku) : false;

  function hydrateFromOrder(nextOrder: MarketplaceOrder) {
    const preview = nextOrder.intake_preview ?? null;
    if (!preview || typeof preview !== "object") {
      return;
    }

    if (nextOrder.product_sku === "fbar_check") {
      const data = preview as Record<string, unknown>;
      const accounts = Array.isArray(data.accounts)
        ? data.accounts.map((account) => {
          const row = account as Record<string, unknown>;
          return {
            institution_name: asText(row.institution_name),
            country: asText(row.country),
            account_type: asText(row.account_type),
            max_balance_usd: asText(row.max_balance_usd),
            account_number_last4: asText(row.account_number_last4),
          };
        })
        : [createEmptyFbarAccount()];
      setFbarForm({
        tax_year: asText(data.tax_year) || createInitialFbarForm().tax_year,
        owner_name: asText(data.owner_name),
        accounts: accounts.length ? accounts : [createEmptyFbarAccount()],
      });
      return;
    }

    if (nextOrder.product_sku === "student_tax_1040nr") {
      const data = preview as Record<string, unknown>;
      setStudentTaxForm({
        tax_year: asText(data.tax_year) || createInitialStudentTaxForm().tax_year,
        full_name: asText(data.full_name),
        visa_type: asText(data.visa_type) || "F-1",
        school_name: asText(data.school_name),
        country_citizenship: asText(data.country_citizenship),
        arrival_date: asText(data.arrival_date),
        days_present_current: asText(data.days_present_current),
        days_present_year_1_ago: asText(data.days_present_year_1_ago),
        days_present_year_2_ago: asText(data.days_present_year_2_ago),
        wage_income_usd: asText(data.wage_income_usd),
        scholarship_income_usd: asText(data.scholarship_income_usd),
        other_income_usd: asText(data.other_income_usd),
        federal_withholding_usd: asText(data.federal_withholding_usd),
        state_withholding_usd: asText(data.state_withholding_usd),
        claim_treaty_benefit: Boolean(data.claim_treaty_benefit),
        treaty_country: asText(data.treaty_country),
        treaty_article: asText(data.treaty_article),
        used_resident_software: Boolean(data.used_resident_software),
      });
      return;
    }

    if (nextOrder.product_sku === "election_83b") {
      const data = preview as Record<string, unknown>;
      setElection83BForm({
        taxpayer_name: asText(data.taxpayer_name),
        taxpayer_address: asText(data.taxpayer_address),
        company_name: asText(data.company_name),
        property_description: asText(data.property_description) || "Restricted common stock",
        grant_date: asText(data.grant_date),
        share_count: asText(data.share_count),
        fair_market_value_per_share: asText(data.fair_market_value_per_share),
        exercise_price_per_share: asText(data.exercise_price_per_share),
        vesting_schedule: asText(data.vesting_schedule),
      });
      return;
    }

    if (nextOrder.product_sku === "opt_execution" || nextOrder.product_sku === "opt_advisory") {
      const clientIntake = (preview as Record<string, unknown>).client_intake as Record<string, unknown> | undefined;
      if (!clientIntake) {
        return;
      }
      setOptIntakeForm((current) => ({
        ...current,
        desired_start_date: asText(clientIntake.desired_start_date),
        employment_plan_text: asText(clientIntake.employment_plan_text),
      }));
    }
  }

  function applyOrder(nextOrder: MarketplaceOrder, note: string) {
    hydrateFromOrder(nextOrder);
    setOrder(nextOrder);
    setTrackingNumber(nextOrder.tracking_number ?? "");
    setActionError(null);
    setActionNote(note);
  }

  function updateFbarAccount(index: number, field: keyof FbarAccountForm, value: string) {
    setFbarForm((current) => ({
      ...current,
      accounts: current.accounts.map((account, accountIndex) => (
        accountIndex === index
          ? { ...account, [field]: value }
          : account
      )),
    }));
  }

  async function handleSaveIntake() {
    if (!order) {
      return;
    }

    setBusyAction("save");
    setActionError(null);
    setActionNote(null);

    try {
      if (order.product_sku === "h1b_doc_check") {
        const formData = new FormData();
        let count = 0;
        for (const field of H1B_FILE_INPUTS) {
          const file = h1bFiles[field.name];
          if (!file) {
            continue;
          }
          formData.append(field.name, file);
          count += 1;
        }
        if (!count) {
          throw new Error("Upload at least one H-1B packet document before saving intake.");
        }
        const nextOrder = await saveMarketplaceOrderFileIntake(order.order_id, formData);
        applyOrder(nextOrder, "Documents saved. Run the review when you are ready.");
        return;
      }

      if (order.product_sku === "fbar_check") {
        const rawAccounts = fbarForm.accounts.map((account) => ({
          institution_name: account.institution_name.trim(),
          country: account.country.trim(),
          account_type: account.account_type.trim(),
          max_balance_usd: account.max_balance_usd.trim(),
          account_number_last4: account.account_number_last4.trim(),
        }));
        const accounts = rawAccounts
          .filter((account) => (
            account.institution_name ||
            account.country ||
            account.account_type ||
            account.account_number_last4 ||
            account.max_balance_usd
          ))
          .map((account) => ({
            ...account,
            max_balance_usd: Number(account.max_balance_usd),
          }));

        if (!fbarForm.owner_name.trim()) {
          throw new Error("Enter the account owner name.");
        }
        if (!fbarForm.tax_year.trim()) {
          throw new Error("Enter the tax year you want reviewed.");
        }
        if (!accounts.length) {
          throw new Error("Add at least one foreign account.");
        }
        if (accounts.some((account) => !account.institution_name || !account.country || !account.account_type || !Number.isFinite(account.max_balance_usd))) {
          throw new Error("Complete each foreign account row before saving intake.");
        }

        const nextOrder = await saveMarketplaceOrderJsonIntake(order.order_id, {
          tax_year: Number(fbarForm.tax_year),
          owner_name: fbarForm.owner_name.trim(),
          accounts,
        });
        applyOrder(nextOrder, "FBAR intake saved. Run the compliance check to generate the result.");
        return;
      }

      if (order.product_sku === "student_tax_1040nr") {
        const requiredValues = [
          studentTaxForm.tax_year,
          studentTaxForm.full_name,
          studentTaxForm.visa_type,
          studentTaxForm.school_name,
          studentTaxForm.country_citizenship,
          studentTaxForm.arrival_date,
          studentTaxForm.days_present_current,
          studentTaxForm.days_present_year_1_ago,
          studentTaxForm.days_present_year_2_ago,
        ];
        if (requiredValues.some((value) => !String(value).trim())) {
          throw new Error("Complete the required student tax fields before saving intake.");
        }

        const taxYear = Number(studentTaxForm.tax_year);
        const daysPresentCurrent = Number(studentTaxForm.days_present_current);
        const daysPresentYear1Ago = Number(studentTaxForm.days_present_year_1_ago);
        const daysPresentYear2Ago = Number(studentTaxForm.days_present_year_2_ago);
        const wageIncome = Number(studentTaxForm.wage_income_usd || "0");
        const scholarshipIncome = Number(studentTaxForm.scholarship_income_usd || "0");
        const otherIncome = Number(studentTaxForm.other_income_usd || "0");
        const federalWithholding = Number(studentTaxForm.federal_withholding_usd || "0");
        const stateWithholding = Number(studentTaxForm.state_withholding_usd || "0");
        if (
          [taxYear, daysPresentCurrent, daysPresentYear1Ago, daysPresentYear2Ago, wageIncome, scholarshipIncome, otherIncome, federalWithholding, stateWithholding]
            .some((value) => !Number.isFinite(value))
        ) {
          throw new Error("Use valid numbers for the student tax year, day counts, income, and withholding fields.");
        }

        const nextOrder = await saveMarketplaceOrderJsonIntake(order.order_id, {
          tax_year: taxYear,
          full_name: studentTaxForm.full_name.trim(),
          visa_type: studentTaxForm.visa_type.trim(),
          school_name: studentTaxForm.school_name.trim(),
          country_citizenship: studentTaxForm.country_citizenship.trim(),
          arrival_date: studentTaxForm.arrival_date,
          days_present_current: daysPresentCurrent,
          days_present_year_1_ago: daysPresentYear1Ago,
          days_present_year_2_ago: daysPresentYear2Ago,
          wage_income_usd: wageIncome,
          scholarship_income_usd: scholarshipIncome,
          other_income_usd: otherIncome,
          federal_withholding_usd: federalWithholding,
          state_withholding_usd: stateWithholding,
          claim_treaty_benefit: studentTaxForm.claim_treaty_benefit,
          treaty_country: studentTaxForm.treaty_country.trim() || null,
          treaty_article: studentTaxForm.treaty_article.trim() || null,
          used_resident_software: studentTaxForm.used_resident_software,
        });
        applyOrder(nextOrder, "Student tax intake saved. Run the package prep to generate the filing materials.");
        return;
      }

      if (order.product_sku === "election_83b") {
        const requiredValues = [
          election83BForm.taxpayer_name,
          election83BForm.taxpayer_address,
          election83BForm.company_name,
          election83BForm.property_description,
          election83BForm.grant_date,
          election83BForm.share_count,
          election83BForm.fair_market_value_per_share,
          election83BForm.exercise_price_per_share,
          election83BForm.vesting_schedule,
        ];
        if (requiredValues.some((value) => !String(value).trim())) {
          throw new Error("Complete every 83(b) field before saving intake.");
        }
        const nextOrder = await saveMarketplaceOrderJsonIntake(order.order_id, {
          taxpayer_name: election83BForm.taxpayer_name.trim(),
          taxpayer_address: election83BForm.taxpayer_address.trim(),
          company_name: election83BForm.company_name.trim(),
          property_description: election83BForm.property_description.trim(),
          grant_date: election83BForm.grant_date,
          share_count: Number(election83BForm.share_count),
          fair_market_value_per_share: Number(election83BForm.fair_market_value_per_share),
          exercise_price_per_share: Number(election83BForm.exercise_price_per_share),
          vesting_schedule: election83BForm.vesting_schedule.trim(),
        });
        applyOrder(nextOrder, "83(b) intake saved. Generate the packet when you are ready.");
        return;
      }

      if (order.product_sku === "opt_execution" || order.product_sku === "opt_advisory") {
        const formData = new FormData();
        let fieldCount = 0;
        if (optIntakeForm.desired_start_date) {
          formData.append("desired_start_date", optIntakeForm.desired_start_date);
          fieldCount += 1;
        }
        if (optIntakeForm.employment_plan_text.trim()) {
          formData.append("employment_plan_text", optIntakeForm.employment_plan_text.trim());
          fieldCount += 1;
        }
        if (optIntakeForm.passport_file) {
          formData.append("passport_file", optIntakeForm.passport_file);
          fieldCount += 1;
        }
        if (optIntakeForm.i20_file) {
          formData.append("i20_file", optIntakeForm.i20_file);
          fieldCount += 1;
        }
        if (optIntakeForm.photo_file) {
          formData.append("photo_file", optIntakeForm.photo_file);
          fieldCount += 1;
        }
        if (optIntakeForm.employment_plan_file) {
          formData.append("employment_plan_file", optIntakeForm.employment_plan_file);
          fieldCount += 1;
        }
        if (!fieldCount) {
          throw new Error("Provide OPT intake details before saving.");
        }
        const nextOrder = await saveMarketplaceOrderFileIntake(order.order_id, formData);
        applyOrder(nextOrder, "OPT intake saved. Review the agreement next.");
      }
    } catch (nextError) {
      setActionError(nextError instanceof Error ? nextError.message : "Could not save intake");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleProcessOrder() {
    if (!order) {
      return;
    }

    setBusyAction("process");
    setActionError(null);
    setActionNote(null);
    try {
      const nextOrder = await processMarketplaceOrder(order.order_id);
      applyOrder(nextOrder, "Processing complete.");
    } catch (nextError) {
      setActionError(nextError instanceof Error ? nextError.message : "Could not process this order");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleMarkMailed() {
    if (!order) {
      return;
    }

    setBusyAction("mail");
    setActionError(null);
    setActionNote(null);
    try {
      const nextOrder = await markMarketplaceOrderMailed(order.order_id, {
        tracking_number: trackingNumber.trim() || undefined,
      });
      applyOrder(nextOrder, "Mailing confirmation saved.");
    } catch (nextError) {
      setActionError(nextError instanceof Error ? nextError.message : "Could not save mailing confirmation");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAcceptUpgrade() {
    if (!order) {
      return;
    }

    setBusyAction("upgrade");
    setActionError(null);
    setActionNote(null);
    try {
      const response = await acceptMarketplaceUpgrade(order.order_id);
      applyOrder(response.original_order, "Your upgraded order is ready. Continue in the new strategy review workspace.");
      router.push(`/account/orders/${response.upgraded_order.order_id}`);
    } catch (nextError) {
      setActionError(nextError instanceof Error ? nextError.message : "Could not continue into strategy review");
    } finally {
      setBusyAction(null);
    }
  }

  async function handlePullPrefill() {
    if (!order) {
      return;
    }

    setBusyAction("prefill");
    setActionError(null);
    setActionNote(null);
    try {
      const response = await pullMarketplaceOrderPrefill(order.order_id);
      applyOrder(response.order, response.prefill.summary);
    } catch (nextError) {
      setActionError(nextError instanceof Error ? nextError.message : "Could not pull extracted data into this order");
    } finally {
      setBusyAction(null);
    }
  }

  useEffect(() => {
    if (!order || order.result_ready || order.intake_preview || !(isSlice3Sku || isOptSku)) {
      return;
    }
    if (autoPrefillAttemptedRef.current === order.order_id) {
      return;
    }
    autoPrefillAttemptedRef.current = order.order_id;
    pullMarketplaceOrderPrefill(order.order_id)
      .then((response) => {
        hydrateFromOrder(response.order);
        setOrder(response.order);
        setTrackingNumber(response.order.tracking_number ?? "");
        setActionError(null);
        setActionNote(response.prefill.summary);
      })
      .catch(() => {
        // Silent miss: not every user will have data-room documents for every service.
      });
  }, [isOptSku, isSlice3Sku, order]);

  function renderPrefilledDocuments(documents: unknown, tone: "neutral" | "accent" = "neutral") {
    if (!Array.isArray(documents) || !documents.length) {
      return null;
    }
    const borderClass = tone === "accent" ? "border-[#d7e4f7] bg-[#f8fbff]" : "border-[#e4edf7] bg-[#fbfdff]";
    return (
      <div className={`mt-5 rounded-[22px] border ${borderClass} p-4`}>
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Attached from data room</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {documents.map((document, index) => {
            const row = (document || {}) as Record<string, unknown>;
            const label = `${formatLabel(asText(row.doc_type) || "document")} · ${asText(row.filename) || `Document ${index + 1}`}`;
            return (
              <span
                key={`${asText(row.source_document_id) || index}-${label}`}
                className="rounded-full border border-[#dbe5f2] bg-white px-3 py-1.5 text-[12px] font-medium text-[#546781]"
              >
                {label}
              </span>
            );
          })}
        </div>
      </div>
    );
  }

  function renderIntakeSection() {
    if (!order || order.product_sku === "form_8843_free" || !isSlice3Sku) {
      return null;
    }

    const inputClassName = "mt-2 w-full rounded-2xl border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#1a2942] outline-none transition focus:border-[#9db8e6]";
    const labelClassName = "text-[12px] font-semibold uppercase tracking-[0.14em] text-[#7384a0]";

    if (order.result_ready) {
      return (
        <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Intake</div>
          <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Input already captured</h2>
          <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
            This order has already been processed. Start a new order from the service page if you want to run another scenario.
          </p>
        </section>
      );
    }

    return (
      <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Intake</div>
            <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Provide the inputs for this order</h2>
            <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
              Guardian keeps the intake inside this workspace so the order page acts as the operating surface, not just a receipt.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handlePullPrefill()}
              disabled={busyAction === "prefill"}
              className="inline-flex rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b] disabled:cursor-not-allowed disabled:text-[#98a5ba]"
            >
              {busyAction === "prefill" ? "Pulling from data room..." : "Pull from data room"}
            </button>
            <button
              type="button"
              onClick={() => void handleSaveIntake()}
              disabled={busyAction === "save"}
              className="inline-flex rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a] disabled:cursor-not-allowed disabled:bg-[#8b97ad]"
            >
              {busyAction === "save" ? "Saving intake..." : "Save intake"}
            </button>
          </div>
        </div>

        {order.product_sku === "h1b_doc_check"
          ? renderPrefilledDocuments((order.intake_preview as Record<string, unknown> | null)?.documents)
          : null}

        {order.product_sku === "h1b_doc_check" ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {H1B_FILE_INPUTS.map((field) => (
              <label
                key={field.name}
                className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4"
              >
                <div className={labelClassName}>{field.label}</div>
                <input
                  type="file"
                  accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
                  className={`${inputClassName} file:mr-4 file:rounded-full file:border-0 file:bg-[#eef4ff] file:px-4 file:py-2 file:text-[13px] file:font-semibold file:text-[#355694]`}
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setH1bFiles((current) => ({ ...current, [field.name]: file }));
                  }}
                />
                <div className="mt-2 text-[13px] text-[#6e7f9a]">
                  {h1bFiles[field.name]?.name || "No file selected"}
                </div>
              </label>
            ))}
          </div>
        ) : null}

        {order.product_sku === "student_tax_1040nr" ? (
          <div className="mt-6 space-y-5">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Tax year</div>
                <input
                  value={studentTaxForm.tax_year}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, tax_year: event.target.value }))}
                  className={inputClassName}
                  placeholder="2025"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Full name</div>
                <input
                  value={studentTaxForm.full_name}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, full_name: event.target.value }))}
                  className={inputClassName}
                  placeholder="Jessica Chen"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Visa type</div>
                <input
                  value={studentTaxForm.visa_type}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, visa_type: event.target.value }))}
                  className={inputClassName}
                  placeholder="F-1"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4 md:col-span-2">
                <div className={labelClassName}>School name</div>
                <input
                  value={studentTaxForm.school_name}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, school_name: event.target.value }))}
                  className={inputClassName}
                  placeholder="Columbia University"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Citizenship</div>
                <input
                  value={studentTaxForm.country_citizenship}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, country_citizenship: event.target.value }))}
                  className={inputClassName}
                  placeholder="China"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Arrival date</div>
                <input
                  type="date"
                  value={studentTaxForm.arrival_date}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, arrival_date: event.target.value }))}
                  className={inputClassName}
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Days present this year</div>
                <input
                  value={studentTaxForm.days_present_current}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, days_present_current: event.target.value }))}
                  className={inputClassName}
                  placeholder="320"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Days present one year ago</div>
                <input
                  value={studentTaxForm.days_present_year_1_ago}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, days_present_year_1_ago: event.target.value }))}
                  className={inputClassName}
                  placeholder="280"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Days present two years ago</div>
                <input
                  value={studentTaxForm.days_present_year_2_ago}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, days_present_year_2_ago: event.target.value }))}
                  className={inputClassName}
                  placeholder="0"
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Wage income (USD)</div>
                <input
                  value={studentTaxForm.wage_income_usd}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, wage_income_usd: event.target.value }))}
                  className={inputClassName}
                  placeholder="24000"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Scholarship income (USD)</div>
                <input
                  value={studentTaxForm.scholarship_income_usd}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, scholarship_income_usd: event.target.value }))}
                  className={inputClassName}
                  placeholder="0"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Other income (USD)</div>
                <input
                  value={studentTaxForm.other_income_usd}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, other_income_usd: event.target.value }))}
                  className={inputClassName}
                  placeholder="0"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Federal withholding (USD)</div>
                <input
                  value={studentTaxForm.federal_withholding_usd}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, federal_withholding_usd: event.target.value }))}
                  className={inputClassName}
                  placeholder="1800"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>State withholding (USD)</div>
                <input
                  value={studentTaxForm.state_withholding_usd}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, state_withholding_usd: event.target.value }))}
                  className={inputClassName}
                  placeholder="450"
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={studentTaxForm.claim_treaty_benefit}
                    onChange={(event) => setStudentTaxForm((current) => ({ ...current, claim_treaty_benefit: event.target.checked }))}
                    className="h-4 w-4 rounded border-[#bfd1e9]"
                  />
                  <div className={labelClassName}>Claim treaty benefit</div>
                </div>
                <div className="mt-3 text-[13px] leading-6 text-[#6e7f9a]">
                  Turn this on if you expect treaty-based wage or scholarship treatment and want Guardian to flag the review step.
                </div>
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={studentTaxForm.used_resident_software}
                    onChange={(event) => setStudentTaxForm((current) => ({ ...current, used_resident_software: event.target.checked }))}
                    className="h-4 w-4 rounded border-[#bfd1e9]"
                  />
                  <div className={labelClassName}>Used resident-return software</div>
                </div>
                <div className="mt-3 text-[13px] leading-6 text-[#6e7f9a]">
                  Guardian will flag this if you may have been routed toward Form 1040 instead of 1040-NR.
                </div>
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Treaty country</div>
                <input
                  value={studentTaxForm.treaty_country}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, treaty_country: event.target.value }))}
                  className={inputClassName}
                  placeholder="China"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Treaty article</div>
                <input
                  value={studentTaxForm.treaty_article}
                  onChange={(event) => setStudentTaxForm((current) => ({ ...current, treaty_article: event.target.value }))}
                  className={inputClassName}
                  placeholder="Article 20(c)"
                />
              </label>
            </div>
          </div>
        ) : null}

        {order.product_sku === "fbar_check" ? (
          <div className="mt-6 space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Tax year</div>
                <input
                  value={fbarForm.tax_year}
                  onChange={(event) => setFbarForm((current) => ({ ...current, tax_year: event.target.value }))}
                  className={inputClassName}
                  placeholder="2025"
                />
              </label>
              <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>Account owner</div>
                <input
                  value={fbarForm.owner_name}
                  onChange={(event) => setFbarForm((current) => ({ ...current, owner_name: event.target.value }))}
                  className={inputClassName}
                  placeholder="Wei Liu"
                />
              </label>
            </div>

            <div>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-[13px] font-semibold uppercase tracking-[0.14em] text-[#7384a0]">Foreign accounts</div>
                <button
                  type="button"
                  onClick={() => setFbarForm((current) => ({ ...current, accounts: [...current.accounts, createEmptyFbarAccount()] }))}
                  className="rounded-full border border-[#dbe5f2] bg-white px-4 py-2 text-[13px] font-semibold text-[#40536f]"
                >
                  Add account
                </button>
              </div>
              <div className="mt-4 space-y-4">
                {fbarForm.accounts.map((account, index) => (
                  <div
                    key={`${index}-${account.institution_name}`}
                    className="rounded-[24px] border border-[#dbe5f2] bg-[#fbfdff] p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-[14px] font-semibold text-[#1a2942]">Account {index + 1}</div>
                      {fbarForm.accounts.length > 1 ? (
                        <button
                          type="button"
                          onClick={() => setFbarForm((current) => ({
                            ...current,
                            accounts: current.accounts.filter((_, accountIndex) => accountIndex !== index),
                          }))}
                          className="text-[13px] font-semibold text-[#8a5160]"
                        >
                          Remove
                        </button>
                      ) : null}
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                      <label>
                        <div className={labelClassName}>Institution</div>
                        <input
                          value={account.institution_name}
                          onChange={(event) => updateFbarAccount(index, "institution_name", event.target.value)}
                          className={inputClassName}
                          placeholder="HSBC Hong Kong"
                        />
                      </label>
                      <label>
                        <div className={labelClassName}>Country</div>
                        <input
                          value={account.country}
                          onChange={(event) => updateFbarAccount(index, "country", event.target.value)}
                          className={inputClassName}
                          placeholder="Hong Kong"
                        />
                      </label>
                      <label>
                        <div className={labelClassName}>Account type</div>
                        <input
                          value={account.account_type}
                          onChange={(event) => updateFbarAccount(index, "account_type", event.target.value)}
                          className={inputClassName}
                          placeholder="Checking"
                        />
                      </label>
                      <label>
                        <div className={labelClassName}>Max balance (USD)</div>
                        <input
                          value={account.max_balance_usd}
                          onChange={(event) => updateFbarAccount(index, "max_balance_usd", event.target.value)}
                          className={inputClassName}
                          placeholder="7000"
                        />
                      </label>
                      <label>
                        <div className={labelClassName}>Account last 4</div>
                        <input
                          value={account.account_number_last4}
                          onChange={(event) => updateFbarAccount(index, "account_number_last4", event.target.value)}
                          className={inputClassName}
                          placeholder="1122"
                        />
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {order.product_sku === "election_83b" ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Taxpayer name</div>
              <input
                value={election83BForm.taxpayer_name}
                onChange={(event) => setElection83BForm((current) => ({ ...current, taxpayer_name: event.target.value }))}
                className={inputClassName}
                placeholder="Jessica Chen"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4 md:col-span-2">
              <div className={labelClassName}>Taxpayer address</div>
              <input
                value={election83BForm.taxpayer_address}
                onChange={(event) => setElection83BForm((current) => ({ ...current, taxpayer_address: event.target.value }))}
                className={inputClassName}
                placeholder="123 Startup Way, San Francisco, CA 94107"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Company</div>
              <input
                value={election83BForm.company_name}
                onChange={(event) => setElection83BForm((current) => ({ ...current, company_name: event.target.value }))}
                className={inputClassName}
                placeholder="CliniPulse, Inc."
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Grant date</div>
              <input
                type="date"
                value={election83BForm.grant_date}
                onChange={(event) => setElection83BForm((current) => ({ ...current, grant_date: event.target.value }))}
                className={inputClassName}
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4 md:col-span-2">
              <div className={labelClassName}>Property description</div>
              <input
                value={election83BForm.property_description}
                onChange={(event) => setElection83BForm((current) => ({ ...current, property_description: event.target.value }))}
                className={inputClassName}
                placeholder="Restricted common stock"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Share count</div>
              <input
                value={election83BForm.share_count}
                onChange={(event) => setElection83BForm((current) => ({ ...current, share_count: event.target.value }))}
                className={inputClassName}
                placeholder="10000"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>FMV per share</div>
              <input
                value={election83BForm.fair_market_value_per_share}
                onChange={(event) => setElection83BForm((current) => ({ ...current, fair_market_value_per_share: event.target.value }))}
                className={inputClassName}
                placeholder="0.02"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Exercise price per share</div>
              <input
                value={election83BForm.exercise_price_per_share}
                onChange={(event) => setElection83BForm((current) => ({ ...current, exercise_price_per_share: event.target.value }))}
                className={inputClassName}
                placeholder="0.01"
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4 md:col-span-2">
              <div className={labelClassName}>Vesting schedule</div>
              <textarea
                value={election83BForm.vesting_schedule}
                onChange={(event) => setElection83BForm((current) => ({ ...current, vesting_schedule: event.target.value }))}
                className={`${inputClassName} min-h-[120px] resize-y`}
                placeholder="25% after 12 months, then monthly over 36 months"
              />
            </label>
          </div>
        ) : null}
      </section>
    );
  }

  function renderResultSection() {
    if (!order || order.product_sku === "form_8843_free" || !result) {
      return null;
    }

    return (
      <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/84 p-6 shadow-[0_22px_70px_rgba(61,84,128,0.07)]">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Result</div>
        <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Guardian output</h2>
        {result.summary ? (
          <div className="mt-4 rounded-[22px] border border-[#e4edf7] bg-[#fbfdff] px-5 py-4 text-[15px] leading-7 text-[#435774]">
            {result.summary}
          </div>
        ) : null}

        {(typeof result.aggregate_max_balance_usd === "number" || typeof result.total_income_usd === "number" || typeof result.requires_fbar === "boolean" || result.filing_deadline) ? (
          <div className="mt-5 grid gap-4 md:grid-cols-4">
            {typeof result.aggregate_max_balance_usd === "number" ? (
              <div className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Aggregate balance</div>
                <div className="mt-2 text-[22px] font-bold text-[#13213b]">{formatMoney(result.aggregate_max_balance_usd)}</div>
              </div>
            ) : null}
            {typeof result.total_income_usd === "number" ? (
              <div className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Income reviewed</div>
                <div className="mt-2 text-[22px] font-bold text-[#13213b]">{formatMoney(result.total_income_usd)}</div>
              </div>
            ) : null}
            {typeof result.requires_fbar === "boolean" ? (
              <div className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">FBAR required</div>
                <div className="mt-2 text-[22px] font-bold text-[#13213b]">{result.requires_fbar ? "Yes" : "No"}</div>
              </div>
            ) : null}
            {result.filing_deadline ? (
              <div className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Deadline</div>
                <div className="mt-2 text-[22px] font-bold text-[#13213b]">{formatDate(result.filing_deadline)}</div>
              </div>
            ) : null}
          </div>
        ) : null}

        {result.findings.length ? (
          <div className="mt-6">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Findings</div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {result.findings.map((finding) => (
                <article
                  key={`${finding.rule_id}-${finding.title}`}
                  className="rounded-[22px] border border-[#e4edf7] bg-[#fbfdff] p-4"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                    {finding.severity} · {finding.category}
                  </div>
                  <h3 className="mt-2 text-[18px] font-semibold text-[#13213b]">{finding.title}</h3>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">{finding.consequence}</p>
                  <div className="mt-4 rounded-2xl border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#40536f]">
                    {finding.action}
                  </div>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        {result.next_steps.length ? (
          <div className="mt-6 rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-5">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Next steps</div>
            <div className="mt-4 space-y-3">
              {result.next_steps.map((step) => (
                <div key={step} className="flex gap-3 text-[14px] leading-6 text-[#435774]">
                  <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#5b8dee]" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {result.mailing_instructions ? (
          <div className="mt-6 rounded-[22px] border border-[#f1e3b4] bg-[#fff9eb] p-5">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#9b7a22]">Mailing</div>
            <h3 className="mt-2 text-[20px] font-semibold text-[#6b5214]">{result.mailing_instructions.headline}</h3>
            <p className="mt-3 text-[14px] leading-6 text-[#856921]">{result.mailing_instructions.summary}</p>
            <div className="mt-4 space-y-3">
              {result.mailing_instructions.steps.map((step) => (
                <div key={step} className="flex gap-3 text-[14px] leading-6 text-[#856921]">
                  <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#d4ab3a]" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {result.artifacts.length ? (
          <div className="mt-6">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Downloads</div>
            <div className="mt-4 flex flex-wrap gap-3">
              {result.artifacts.map((artifact) => {
                return (
                  <button
                    key={artifact.filename}
                    type="button"
                    onClick={() => {
                      void downloadMarketplaceArtifact(artifact.url, artifact.filename).catch((nextError) => {
                        setActionError(nextError instanceof Error ? nextError.message : "Could not download artifact");
                      });
                    }}
                    className="inline-flex items-center justify-center rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a]"
                  >
                    {artifact.label}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {result.comparisons?.length ? (
          <div className="mt-6">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Cross-checks</div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {result.comparisons.map((comparison) => (
                <div
                  key={comparison.field_name}
                  className="rounded-[22px] border border-[#e4edf7] bg-[#fbfdff] p-4 text-[14px] text-[#435774]"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                    {formatLabel(comparison.field_name)}
                  </div>
                  <div className="mt-3 space-y-2">
                    <div>A: {comparison.value_a || "Not found"}</div>
                    <div>B: {comparison.value_b || "Not found"}</div>
                    <div className="font-semibold text-[#13213b]">
                      {comparison.status} · confidence {Math.round(comparison.confidence * 100)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {result.document_summary?.length ? (
          <div className="mt-6">
            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-[#7384a0]">Documents reviewed</div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {result.document_summary.map((document) => (
                <div
                  key={`${document.doc_type}-${document.filename}`}
                  className="rounded-[22px] border border-[#e4edf7] bg-[#fbfdff] p-4"
                >
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">
                    {formatLabel(document.doc_type)}
                  </div>
                  <div className="mt-2 text-[16px] font-semibold text-[#13213b]">{document.filename}</div>
                  <div className="mt-4 space-y-2 text-[14px] text-[#435774]">
                    {Object.entries(document.fields).map(([fieldName, value]) => (
                      <div key={fieldName}>
                        <span className="font-semibold text-[#13213b]">{formatLabel(fieldName)}:</span>{" "}
                        <span>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    );
  }

  function renderOptIntakeSection() {
    if (!order || !isOptSku) {
      return null;
    }

    const inputClassName = "mt-2 w-full rounded-2xl border border-[#dbe5f2] bg-white px-4 py-3 text-[14px] text-[#1a2942] outline-none transition focus:border-[#9db8e6]";
    const labelClassName = "text-[12px] font-semibold uppercase tracking-[0.14em] text-[#7384a0]";

    return (
      <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">OPT intake</div>
            <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Prepare the attorney review packet</h2>
            <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
              Upload the core OPT documents and add the intended start date so the attorney has a complete filing packet before review.
            </p>
          </div>
          {!order.intake_complete ? (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void handlePullPrefill()}
                disabled={busyAction === "prefill"}
                className="inline-flex rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b] disabled:cursor-not-allowed disabled:text-[#98a5ba]"
              >
                {busyAction === "prefill" ? "Pulling from data room..." : "Pull from data room"}
              </button>
              <button
                type="button"
                onClick={() => void handleSaveIntake()}
                disabled={busyAction === "save"}
                className="inline-flex rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a] disabled:cursor-not-allowed disabled:bg-[#8b97ad]"
              >
                {busyAction === "save" ? "Saving intake..." : "Save intake"}
              </button>
            </div>
          ) : (
            <div className="rounded-full border border-[#cfe7d3] bg-[#f3fbf4] px-4 py-2 text-[13px] font-semibold text-[#326247]">
              Intake captured
            </div>
          )}
        </div>

        {renderPrefilledDocuments(
          (((order.intake_preview as Record<string, unknown> | null)?.client_intake as Record<string, unknown> | undefined)?.documents),
          "accent",
        )}

        {!order.intake_complete ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
              <div className={labelClassName}>Desired OPT start date</div>
              <input
                type="date"
                value={optIntakeForm.desired_start_date}
                onChange={(event) => setOptIntakeForm((current) => ({ ...current, desired_start_date: event.target.value }))}
                className={inputClassName}
              />
            </label>
            <label className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4 md:col-span-2">
              <div className={labelClassName}>Employment plan</div>
              <textarea
                value={optIntakeForm.employment_plan_text}
                onChange={(event) => setOptIntakeForm((current) => ({ ...current, employment_plan_text: event.target.value }))}
                className={`${inputClassName} min-h-[120px] resize-y`}
                placeholder="Describe the role you intend to pursue and how it connects to your field of study."
              />
            </label>
            {[
              ["passport_file", "Passport"],
              ["i20_file", "I-20 with OPT recommendation"],
              ["photo_file", "Passport-style photo"],
              ["employment_plan_file", "Employment plan document"],
            ].map(([fieldName, label]) => (
              <label key={fieldName} className="rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] p-4">
                <div className={labelClassName}>{label}</div>
                <input
                  type="file"
                  accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
                  className={`${inputClassName} file:mr-4 file:rounded-full file:border-0 file:bg-[#eef4ff] file:px-4 file:py-2 file:text-[13px] file:font-semibold file:text-[#355694]`}
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setOptIntakeForm((current) => ({ ...current, [fieldName]: file }));
                  }}
                />
                <div className="mt-2 text-[13px] text-[#6e7f9a]">
                  {optIntakeForm[fieldName as keyof OptIntakeFormState] instanceof File
                    ? (optIntakeForm[fieldName as keyof OptIntakeFormState] as File).name
                    : "No file selected"}
                </div>
              </label>
            ))}
          </div>
        ) : (
          <div className="mt-6 rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] px-5 py-4 text-[14px] leading-7 text-[#435774]">
            The core OPT intake is already saved. Continue to the agreement step to activate attorney review.
          </div>
        )}
      </section>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f5f8fd_0%,#eef4fb_100%)] px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/84 px-4 py-2 text-[13px] font-semibold text-[#40536f] shadow-[0_10px_24px_rgba(61,84,128,0.06)] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
          >
            &larr; Back to dashboard
          </Link>
          <Link
            href="/account/orders"
            className="inline-flex items-center rounded-full border border-[#dbe5f2] bg-white/70 px-4 py-2 text-[13px] font-semibold text-[#5b76a2] transition hover:border-[#c4d4ea] hover:text-[#243958]"
          >
            Back to orders
          </Link>
        </div>

        {loading ? (
          <div className="mt-6 rounded-[32px] border border-[#dbe5f2] bg-white/82 px-6 py-8 text-[15px] text-[#6e7f9a] shadow-[0_22px_70px_rgba(61,84,128,0.08)]">
            Loading order details...
          </div>
        ) : null}

        {error ? (
          <div className="mt-6 rounded-[32px] border border-[#ffd6d6] bg-[#fff4f4] px-6 py-4 text-[14px] text-[#a33a3a]">
            {error}
          </div>
        ) : null}

        {order ? (
          <>
            <section className="mt-6 rounded-[32px] border border-[#dbe5f2] bg-white/86 p-8 shadow-[0_26px_80px_rgba(61,84,128,0.08)]">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-[#71829f]">
                    {order.product.category || "Marketplace order"}
                  </div>
                  <h1 className="mt-3 text-[34px] font-bold tracking-tight text-[#0d1424]">
                    {displayProductName(order)}
                  </h1>
                  <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                    {displayProductSummary(order)}
                  </p>
                </div>
                <div className="rounded-3xl border border-[#dbe5f2] bg-[#f8fbff] px-5 py-4 text-right">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Status</div>
                  <div className="mt-1 text-[18px] font-semibold capitalize text-[#1a2942]">
                    {formatLabel(order.status)}
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-4">
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Order</div>
                  <div className="mt-2 break-all text-[14px] font-medium text-[#1a2942]">{order.order_id}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Ordered</div>
                  <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatDate(order.created_at)}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Deadline</div>
                  <div className="mt-2 text-[14px] font-medium text-[#1a2942]">{formatDate(order.filing_deadline)}</div>
                </div>
                <div className="rounded-2xl border border-[#dbe5f2] bg-[#fbfdff] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Mailing</div>
                  <div className="mt-2 text-[14px] font-medium capitalize text-[#1a2942]">
                    {formatLabel(order.mailing_status)}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                {order?.pdf_url ? (
                  <button
                    type="button"
                    onClick={() => {
                      void downloadForm8843Pdf(order.order_id).catch((nextError) => {
                        setError(nextError instanceof Error ? nextError.message : "Could not download the PDF");
                      });
                    }}
                    className="inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de]"
                  >
                    Download PDF
                  </button>
                ) : null}
                {order.product.path ? (
                  <Link
                    href={order.product.path}
                    className="inline-flex items-center justify-center rounded-full border border-[#dbe5f2] bg-white px-5 py-3 text-[14px] font-semibold text-[#40536f] transition hover:border-[#c4d4ea] hover:text-[#16253b]"
                  >
                    Reopen service
                  </Link>
                ) : null}
              </div>
            </section>

            {actionError ? (
              <div className="mt-6 rounded-[28px] border border-[#ffd6d6] bg-[#fff4f4] px-5 py-4 text-[14px] text-[#a33a3a]">
                {actionError}
              </div>
            ) : null}

            {actionNote ? (
              <div className="mt-6 rounded-[28px] border border-[#cfe7d3] bg-[#f3fbf4] px-5 py-4 text-[14px] text-[#326247]">
                {actionNote}
              </div>
            ) : null}

            {!!(order.product.public_highlights?.length || order.product.highlights.length) ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Included</div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {(order.product.public_highlights?.length ? order.product.public_highlights : order.product.highlights).map((highlight) => (
                    <div
                      key={highlight}
                      className="rounded-2xl border border-[#e4edf7] bg-[#fbfdff] px-4 py-3 text-[14px] text-[#435774]"
                    >
                      {highlight}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {isSlice3Sku ? (
              <section className="mt-6 grid gap-4 md:grid-cols-3">
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 1</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Save intake</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.intake_complete ? "Captured" : "Still needed"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 2</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Run processing</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.result_ready ? "Completed" : order.intake_complete ? "Ready" : "Blocked on intake"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 3</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Download or mail</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.result_ready ? "Available now" : "Waiting for output"}
                  </p>
                </div>
              </section>
            ) : null}

            {isOptSku ? (
              <section className="mt-6 grid gap-4 md:grid-cols-5">
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 1</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Questionnaire</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.questionnaire_response_id ? "Captured" : "Not linked"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 2</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Intake</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.intake_complete ? "Captured" : "Still needed"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 3</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Agreement</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.agreement_signed ? "Signed" : "Pending signature"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 4</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Attorney review</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {order.attorney_assignment?.decision ? order.attorney_assignment.decision.replace(/_/g, " ") : "Waiting for assignment"}
                  </p>
                </div>
                <div className="rounded-[24px] border border-[#dbe5f2] bg-white/84 p-5 shadow-[0_16px_50px_rgba(61,84,128,0.06)]">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Step 5</div>
                  <div className="mt-2 text-[19px] font-semibold text-[#13213b]">Filing</div>
                  <p className="mt-3 text-[14px] leading-6 text-[#556480]">
                    {result?.receipt_number ? "Receipt recorded" : "Pending filing"}
                  </p>
                </div>
              </section>
            ) : null}

            {renderIntakeSection()}
            {renderOptIntakeSection()}

            {isOptSku && order.intake_complete && !order.agreement_signed ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Agreement</div>
                    <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Sign the limited-scope agreement</h2>
                    <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                      Guardian will not assign the case into attorney review until the engagement is signed.
                    </p>
                  </div>
                  <Link
                    href={`/account/orders/${order.order_id}/agreement`}
                    className="inline-flex rounded-full bg-[#0f1728] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#18243a]"
                  >
                    Open agreement
                  </Link>
                </div>
              </section>
            ) : null}

            {isOptSku && order.agreement_signed ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Attorney lane</div>
                <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Attorney review is now the active step</h2>
                <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                  {order.attorney_assignment?.attorney?.full_name
                    ? `${order.attorney_assignment.attorney.full_name} is assigned to this case.`
                    : "An attorney will be assigned as part of this filing workflow."}
                </p>
                {order.attorney_assignment?.attorney ? (
                  <div className="mt-4 rounded-[22px] border border-[#dbe5f2] bg-[#fbfdff] px-5 py-4 text-[14px] leading-6 text-[#435774]">
                    {order.attorney_assignment.attorney.full_name} · {order.attorney_assignment.attorney.bar_state || "State pending"} · {order.attorney_assignment.attorney.bar_number || "Bar number pending"}
                  </div>
                ) : null}
              </section>
            ) : null}

            {isOptSku && result?.upgrade_offer ? (
              <section className="mt-6 rounded-[28px] border border-[#f0d6cf] bg-[#fff7f4] p-6 shadow-[0_18px_48px_rgba(128,84,61,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#a56b52]">Upgrade path</div>
                <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#532d20]">Attorney requested strategy review</h2>
                <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#7d5649]">
                  {result.upgrade_offer.reason}
                </p>
                <div className="mt-4 rounded-[22px] border border-[#efd4cc] bg-white/80 px-5 py-4 text-[14px] leading-7 text-[#6b473c]">
                  Guardian is carrying forward a {formatMoney(result.upgrade_offer.credit_cents / 100)} filing-support credit into the upgraded order.
                </div>
                {result.upgrade_offer.accepted_order_id ? (
                  <Link
                    href={`/account/orders/${result.upgrade_offer.accepted_order_id}`}
                    className="mt-5 inline-flex rounded-full bg-[#532d20] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#432419]"
                  >
                    Open upgraded order
                  </Link>
                ) : (
                  <button
                    type="button"
                    onClick={() => void handleAcceptUpgrade()}
                    disabled={busyAction === "upgrade"}
                    className="mt-5 inline-flex rounded-full bg-[#532d20] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#432419] disabled:cursor-not-allowed disabled:bg-[#b08d82]"
                  >
                    {busyAction === "upgrade" ? "Creating upgraded order..." : "Continue with strategy review"}
                  </button>
                )}
              </section>
            ) : null}

            {isSlice3Sku && order.intake_complete && !order.result_ready ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Processing</div>
                    <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">Run this order</h2>
                    <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                      Intake is saved. Run the product workflow to generate the report, packet, or filing guidance.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleProcessOrder()}
                    disabled={busyAction === "process"}
                    className="inline-flex rounded-full bg-[#5b8dee] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_14px_30px_rgba(91,141,238,0.24)] transition hover:bg-[#4f82de] disabled:cursor-not-allowed disabled:bg-[#9db8e6]"
                  >
                    {busyAction === "process" ? "Processing..." : "Run now"}
                  </button>
                </div>
              </section>
            ) : null}

            {renderResultSection()}

            {isOptSku && result?.receipt_number ? (
              <section className="mt-6 rounded-[28px] border border-[#cfe7d3] bg-[#f3fbf4] p-6 shadow-[0_18px_48px_rgba(50,98,71,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5b8669]">Receipt</div>
                <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#183926]">{result.receipt_number}</h2>
                <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#326247]">
                  {result.filing_confirmation || "The attorney recorded the filing confirmation for this case."}
                </p>
              </section>
            ) : null}

            {order.delivery_method === "user_mail" && order.product_sku !== "form_8843_free" && order.result_ready ? (
              <section className="mt-6 rounded-[28px] border border-[#f1e3b4] bg-[#fff9eb] p-6 shadow-[0_18px_48px_rgba(118,91,22,0.08)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9b7a22]">Mailing confirmation</div>
                <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#6b5214]">Record when you mailed this packet</h2>
                <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#856921]">
                  This workflow ends with a physical mailing step. Save the tracking number once you have sent the packet.
                </p>
                <div className="mt-5 grid gap-4 md:grid-cols-[1fr,auto]">
                  <label className="rounded-[22px] border border-[#ebd7a2] bg-white/75 p-4">
                    <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[#9b7a22]">Tracking number</div>
                    <input
                      value={trackingNumber}
                      onChange={(event) => setTrackingNumber(event.target.value)}
                      className="mt-2 w-full rounded-2xl border border-[#ebd7a2] bg-white px-4 py-3 text-[14px] text-[#6b5214] outline-none transition focus:border-[#d4ab3a]"
                      placeholder="9407 1000 0000 0000 1234 56"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => void handleMarkMailed()}
                    disabled={busyAction === "mail" || order.mailing_status === "mailed"}
                    className="self-end inline-flex rounded-full bg-[#c98f20] px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-[#b8821b] disabled:cursor-not-allowed disabled:bg-[#e0c27c]"
                  >
                    {order.mailing_status === "mailed"
                      ? "Already marked mailed"
                      : busyAction === "mail"
                        ? "Saving..."
                        : "Mark as mailed"}
                  </button>
                </div>
              </section>
            ) : null}

            {form8843Order ? (
              <FilingChecklistCard
                order={form8843Order}
                onOrderChange={(nextOrder) => {
                  setOrder((current) => {
                    if (!current) {
                      return current;
                    }
                    return {
                      ...current,
                      ...nextOrder,
                    };
                  });
                }}
              />
            ) : null}

            {!isSlice3Sku && !isOptSku && !form8843Order ? (
              <section className="mt-6 rounded-[28px] border border-[#dbe5f2] bg-white/82 p-6 shadow-[0_20px_60px_rgba(61,84,128,0.06)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#7b8ba5]">Workflow</div>
                <h2 className="mt-3 text-[24px] font-bold tracking-tight text-[#0d1424]">This order type is not implemented yet</h2>
                <p className="mt-3 max-w-3xl text-[15px] leading-7 text-[#556480]">
                  The catalog entry exists, but the interactive account workflow for this product is still pending the earlier marketplace checkout slice.
                </p>
              </section>
            ) : null}
          </>
        ) : null}
      </div>
    </main>
  );
}
