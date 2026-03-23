"use client";

import { useEffect } from "react";
import ProgressBar from "@/components/ui/ProgressBar";
import type { StepDef } from "./useWizard";

interface Props {
  currentIndex: number;
  steps: StepDef[];
  isFirst: boolean;
  isLast: boolean;
  saving: boolean;
  onBack: () => void;
  onNext: () => void;
  nextDisabled?: boolean;
  nextLabel?: string;
  children: React.ReactNode;
}

export default function WizardShell({
  currentIndex, steps, isFirst, isLast,
  saving, onBack, onNext, nextDisabled,
  nextLabel, children,
}: Props) {
  // Keyboard navigation: Enter to advance, Backspace to go back
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't intercept when user is typing in an input/textarea
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "Enter" && !nextDisabled && !saving) {
        e.preventDefault();
        onNext();
      } else if (e.key === "Backspace" && !isFirst) {
        e.preventDefault();
        onBack();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onNext, onBack, nextDisabled, saving, isFirst]);

  return (
    <div className="mx-auto max-w-xl space-y-8">
      <ProgressBar
        currentStep={currentIndex}
        totalSteps={steps.length}
        labels={steps.map((s) => s.label)}
      />
      <div className="min-h-[300px]">{children}</div>
      <div className="flex justify-between">
        <button
          onClick={onBack}
          disabled={isFirst}
          className="rounded-lg border border-stone-300 px-5 py-2.5 text-sm font-medium disabled:opacity-30 hover:bg-stone-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={onNext}
          disabled={nextDisabled || saving}
          className="rounded-lg bg-stone-800 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50 hover:bg-stone-700 transition-colors"
        >
          {saving ? "Saving..." : nextLabel || (isLast ? "Confirm" : "Continue")}
        </button>
      </div>
    </div>
  );
}
