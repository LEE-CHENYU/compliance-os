"use client";

import { useParams, useRouter } from "next/navigation";
import { useWizard } from "@/components/wizard/useWizard";
import WizardShell from "@/components/wizard/WizardShell";
import ConcernAreaStep from "@/components/wizard/steps/ConcernAreaStep";
import CurrentStageStep from "@/components/wizard/steps/CurrentStageStep";
import ExistingHelpStep from "@/components/wizard/steps/ExistingHelpStep";
import ResidencyStep from "@/components/wizard/steps/ResidencyStep";
import TimelineStep from "@/components/wizard/steps/TimelineStep";
import PriorFilingsStep from "@/components/wizard/steps/PriorFilingsStep";
import EntitiesStep from "@/components/wizard/steps/EntitiesStep";
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

  const renderStep = () => {
    if (!wizard.currentStep) return null;
    const key = wizard.currentStep.key;
    switch (key) {
      case "concern_area":
        return <ConcernAreaStep value={(wizard.answers.concern_area as string[]) || []} onChange={(v) => wizard.setAnswer("concern_area", v)} />;
      case "current_stage":
        return <CurrentStageStep value={(wizard.answers.current_stage as string[]) || []} onChange={(v) => wizard.setAnswer("current_stage", v)} concerns={(wizard.answers.concern_area as string[]) || []} />;
      case "existing_help":
        return <ExistingHelpStep value={(wizard.answers.existing_help as string[]) || []} onChange={(v) => wizard.setAnswer("existing_help", v)} />;
      case "residency_status":
        return <ResidencyStep value={wizard.answers.residency_status ? [wizard.answers.residency_status as string] : []} onChange={(v) => wizard.setAnswer("residency_status", v[0] || "")} />;
      case "timeline_urgency":
        return <TimelineStep value={(wizard.answers.timeline_urgency as { date: string; description: string }) || { date: "", description: "" }} onChange={(v) => wizard.setAnswer("timeline_urgency", v)} />;
      case "prior_filings":
        return <PriorFilingsStep value={(wizard.answers.prior_filings as string[]) || []} onChange={(v) => wizard.setAnswer("prior_filings", v)} />;
      case "entities":
        return <EntitiesStep value={(wizard.answers.entities as { name: string; type: string; state: string; ein: string }[]) || []} onChange={(v) => wizard.setAnswer("entities", v)} />;
      case "summary":
        return <SummaryStep answers={wizard.answers} />;
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
  );
}
