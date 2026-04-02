"use client";

import { useParams, useRouter } from "next/navigation";
import { useWizard } from "@/components/wizard/useWizard";
import WizardShell from "@/components/wizard/WizardShell";
import ConcernAreaStep from "@/components/wizard/steps/ConcernAreaStep";
import ExistingHelpStep from "@/components/wizard/steps/ExistingHelpStep";
import TimelineStep from "@/components/wizard/steps/TimelineStep";
import TaxResidencyStep from "@/components/wizard/steps/TaxResidencyStep";
import TaxFilingStageStep from "@/components/wizard/steps/TaxFilingStageStep";
import PriorFilingsStep from "@/components/wizard/steps/PriorFilingsStep";
import TaxIncomeSourcesStep from "@/components/wizard/steps/TaxIncomeSourcesStep";
import EntitiesStep from "@/components/wizard/steps/EntitiesStep";
import ImmVisaCategoryStep from "@/components/wizard/steps/ImmVisaCategoryStep";
import ImmSubdomainStep from "@/components/wizard/steps/ImmSubdomainStep";
import ImmStageStep from "@/components/wizard/steps/ImmStageStep";
import CorpObligationsStep from "@/components/wizard/steps/CorpObligationsStep";
import SummaryStep from "@/components/wizard/steps/SummaryStep";
import ChatPanel from "@/components/chat/ChatPanel";
import { generateSummary } from "@/lib/api";
import { useState } from "react";

export default function DiscoveryPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const wizard = useWizard(caseId);
  const [showChat, setShowChat] = useState(false);

  if (wizard.loading) return <p className="text-stone-400 text-center py-20">Loading...</p>;

  const handleConfirmSummary = async () => {
    await generateSummary(caseId);
    setShowChat(true);
  };

  // Track indicator for the current step
  const trackLabel = wizard.currentStep?.track
    ? { tax: "Tax Filing", immigration: "Immigration", corporate: "Corporate" }[wizard.currentStep.track]
    : null;

  const renderStep = () => {
    if (!wizard.currentStep) return null;
    const key = wizard.currentStep.key;
    const a = wizard.answers;

    switch (key) {
      // Shared steps
      case "concern_area":
        return <ConcernAreaStep value={(a.concern_area as string[]) || []} onChange={(v) => wizard.setAnswer("concern_area", v)} />;
      case "existing_help":
        return <ExistingHelpStep value={(a.existing_help as string[]) || []} onChange={(v) => wizard.setAnswer("existing_help", v)} />;
      case "timeline_urgency":
        return <TimelineStep value={(a.timeline_urgency as { date: string; description: string }) || { date: "", description: "" }} onChange={(v) => wizard.setAnswer("timeline_urgency", v)} />;

      // Tax track
      case "tax_residency_status":
        return <TaxResidencyStep value={a.tax_residency_status ? [a.tax_residency_status as string] : []} onChange={(v) => wizard.setAnswer("tax_residency_status", v[0] || "")} />;
      case "tax_filing_stage":
        return <TaxFilingStageStep value={a.tax_filing_stage ? [a.tax_filing_stage as string] : []} onChange={(v) => wizard.setAnswer("tax_filing_stage", v[0] || "")} />;
      case "tax_prior_filings":
        return <PriorFilingsStep value={(a.tax_prior_filings as string[]) || []} onChange={(v) => wizard.setAnswer("tax_prior_filings", v)} />;
      case "tax_income_sources":
        return <TaxIncomeSourcesStep value={(a.tax_income_sources as string[]) || []} onChange={(v) => wizard.setAnswer("tax_income_sources", v)} />;
      case "tax_entities":
        return <EntitiesStep value={(a.tax_entities as { name: string; type: string; state: string; ein: string }[]) || []} onChange={(v) => wizard.setAnswer("tax_entities", v)} />;

      // Immigration track
      case "imm_visa_category":
        return <ImmVisaCategoryStep value={a.imm_visa_category ? [a.imm_visa_category as string] : []} onChange={(v) => wizard.setAnswer("imm_visa_category", v[0] || "")} />;
      case "imm_subdomain":
        return <ImmSubdomainStep value={(a.imm_subdomain as string[]) || []} onChange={(v) => wizard.setAnswer("imm_subdomain", v)} visaCategory={(a.imm_visa_category as string) || ""} />;
      case "imm_stage":
        return <ImmStageStep value={a.imm_stage ? [a.imm_stage as string] : []} onChange={(v) => wizard.setAnswer("imm_stage", v[0] || "")} />;

      // Corporate track
      case "corp_entities":
        return <EntitiesStep value={(a.corp_entities as { name: string; type: string; state: string; ein: string }[]) || []} onChange={(v) => wizard.setAnswer("corp_entities", v)} />;
      case "corp_obligations":
        return <CorpObligationsStep value={(a.corp_obligations as string[]) || []} onChange={(v) => wizard.setAnswer("corp_obligations", v)} />;

      // Summary
      case "summary":
        return <SummaryStep answers={a} />;
      default:
        return null;
    }
  };

  if (showChat) {
    return (
      <div className="mx-auto max-w-xl space-y-6">
        <SummaryStep answers={wizard.answers} />
        <div className="border-t border-stone-200 pt-6">
          <ChatPanel caseId={caseId} />
        </div>
        <div className="flex justify-center">
          <button
            onClick={() => router.push(`/case/${caseId}/documents`)}
            className="rounded-lg bg-stone-800 px-6 py-3 text-white font-medium hover:bg-stone-700 transition-colors"
          >
            Proceed to Documents
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {trackLabel && (
        <div className="mx-auto max-w-xl mb-2">
          <span className="inline-block rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
            {trackLabel}
          </span>
        </div>
      )}
      <WizardShell
        currentIndex={wizard.currentIndex}
        steps={wizard.visibleSteps}
        isFirst={wizard.isFirst}
        isLast={wizard.isLast}
        saving={wizard.saving}
        onBack={wizard.back}
        onNext={wizard.isLast ? handleConfirmSummary : wizard.next}
        nextLabel={wizard.isLast ? "Confirm & Continue" : undefined}
        nextDisabled={!wizard.currentStep}
      >
        {renderStep()}
      </WizardShell>
    </div>
  );
}
