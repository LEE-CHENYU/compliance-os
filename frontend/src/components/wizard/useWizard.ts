"use client";

import { useCallback, useEffect, useState } from "react";
import { getAnswers, saveAnswer } from "@/lib/api";

export interface StepDef {
  key: string;
  label: string;
  condition?: (answers: Record<string, unknown>) => boolean;
}

const ALL_STEPS: StepDef[] = [
  { key: "concern_area", label: "Concerns" },
  { key: "current_stage", label: "Stage" },
  { key: "existing_help", label: "Professionals" },
  {
    key: "residency_status",
    label: "Residency",
    condition: (a) => {
      const concerns = (a.concern_area as string[]) || [];
      return concerns.includes("Immigration") || concerns.includes("Tax Filing");
    },
  },
  { key: "timeline_urgency", label: "Timeline" },
  {
    key: "prior_filings",
    label: "Prior Filings",
    condition: (a) => {
      const concerns = (a.concern_area as string[]) || [];
      return concerns.includes("Tax Filing");
    },
  },
  { key: "entities", label: "Entities" },
  { key: "summary", label: "Summary" },
];

export function useWizard(caseId: string) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Compute visible steps based on current answers
  const visibleSteps = ALL_STEPS.filter(
    (s) => !s.condition || s.condition(answers)
  );

  const currentStep = visibleSteps[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === visibleSteps.length - 1;

  // Load existing answers on mount
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
