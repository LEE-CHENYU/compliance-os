"use client";

import { useCallback, useEffect, useState } from "react";
import { getAnswers, saveAnswer } from "@/lib/api";

export interface StepDef {
  key: string;
  label: string;
  track?: string; // "tax" | "immigration" | "corporate" | undefined (shared)
  condition?: (answers: Record<string, unknown>) => boolean;
}

const ALL_STEPS: StepDef[] = [
  // --- Shared intake ---
  { key: "concern_area", label: "Concerns" },
  { key: "existing_help", label: "Professionals" },
  { key: "timeline_urgency", label: "Timeline" },

  // --- Tax track ---
  {
    key: "tax_residency_status",
    label: "Tax Residency",
    track: "tax",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Tax Filing"),
  },
  {
    key: "tax_filing_stage",
    label: "Filing Stage",
    track: "tax",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Tax Filing"),
  },
  {
    key: "tax_prior_filings",
    label: "Prior Filings",
    track: "tax",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Tax Filing"),
  },
  {
    key: "tax_income_sources",
    label: "Income Sources",
    track: "tax",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Tax Filing"),
  },
  {
    key: "tax_entities",
    label: "Tax Entities",
    track: "tax",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Tax Filing"),
  },

  // --- Immigration track ---
  {
    key: "imm_visa_category",
    label: "Visa Status",
    track: "immigration",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Immigration"),
  },
  {
    key: "imm_subdomain",
    label: "Immigration Need",
    track: "immigration",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Immigration"),
  },
  {
    key: "imm_stage",
    label: "Case Stage",
    track: "immigration",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Immigration"),
  },

  // --- Corporate track ---
  {
    key: "corp_entities",
    label: "Entities",
    track: "corporate",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Corporate Compliance"),
  },
  {
    key: "corp_obligations",
    label: "Obligations",
    track: "corporate",
    condition: (a) => ((a.concern_area as string[]) || []).includes("Corporate Compliance"),
  },

  // --- Summary ---
  { key: "summary", label: "Summary" },
];

export function useWizard(caseId: string) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const visibleSteps = ALL_STEPS.filter(
    (s) => !s.condition || s.condition(answers)
  );

  const currentStep = visibleSteps[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === visibleSteps.length - 1;

  useEffect(() => {
    getAnswers(caseId)
      .then((data) => {
        const restored: Record<string, unknown> = {};
        for (const a of data.answers) {
          restored[a.question_key] = a.answer;
        }
        setAnswers(restored);
      })
      .finally(() => setLoading(false));
  }, [caseId]);

  const setAnswer = useCallback((key: string, value: unknown) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }, []);

  const save = useCallback(
    async (key: string, value: unknown) => {
      setSaving(true);
      try {
        await saveAnswer(caseId, key, key, value);
      } finally {
        setSaving(false);
      }
    },
    [caseId]
  );

  const next = useCallback(async () => {
    if (!currentStep || isLast) return;
    const key = currentStep.key;
    const value = answers[key];
    if (value !== undefined && key !== "summary") {
      await save(key, value);
    }
    setCurrentIndex((i) => Math.min(i + 1, visibleSteps.length - 1));
  }, [currentStep, isLast, answers, save, visibleSteps.length]);

  const back = useCallback(() => {
    setCurrentIndex((i) => Math.max(i - 1, 0));
  }, []);

  return {
    answers,
    setAnswer,
    currentStep,
    currentIndex,
    visibleSteps,
    isFirst,
    isLast,
    loading,
    saving,
    next,
    back,
  };
}
