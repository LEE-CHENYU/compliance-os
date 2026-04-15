"use client";

import Vapi from "@vapi-ai/web";
import type { ClientMessageTranscript, CreateAssistantDTO, OpenAIModel, VapiVoice } from "@vapi-ai/web/dist/api";
import { useCallback, useEffect, useState, useRef, type ChangeEvent, type ComponentPropsWithoutRef, type DragEvent as ReactDragEvent } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn, authHeaders, getUser, logout } from "@/lib/auth";
import ReactMarkdown from "react-markdown";
import ModeBar, { ChatMode } from "@/components/chat/ModeBar";
import FormFillerUpload from "@/components/chat/FormFillerUpload";
import FormPreviewCard, { FieldProposal } from "@/components/chat/FormPreviewCard";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { useTheme } from "@/lib/theme";

interface TimelineEvent {
  date: string;
  title: string;
  type: string;
  category: string | null;
  chain?: TimelineChainRef | null;
  documents: { id: string; filename: string; doc_type: string; category: string }[];
  risks: {
    id: string;
    title: string;
    action: string;
    consequence: string;
    immigration_impact: boolean;
    severity: string;
    documents?: { id: string; filename: string; doc_type: string; category: string }[];
  }[];
}

interface TimelineChainRef {
  type: string;
  key: string;
  label: string;
  employer_name?: string | null;
  start_date?: string | null;
  source_context?: string | null;
}

interface UploadPrompt {
  doc_type: string;
  prompt: string;
  why: string;
  event_date?: string;
}

interface IntegrityIssue {
  issue_code: string;
  severity: string;
  title: string;
  message: string;
  documents: { id: string; filename: string; doc_type: string; category: string }[];
  chains: TimelineChainRef[];
  details?: Record<string, unknown>;
}

interface AssistantPromptChoice {
  label: string;
  value: string;
  action_type: "chat_answer" | "integrity_resolution";
  question_id?: string;
  prompt_id?: string;
  action?: string;
  chain_key?: string | null;
  document_id?: string;
}

interface AssistantPrompt {
  id: string;
  kind: string;
  issue_code: string;
  text: string;
  documents: DashboardDocumentLink[];
  chains: TimelineChainRef[];
  choices: {
    label: string;
    action: string;
    chain_key: string | null;
  }[];
  cadence_seconds?: number;
}

interface ChatReferenceDoc {
  id: string;
  filename: string;
  doc_type: string;
  score?: number;
}

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  chips?: AssistantPromptChoice[];
  references?: ChatReferenceDoc[];
  mode?: ChatMode;
}

type VoiceCallState = "idle" | "connecting" | "active" | "ended" | "error";

interface Stats {
  documents: number;
  risks: number;
  verified: number;
  next_deadline_days: number | null;
}

interface OpenClawTokenInfo {
  label: string;
  token_type: string;
  scope: string;
  token_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

interface OpenClawConnectionStatus {
  api_url: string;
  install_command: string;
  env_var: string;
  token_type: string;
  scope: string;
  active_token: OpenClawTokenInfo | null;
}

interface OpenClawTokenIssueResponse extends OpenClawConnectionStatus {
  token: string;
}

interface TimelineData {
  events: TimelineEvent[];
  findings: unknown[];
  advisories: { id: string; title: string; action: string; consequence: string }[];
  integrity_issues: IntegrityIssue[];
  assistant_prompts: AssistantPrompt[];
  upload_prompts: UploadPrompt[];
  key_facts: { label: string; value: string }[];
  deadlines: { title: string; date: string; days: number; category: string; severity: string; action: string }[];
  service_summary?: DashboardServiceSummary;
}

interface DashboardServiceProduct {
  sku: string;
  name: string;
  description: string;
  price_cents: number;
  category: string | null;
  headline: string | null;
  cta_label: string | null;
  path: string | null;
}

interface DashboardServiceOrder {
  order_id: string;
  product_sku: string;
  product_name: string;
  product: DashboardServiceProduct;
  status: string;
  status_label: string;
  attention_state: "urgent" | "active" | "complete";
  summary: string;
  next_action: string;
  filing_deadline: string | null;
  deadline_days: number | null;
  mailing_status: string;
  href: string;
  cta_label: string;
}

interface DashboardServiceRecommendation {
  sku: string;
  name: string;
  reason: string;
  priority: number;
  product: DashboardServiceProduct;
  href: string;
  cta_label: string;
}

interface DashboardServiceSummary {
  active_orders: DashboardServiceOrder[];
  recent_completed: DashboardServiceOrder[];
  recommended_services: DashboardServiceRecommendation[];
  service_deadlines: { title: string; date: string; days: number; category: string; severity: string; action: string }[];
  stats: {
    active_orders: number;
    recent_completed: number;
    recommended_services: number;
  };
}

interface UploadDuplicateCandidate {
  id: string;
  check_id: string;
  filename: string;
  doc_type: string;
  source_path: string | null;
  uploaded_at: string | null;
  is_active: boolean;
  content_hash: string | null;
}

interface SelectedUploadFile {
  file: File;
  sourcePath: string | null;
}

interface PreparedUploadItem {
  file: File;
  sourcePath: string | null;
  fileName: string;
  mimeType: string;
  fileSize: number;
  resolvedDocType: string | null;
  classificationSource: string | null;
  confidence: string | null;
  status: "ready" | "duplicate" | "invalid" | "unresolved";
  message: string | null;
  contentHash: string | null;
  duplicates: UploadDuplicateCandidate[];
  action: "upload" | "skip";
}

interface DashboardDocumentLink {
  id: string;
  filename: string;
  doc_type: string;
  category: string;
}

interface ProcessingIndicatorState {
  progress: number;
  title: string;
  detail: string;
}

const API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://127.0.0.1:8000/api/dashboard"
  : "/api/dashboard";
const FORM_FILL_API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://127.0.0.1:8000/api/form-fill"
  : "/api/form-fill";
const AUTH_API = typeof window !== "undefined" && window.location.hostname === "localhost"
  ? "http://127.0.0.1:8000/api/auth"
  : "/api/auth";

const DASHBOARD_ACCEPT = ".pdf,.png,.jpg,.jpeg,.csv,.txt,.docx";
const VOICE_CONVERSATION_STARTER = "Give me a brief spoken review of my current dashboard: the top-line issues, the next deadline, and the single most useful next step. Then ask me one concise follow-up question to continue the conversation naturally.";
const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY?.trim();
const SUPPORTED_GUARDIAN_VOICE_MODELS = ["gpt-4.1-mini", "gpt-4.1", "gpt-5-mini", "gpt-5"] as const satisfies readonly OpenAIModel["model"][];
const SUPPORTED_GUARDIAN_VOICE_IDS = ["Elliot", "Kylie", "Rohan", "Lily", "Savannah", "Hana", "Neha", "Cole", "Harry", "Paige", "Spencer", "Leah", "Tara"] as const satisfies readonly VapiVoice["voiceId"][];
const GUARDIAN_VOICE_PROMPT = [
  "You are Guardian, a calm voice guide for a user's compliance dashboard.",
  "Open with a concise dashboard review, not a generic greeting.",
  "Summarize the top-line issues, the next deadline, and the single best next step.",
  "Keep each turn natural and spoken, with short sentences and no markdown.",
  "Ask at most one short follow-up question at a time.",
  "Frame risks as things worth checking, not definitive legal conclusions.",
  "You are not a lawyer and should not provide legal advice.",
].join(" ");

function resolveGuardianVoiceModel(value?: string) {
  const nextModel = value?.trim();
  return SUPPORTED_GUARDIAN_VOICE_MODELS.find((model) => model === nextModel) || "gpt-4.1-mini";
}

function resolveGuardianVoiceId(value?: string) {
  const nextVoiceId = value?.trim();
  return SUPPORTED_GUARDIAN_VOICE_IDS.find((voiceId) => voiceId === nextVoiceId) || "Elliot";
}

const GUARDIAN_VOICE_MODEL = resolveGuardianVoiceModel(process.env.NEXT_PUBLIC_GUARDIAN_VOICE_MODEL);
const GUARDIAN_VOICE_ID = resolveGuardianVoiceId(process.env.NEXT_PUBLIC_GUARDIAN_VOICE_ID);

type CategoryPalette = { bg: string; text: string; border: string; label: string };

const CATEGORY_COLORS: Record<string, CategoryPalette> = {
  student_status: { bg: "rgba(6,182,212,0.1)", text: "#0891b2", border: "rgba(6,182,212,0.12)", label: "Student Status" },
  immigration: { bg: "rgba(99,102,241,0.1)", text: "#4f46e5", border: "rgba(99,102,241,0.12)", label: "Immigration" },
  work_auth: { bg: "rgba(245,158,11,0.1)", text: "#d97706", border: "rgba(245,158,11,0.12)", label: "Employment" },
  employment: { bg: "rgba(245,158,11,0.1)", text: "#d97706", border: "rgba(245,158,11,0.12)", label: "Employment" },
  tax: { bg: "rgba(16,185,129,0.1)", text: "#059669", border: "rgba(16,185,129,0.12)", label: "Tax" },
  entity: { bg: "rgba(124,58,237,0.1)", text: "#7c3aed", border: "rgba(124,58,237,0.12)", label: "Business" },
  business: { bg: "rgba(124,58,237,0.1)", text: "#7c3aed", border: "rgba(124,58,237,0.12)", label: "Business" },
  personal: { bg: "rgba(236,72,153,0.1)", text: "#db2777", border: "rgba(236,72,153,0.12)", label: "Personal" },
  other: { bg: "rgba(107,114,128,0.1)", text: "#6b7280", border: "rgba(107,114,128,0.12)", label: "Other" },
};

// Softer, lower-saturation variants for dark mode. Same hue, brighter text for
// legibility against dark bg, and a slightly more visible bg tint.
const CATEGORY_COLORS_DARK: Record<string, CategoryPalette> = {
  student_status: { bg: "rgba(6,182,212,0.16)", text: "#67e8f9", border: "rgba(6,182,212,0.25)", label: "Student Status" },
  immigration: { bg: "rgba(99,102,241,0.16)", text: "#a5b4fc", border: "rgba(99,102,241,0.25)", label: "Immigration" },
  work_auth: { bg: "rgba(245,158,11,0.16)", text: "#fcd34d", border: "rgba(245,158,11,0.25)", label: "Employment" },
  employment: { bg: "rgba(245,158,11,0.16)", text: "#fcd34d", border: "rgba(245,158,11,0.25)", label: "Employment" },
  tax: { bg: "rgba(16,185,129,0.16)", text: "#6ee7b7", border: "rgba(16,185,129,0.25)", label: "Tax" },
  entity: { bg: "rgba(124,58,237,0.16)", text: "#c4b5fd", border: "rgba(124,58,237,0.25)", label: "Business" },
  business: { bg: "rgba(124,58,237,0.16)", text: "#c4b5fd", border: "rgba(124,58,237,0.25)", label: "Business" },
  personal: { bg: "rgba(236,72,153,0.16)", text: "#f9a8d4", border: "rgba(236,72,153,0.25)", label: "Personal" },
  other: { bg: "rgba(107,114,128,0.18)", text: "#9ca3af", border: "rgba(107,114,128,0.28)", label: "Other" },
};

function clampProgress(progress: number): number {
  return Math.min(1, Math.max(0, progress));
}

function stripMarkdownForTranscript(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getVoiceErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  if (error && typeof error === "object") {
    const maybeError = error as {
      message?: unknown;
      error?: unknown;
      errorMsg?: unknown;
      reason?: unknown;
      details?: unknown;
    };

    if (typeof maybeError.message === "string" && maybeError.message.trim()) {
      return maybeError.message;
    }

    if (typeof maybeError.errorMsg === "string" && maybeError.errorMsg.trim()) {
      return maybeError.errorMsg;
    }

    if (typeof maybeError.reason === "string" && maybeError.reason.trim()) {
      return maybeError.reason;
    }

    if (maybeError.error) {
      const nestedError = getVoiceErrorMessage(maybeError.error);
      if (nestedError !== "Voice assistant failed to start.") {
        return nestedError;
      }
    }

    if (maybeError.details) {
      const nestedDetails = getVoiceErrorMessage(maybeError.details);
      if (nestedDetails !== "Voice assistant failed to start.") {
        return nestedDetails;
      }
    }
  }

  return "Voice assistant failed to start.";
}

function isVoiceConversationEndedMessage(message: string) {
  const normalized = message.toLowerCase();
  return normalized.includes("meeting has ended")
    || normalized.includes("conversation ended")
    || normalized.includes("ended due to ejection")
    || normalized.includes("call has ended")
    || normalized.includes("customer-ended-call");
}

function isTranscriptMessage(message: unknown): message is ClientMessageTranscript {
  return Boolean(
    message
      && typeof message === "object"
      && "type" in message
      && typeof (message as { type?: string }).type === "string"
      && (message as { type: string }).type.startsWith("transcript"),
  );
}

function isStatusUpdateMessage(message: unknown): message is { type: "status-update"; status: string; endedReason?: string } {
  return Boolean(
    message
      && typeof message === "object"
      && "type" in message
      && "status" in message
      && (message as { type?: string }).type === "status-update"
      && typeof (message as { status?: string }).status === "string",
  );
}

function buildVoiceContextMessage(
  timeline: TimelineData | null,
  stats: Stats | null,
  documents: { filename: string; doc_type: string; category: string }[],
) {
  const keyFacts = (timeline?.key_facts || []).slice(0, 8)
    .map((fact) => `${fact.label}: ${fact.value}`)
    .join("\n");
  const advisories = (timeline?.advisories || []).slice(0, 4)
    .map((advisory) => `${advisory.title} — ${advisory.action}`)
    .join("\n");
  const integrityIssues = (timeline?.integrity_issues || []).slice(0, 3)
    .map((issue) => `${issue.title} — ${issue.message}`)
    .join("\n");
  const deadlines = (timeline?.deadlines || []).slice(0, 4)
    .map((deadline) => `${deadline.title} | ${deadline.date} | ${deadline.days} days`)
    .join("\n");
  const documentLines = documents.slice(0, 8)
    .map((document) => `${document.filename} (${document.doc_type}, ${document.category})`)
    .join("\n");
  const serviceOrders = (timeline?.service_summary?.active_orders || []).slice(0, 4)
    .map((order) => `${order.product_name} | ${order.status_label} | ${order.next_action}`)
    .join("\n");
  const serviceRecommendations = (timeline?.service_summary?.recommended_services || []).slice(0, 4)
    .map((service) => `${service.name} — ${service.reason}`)
    .join("\n");

  return [
    VOICE_CONVERSATION_STARTER,
    "",
    `Dashboard snapshot: ${stats?.documents || 0} documents, ${stats?.risks || 0} needs-attention items, ${(timeline?.advisories || []).length} potential risks, next deadline in ${stats?.next_deadline_days ?? "unknown"} days.`,
    deadlines ? `Deadlines:\n${deadlines}` : "Deadlines: none available.",
    advisories ? `Potential risks:\n${advisories}` : "Potential risks: none available.",
    integrityIssues ? `Data gaps:\n${integrityIssues}` : "Data gaps: none available.",
    serviceOrders ? `Active services:\n${serviceOrders}` : "Active services: none available.",
    serviceRecommendations ? `Suggested services:\n${serviceRecommendations}` : "Suggested services: none available.",
    keyFacts ? `Key facts:\n${keyFacts}` : "Key facts: none available.",
    documentLines ? `Documents on file:\n${documentLines}` : "Documents on file: none available.",
  ].join("\n\n");
}

function createGuardianVoiceAssistant(): CreateAssistantDTO {
  return {
    firstMessageMode: "assistant-waits-for-user",
    backgroundSound: "off",
    maxDurationSeconds: 1200,
    model: {
      provider: "openai",
      model: GUARDIAN_VOICE_MODEL,
      messages: [
        {
          role: "system",
          content: GUARDIAN_VOICE_PROMPT,
        },
      ],
    },
    transcriber: {
      provider: "deepgram",
      model: "flux-general-en",
      language: "en",
    },
    voice: {
      provider: "vapi",
      voiceId: GUARDIAN_VOICE_ID,
      speed: 1.02,
    },
  };
}

function ProgressRing({
  progress,
  size = 36,
  label,
}: {
  progress: number;
  size?: number;
  label?: string;
}) {
  const normalizedProgress = clampProgress(progress);
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      aria-label={label || `Progress ${Math.round(normalizedProgress * 100)} percent`}
      role="img"
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(#5b8dee ${normalizedProgress * 360}deg, rgba(91,141,238,0.14) ${normalizedProgress * 360}deg 360deg)`,
        }}
      />
      <div className="absolute inset-[4px] rounded-full bg-white/85 backdrop-blur-sm" />
      <div className="absolute inset-0 flex items-center justify-center text-[9px] font-semibold text-[#3d6bc5]">
        {Math.round(normalizedProgress * 100)}%
      </div>
    </div>
  );
}

function normalizeSelectedSourcePath(file: File): string | null {
  const relativePath = "webkitRelativePath" in file
    ? (file as File & { webkitRelativePath: string }).webkitRelativePath
    : "";
  if (relativePath && relativePath.length > 0) {
    return relativePath;
  }
  return file.name || null;
}

function dedupeSelectedUploads(items: SelectedUploadFile[]): SelectedUploadFile[] {
  const seen = new Set<string>();
  const unique: SelectedUploadFile[] = [];
  for (const item of items) {
    const key = [
      item.sourcePath || item.file.name,
      item.file.size,
      item.file.lastModified,
      item.file.type,
    ].join(":");
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(item);
  }
  return unique;
}

function fileFromEntry(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject);
  });
}

function readAllDirectoryEntries(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  return new Promise((resolve, reject) => {
    const entries: FileSystemEntry[] = [];
    const readNext = () => {
      reader.readEntries(
        (batch) => {
          if (!batch.length) {
            resolve(entries);
            return;
          }
          entries.push(...batch);
          readNext();
        },
        reject,
      );
    };
    readNext();
  });
}

async function collectEntryFiles(entry: FileSystemEntry): Promise<SelectedUploadFile[]> {
  if (entry.isFile) {
    const file = await fileFromEntry(entry as FileSystemFileEntry);
    const sourcePath = entry.fullPath ? entry.fullPath.replace(/^\/+/, "") : normalizeSelectedSourcePath(file);
    return [{ file, sourcePath }];
  }
  const children = await readAllDirectoryEntries((entry as FileSystemDirectoryEntry).createReader());
  const nested = await Promise.all(children.map((child) => collectEntryFiles(child)));
  return nested.flat();
}

async function collectDroppedFiles(dataTransfer: DataTransfer): Promise<SelectedUploadFile[]> {
  const items = Array.from(dataTransfer.items || []);
  const withEntries = items
    .map((item) => item.webkitGetAsEntry?.())
    .filter((entry): entry is FileSystemEntry => Boolean(entry));
  if (withEntries.length > 0) {
    const nested = await Promise.all(withEntries.map((entry) => collectEntryFiles(entry)));
    return dedupeSelectedUploads(nested.flat());
  }
  return dedupeSelectedUploads(
    Array.from(dataTransfer.files || []).map((file) => ({
      file,
      sourcePath: normalizeSelectedSourcePath(file),
    })),
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const categoryPalette = theme === "dark" ? CATEGORY_COLORS_DARK : CATEGORY_COLORS;
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const folderRef = useRef<HTMLInputElement | null>(null);
  const [uploadDocType, setUploadDocType] = useState("");
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [showUploadReview, setShowUploadReview] = useState(false);
  const [preparedUploads, setPreparedUploads] = useState<PreparedUploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [view, setView] = useState<"timeline" | "documents" | "profile" | "deadlines">("timeline");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatAnswered, setChatAnswered] = useState<Set<string>>(new Set());
  const [resolvedAssistantPromptIds, setResolvedAssistantPromptIds] = useState<Set<string>>(new Set());
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>("guardian");
  const [formFillLoading, setFormFillLoading] = useState(false);
  const [formFillPreview, setFormFillPreview] = useState<{
    fields: FieldProposal[];
    formFieldCount: number;
    filledCount: number;
    unfilledCount: number;
    originalFile: File;
  } | null>(null);
  const [documents, setDocuments] = useState<{ id: string; filename: string; doc_type: string; file_size: number; uploaded_at: string; category: string }[]>([]);
  const [showToken, setShowToken] = useState(false);
  const [tokenCopied, setTokenCopied] = useState(false);
  const [openClawConnection, setOpenClawConnection] = useState<OpenClawConnectionStatus | null>(null);
  const [openClawToken, setOpenClawToken] = useState<string | null>(null);
  const [openClawLoading, setOpenClawLoading] = useState(false);
  const [openClawError, setOpenClawError] = useState<string | null>(null);
  const [processingIndicator, setProcessingIndicator] = useState<ProcessingIndicatorState | null>(null);
  const [voiceCallState, setVoiceCallState] = useState<VoiceCallState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [assistantTranscript, setAssistantTranscript] = useState("");
  const [userTranscript, setUserTranscript] = useState("");
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [micMuted, setMicMuted] = useState(false);
  const chatMessageCounterRef = useRef(0);
  const processingHideTimeoutRef = useRef<number | null>(null);
  const vapiRef = useRef<Vapi | null>(null);
  const voiceCallStartedRef = useRef(false);
  const guardianMessagesRef = useRef<ChatMessage[]>([]);
  const guardianMessages = chatMessages.filter((message) => message.mode !== "form-filler");
  const formFillerMessages = chatMessages.filter((message) => message.mode === "form-filler");
  const visibleChatMessages = chatMode === "guardian" ? guardianMessages : formFillerMessages;
  const hasGuardianQuestion = guardianMessages.some(
    (message) => message.role === "assistant" && Boolean(message.chips?.length),
  );
  const voiceReady = Boolean(VAPI_PUBLIC_KEY);
  const voiceBusy = voiceCallState === "connecting";
  const voiceActive = voiceCallState === "active";
  const voiceEnded = voiceCallState === "ended";
  const voiceListening = voiceActive && !assistantSpeaking && !micMuted;

  const nextChatMessageId = useCallback(() => {
    chatMessageCounterRef.current += 1;
    return `chat-${chatMessageCounterRef.current}`;
  }, []);

  const updateProcessingIndicator = useCallback((progress: number, title: string, detail: string) => {
    if (processingHideTimeoutRef.current) {
      window.clearTimeout(processingHideTimeoutRef.current);
      processingHideTimeoutRef.current = null;
    }
    setProcessingIndicator({ progress: clampProgress(progress), title, detail });
  }, []);

  const clearProcessingIndicator = useCallback((delay = 0) => {
    if (processingHideTimeoutRef.current) {
      window.clearTimeout(processingHideTimeoutRef.current);
      processingHideTimeoutRef.current = null;
    }
    if (delay <= 0) {
      setProcessingIndicator(null);
      return;
    }
    processingHideTimeoutRef.current = window.setTimeout(() => {
      setProcessingIndicator(null);
      processingHideTimeoutRef.current = null;
    }, delay);
  }, []);

  const refreshDashboard = useCallback(async () => {
    const [tl, st, docs] = await Promise.all([
      fetch(`${API}/timeline`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/stats`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/documents`, { headers: authHeaders() }).then((r) => r.json()),
    ]);
    const hasServiceContent = Boolean(
      tl.service_summary?.active_orders?.length
      || tl.service_summary?.recent_completed?.length
      || tl.service_summary?.recommended_services?.length,
    );
    if (docs.length === 0 && (!tl.events || tl.events.length <= 1) && !hasServiceContent) {
      router.push("/check");
      return;
    }
    setTimeline(tl);
    setStats(st);
    setDocuments(docs);
    setLoading(false);
  }, [router]);

  const openDashboardDocument = useCallback(async (docId: string) => {
    const resp = await fetch(`${API}/documents/${docId}/view`, { headers: authHeaders() });
    if (!resp.ok) {
      throw new Error("Could not open document");
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }, []);

  const renderDocumentChip = useCallback((
    doc: DashboardDocumentLink,
    options?: {
      compact?: boolean;
    },
  ) => {
    const colors = categoryPalette[doc.category] || categoryPalette.immigration;
    const compact = options?.compact ?? false;
    return (
      <button
        key={doc.id}
        type="button"
        onClick={() => {
          openDashboardDocument(doc.id).catch((error) => {
            console.error(error);
          });
        }}
        className={`flex items-center gap-2 rounded-xl border text-left font-medium text-[#3d6bc5] dark:text-[#8aa8e0] shadow-sm transition-all hover:bg-white/80 dark:hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-[#5b8dee]/35 ${
          compact
            ? "px-2.5 py-1.5 text-[11px] bg-white/70 dark:bg-white/5 border-white/70 dark:border-white/10"
            : "px-3 py-2 text-[12px] bg-white/55 dark:bg-white/5 backdrop-blur border-white/60 dark:border-white/10"
        }`}
      >
        <span>📄</span>
        {doc.filename}
        <span
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md capitalize"
          style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}
        >
          {doc.category}
        </span>
      </button>
    );
  }, [openDashboardDocument, categoryPalette]);

  const dashboardPromptApi = `${API}/integrity/respond`;
  const chatApi = typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000/api/chat"
    : "/api/chat";

  const loadOpenClawConnection = useCallback(async () => {
    setOpenClawLoading(true);
    setOpenClawError(null);
    try {
      const resp = await fetch(`${AUTH_API}/openclaw/connection`, { headers: authHeaders() });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.detail || "Could not load OpenClaw connection");
      }
      setOpenClawConnection(data);
    } catch (error) {
      setOpenClawError(error instanceof Error ? error.message : "Could not load OpenClaw connection");
    } finally {
      setOpenClawLoading(false);
    }
  }, []);

  const issueOpenClawToken = useCallback(async () => {
    setOpenClawLoading(true);
    setOpenClawError(null);
    try {
      const resp = await fetch(`${AUTH_API}/openclaw/token`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.detail || "Could not issue OpenClaw token");
      }
      const issued = data as OpenClawTokenIssueResponse;
      setOpenClawConnection(issued);
      setOpenClawToken(issued.token);
    } catch (error) {
      setOpenClawError(error instanceof Error ? error.message : "Could not issue OpenClaw token");
    } finally {
      setOpenClawLoading(false);
    }
  }, []);

  const makeQuestionChips = useCallback((questionId: string, options: string[]) => (
    options.map((option) => ({
      label: option,
      value: option,
      action_type: "chat_answer" as const,
      question_id: questionId,
    }))
  ), []);

  const makeAssistantPromptMessage = useCallback((prompt: AssistantPrompt): ChatMessage => ({
    id: `assistant-prompt:${prompt.id}`,
    role: "assistant",
    text: prompt.text,
    mode: "guardian",
    chips: prompt.choices.map((choice) => ({
      label: choice.label,
      value: choice.label,
      action_type: "integrity_resolution" as const,
      prompt_id: prompt.id,
      action: choice.action,
      chain_key: choice.chain_key,
      document_id: prompt.documents[0]?.id,
    })),
  }), []);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/login");
      return;
    }
    refreshDashboard();
  }, [refreshDashboard, router]);

  useEffect(() => {
    if (!folderRef.current) {
      return;
    }
    folderRef.current.setAttribute("webkitdirectory", "");
    folderRef.current.setAttribute("directory", "");
  }, []);

  useEffect(() => {
    if (!showToken) {
      return;
    }
    setOpenClawToken(null);
    loadOpenClawConnection();
  }, [loadOpenClawConnection, showToken]);

  useEffect(() => {
    guardianMessagesRef.current = guardianMessages;
  }, [guardianMessages]);

  function resetUploadState() {
    setPreparedUploads([]);
    setShowUploadReview(false);
    setUploadError(null);
    setDragActive(false);
    if (fileRef.current) {
      fileRef.current.value = "";
    }
    if (folderRef.current) {
      folderRef.current.value = "";
    }
  }

  async function executeUploadBatch(
    items: PreparedUploadItem[],
    options?: {
      preserveLoading?: boolean;
      reopenReviewOnError?: boolean;
    },
  ) {
    const preserveLoading = options?.preserveLoading ?? false;
    const reopenReviewOnError = options?.reopenReviewOnError ?? true;
    if (!preserveLoading) {
      setUploading(true);
    }
    setUploadError(null);
    try {
      const toUpload = items.filter(
        (item) => item.action === "upload" && (item.status === "ready" || item.status === "duplicate"),
      );
      const totalUploads = Math.max(toUpload.length, 1);
      updateProcessingIndicator(0.22, "Processing documents", `${toUpload.length} file${toUpload.length === 1 ? "" : "s"} queued`);
      for (let index = 0; index < toUpload.length; index += 1) {
        const item = toUpload[index];
        updateProcessingIndicator(
          0.22 + (index / totalUploads) * 0.62,
          "Processing documents",
          `Uploading and analyzing ${index + 1} of ${totalUploads}: ${item.fileName}`,
        );
        const form = new FormData();
        form.append("file", item.file, item.file.name);
        form.append("doc_type", uploadDocType || item.resolvedDocType || "other");
        form.append("duplicate_action", "keep");
        if (item.sourcePath) {
          form.append("source_path", item.sourcePath);
        }
        const resp = await fetch(`${API}/upload`, {
          method: "POST",
          headers: authHeaders(),
          body: form,
        });
        const body = await resp.json().catch(() => null);
        if (!resp.ok) {
          throw new Error(body?.detail?.message || body?.detail || `Upload failed for ${item.fileName}`);
        }
        updateProcessingIndicator(
          0.22 + ((index + 1) / totalUploads) * 0.62,
          "Processing documents",
          `${index + 1} of ${totalUploads} files processed`,
        );
      }
      updateProcessingIndicator(0.92, "Refreshing dashboard", "Updating your timeline and risk summary");
      await refreshDashboard();
      updateProcessingIndicator(1, "Dashboard updated", "Your latest document analysis is ready");
      clearProcessingIndicator(1400);
      setShowUploadPanel(false);
      setUploadDocType("");
      resetUploadState();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      setUploadError(message);
      if (reopenReviewOnError) {
        setShowUploadReview(true);
        clearProcessingIndicator();
      } else {
        updateProcessingIndicator(1, "Upload interrupted", message);
        clearProcessingIndicator(5000);
      }
    } finally {
      if (!preserveLoading) {
        setUploading(false);
      }
    }
  }

  async function prepareUploadBatch(selectedFiles: SelectedUploadFile[]) {
    const uniqueFiles = dedupeSelectedUploads(selectedFiles);
    if (uniqueFiles.length === 0) {
      return;
    }
    setUploading(true);
    setUploadError(null);
    setShowUploadPanel(false);
    updateProcessingIndicator(0.08, "Reviewing files", `${uniqueFiles.length} file${uniqueFiles.length === 1 ? "" : "s"} selected`);
    try {
      const form = new FormData();
      for (const item of uniqueFiles) {
        form.append("files", item.file, item.file.name);
      }
      form.append("source_paths_json", JSON.stringify(uniqueFiles.map((item) => item.sourcePath)));
      if (uploadDocType) {
        form.append("doc_type", uploadDocType);
      }
      const resp = await fetch(`${API}/upload/prepare`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      });
      const body = await resp.json();
      if (!resp.ok) {
        throw new Error(body?.detail || body?.message || "Could not prepare uploads");
      }
      const prepared: PreparedUploadItem[] = body.files.map((item: {
        file_name: string;
        mime_type: string;
        file_size: number;
        resolved_doc_type: string | null;
        classification_source: string | null;
        confidence: string | null;
        status: "ready" | "duplicate" | "invalid" | "unresolved";
        message: string | null;
        content_hash: string | null;
        duplicates: UploadDuplicateCandidate[];
      }, index: number) => ({
        file: uniqueFiles[index].file,
        sourcePath: uniqueFiles[index].sourcePath,
        fileName: item.file_name,
        mimeType: item.mime_type,
        fileSize: item.file_size,
        resolvedDocType: item.resolved_doc_type,
        classificationSource: item.classification_source,
        confidence: item.confidence,
        status: item.status,
        message: item.message,
        contentHash: item.content_hash,
        duplicates: item.duplicates || [],
        action: item.status === "duplicate" ? "skip" : item.status === "ready" ? "upload" : "skip",
      }));
      const needsReview = prepared.some((item) => item.status !== "ready");
      setPreparedUploads(prepared);
      if (needsReview) {
        setShowUploadReview(true);
        updateProcessingIndicator(1, "Review complete", "Please confirm duplicates or unresolved files before upload");
        clearProcessingIndicator(1400);
        return;
      }
      await executeUploadBatch(prepared, { preserveLoading: true });
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Could not prepare uploads");
      setShowUploadPanel(true);
      clearProcessingIndicator();
    } finally {
      setUploading(false);
    }
  }

  async function handleNativeInputSelection(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []).map((file) => ({
      file,
      sourcePath: normalizeSelectedSourcePath(file),
    }));
    await prepareUploadBatch(files);
    event.target.value = "";
  }

  async function handleDropOnUploadPanel(event: ReactDragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (uploading) {
      return;
    }
    const files = await collectDroppedFiles(event.dataTransfer);
    await prepareUploadBatch(files);
  }

  const hasActiveChatPrompt = guardianMessages.some(
    (message) => message.role === "assistant" && Boolean(message.chips?.length),
  );

  // Generate proactive questions based on what we know and what's missing.
  useEffect(() => {
    if (!timeline?.key_facts) return;
    if (hasActiveChatPrompt) return;

    const pendingIntegrityPrompt = timeline.assistant_prompts.find(
      (prompt) =>
        !resolvedAssistantPromptIds.has(prompt.id)
        && !chatMessages.some(
          (message) => message.mode !== "form-filler" && message.id === `assistant-prompt:${prompt.id}`,
        ),
    );
    if (pendingIntegrityPrompt) {
      setChatMessages((prev) => [...prev, makeAssistantPromptMessage(pendingIntegrityPrompt)]);
      return;
    }

    const facts = new Set((timeline.key_facts as { label: string }[]).map((f) => f.label));
    const questions: { id: string; text: string; chips: string[] }[] = [];

    // Cross-track: if they did entity check but we don't know immigration status
    if (facts.has("Entity type") && !facts.has("Immigration stage")) {
      questions.push({
        id: "immigration_stage",
        text: "Since you have a US business entity, are you also on an immigration visa? This helps us check for cross-domain risks like Schedule C restrictions.",
        chips: ["Yes, I'm on a visa", "US citizen / PR", "Outside the US"],
      });
    }

    // If they did immigration check but we don't know about entity
    if (facts.has("Immigration stage") && !facts.has("Entity type")) {
      questions.push({
        id: "has_entity",
        text: "Do you own or have ownership in any US business entity (LLC, C-Corp, etc.)? Foreign-owned entities have specific filing requirements.",
        chips: ["Yes", "No", "Not sure"],
      });
    }

    // Missing employment details
    if (!facts.has("Employer") && !facts.has("Job title")) {
      questions.push({
        id: "employer_info",
        text: "Who is your current employer? This helps us verify your employment authorization and check for any document mismatches.",
        chips: ["I'll upload my employment letter", "Not currently employed"],
      });
    }

    // Tax residency unclear
    if (facts.has("Years in US") && !facts.has("Tax form filed")) {
      questions.push({
        id: "tax_filing",
        text: "Have you filed a US tax return for the most recent tax year? Knowing which form you filed helps us check for common errors.",
        chips: ["Yes, 1040", "Yes, 1040-NR", "Haven't filed yet", "Not sure"],
      });
    }

    // Tax software used
    if (!chatAnswered.has("tax_software") && !facts.has("Tax form filed")) {
      questions.push({
        id: "tax_software",
        text: "What did you use to file your most recent US tax return? Some software can\u2019t file the correct form for non-US persons, which can lead to serious issues.",
        chips: ["TurboTax", "H&R Block", "Sprintax", "A CPA did it", "Haven\u2019t filed"],
      });
    }

    // Foreign accounts
    if (!chatAnswered.has("foreign_accounts")) {
      questions.push({
        id: "foreign_accounts",
        text: "Do you have any bank accounts, investments, or insurance policies outside the US? This determines your FBAR and FATCA obligations.",
        chips: ["Yes", "No"],
      });
    }

    // Foreign gifts
    if (!chatAnswered.has("foreign_gifts")) {
      questions.push({
        id: "foreign_gifts",
        text: "Have you received money from family or anyone abroad totaling over $100,000 in a single year? This includes transfers for tuition, living expenses, or investments.",
        chips: ["Yes", "No", "Not sure"],
      });
    }

    // Open-ended employment chains — ask if still employed
    const openChains = (timeline.deadlines || []).filter(
      (d: { title: string; days: number }) =>
        d.title === "I-983 12-month evaluation due" && d.days < -30,
    );
    if (openChains.length > 0 && !chatAnswered.has("employment_status_check")) {
      questions.push({
        id: "employment_status_check",
        text: "We noticed some of your employment records don't have an end date, which is generating overdue evaluation alerts. Are you still employed at all of your listed employers, or have any of those positions ended?",
        chips: ["Still employed at all", "Some have ended", "I'll update my records"],
      });
    }

    // Form 8843
    if (!chatAnswered.has("form_8843") && facts.has("Immigration stage")) {
      questions.push({
        id: "form_8843",
        text: "Have you filed Form 8843 with your tax returns? This form is required every year for all F-1 and J-1 visa holders, even with zero income.",
        chips: ["Yes", "No", "What is that?"],
      });
    }

    // Government health plan
    if (!chatAnswered.has("govt_health_plan") && facts.has("Immigration stage")) {
      questions.push({
        id: "govt_health_plan",
        text: "Are you enrolled in a free or government-subsidized health plan? This includes Essential Plan (NY), Medi-Cal, Medicaid, or marketplace plans with $0 premium.",
        chips: ["Yes, free/subsidized plan", "Yes, but I pay full price", "No", "Not sure"],
      });
    }

    // Multi-state health enrollment
    if (!chatAnswered.has("multistate_health") && chatAnswered.has("govt_health_plan")) {
      questions.push({
        id: "multistate_health",
        text: "Have you been enrolled in health plans in more than one state? For example, a NY plan while also applying in California.",
        chips: ["Yes", "No"],
      });
    }

    // Filter out already answered
    const unanswered = questions.filter((q) => !chatAnswered.has(q.id));
    if (unanswered.length > 0) {
      const nextQuestion = unanswered[0];
      const nextMessageId = `assistant-question:${nextQuestion.id}`;
      if (!chatMessages.some(
        (message) => message.mode !== "form-filler" && message.id === nextMessageId,
      )) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: nextMessageId,
            role: "assistant",
            text: nextQuestion.text,
            mode: "guardian",
            chips: makeQuestionChips(nextQuestion.id, nextQuestion.chips),
          },
        ]);
      }
    }
  }, [
    timeline,
    chatAnswered,
    chatMessages,
    hasActiveChatPrompt,
    makeAssistantPromptMessage,
    makeQuestionChips,
    resolvedAssistantPromptIds,
  ]);

  useEffect(() => {
    if (!timeline?.assistant_prompts?.length) {
      return;
    }
    const interval = window.setInterval(() => {
      setChatMessages((prev) => {
        if (prev.some((message) => message.role === "assistant" && Boolean(message.chips?.length))) {
          return prev;
        }
        const nextPrompt = timeline.assistant_prompts.find(
          (prompt) =>
            !resolvedAssistantPromptIds.has(prompt.id)
            && !prev.some((message) => message.id === `assistant-prompt:${prompt.id}`),
        );
        if (!nextPrompt) {
          return prev;
        }
        return [...prev, makeAssistantPromptMessage(nextPrompt)];
      });
    }, 30000);
    return () => window.clearInterval(interval);
  }, [timeline?.assistant_prompts, resolvedAssistantPromptIds, makeAssistantPromptMessage]);

  const sendChatMessage = useCallback(async (text: string) => {
    const userMessage: ChatMessage = {
      id: nextChatMessageId(),
      role: "user",
      text,
      mode: "guardian",
    };
    const history = [...guardianMessagesRef.current, userMessage];
    guardianMessagesRef.current = history;
    setChatMessages((prev) => [...prev, userMessage]);
    setChatLoading(true);

    try {
      const resp = await fetch(chatApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ message: text, history: history.slice(0, -1).map((m) => ({ role: m.role, text: m.text })) }),
      });
      const data = await resp.json();
      const replyText = data.reply || "I was not able to summarize that just now.";
      const assistantMessage: ChatMessage = {
        id: nextChatMessageId(),
        role: "assistant",
        text: replyText,
        references: data.references || [],
        mode: "guardian",
      };
      guardianMessagesRef.current = [...history, assistantMessage];
      setChatMessages((prev) => [
        ...prev,
        assistantMessage,
      ]);
    } catch {
      const fallbackText = "Sorry, I couldn't process that. Please try again.";
      const assistantMessage: ChatMessage = {
        id: nextChatMessageId(),
        role: "assistant",
        text: fallbackText,
        mode: "guardian",
      };
      guardianMessagesRef.current = [...history, assistantMessage];
      setChatMessages((prev) => [
        ...prev,
        assistantMessage,
      ]);
    } finally {
      setChatLoading(false);
      setTimeout(() => {
        document.getElementById("chat-scroll")?.scrollTo({ top: 99999, behavior: "smooth" });
      }, 100);
    }
  }, [chatApi, nextChatMessageId]);

  const stopVoiceConversation = useCallback(async () => {
    const activeVapi = vapiRef.current;
    if (!activeVapi) {
      return;
    }

    try {
      await activeVapi.stop();
    } catch {
      // Ignore local transport shutdown failures.
    }

    activeVapi.removeAllListeners();
    vapiRef.current = null;
    voiceCallStartedRef.current = false;
    setVoiceCallState("idle");
    setVoiceError(null);
    setAssistantSpeaking(false);
    setMicMuted(false);
  }, []);

  const startVoiceConversation = useCallback(async () => {
    if (!voiceReady || vapiRef.current || voiceBusy) {
      if (!voiceReady) {
        setVoiceError("Add NEXT_PUBLIC_VAPI_PUBLIC_KEY in frontend/.env.local to enable the same live voice stack as Decid.");
      }
      return;
    }

    const nextVapi = new Vapi(VAPI_PUBLIC_KEY as string);
    const contextMessage = buildVoiceContextMessage(timeline, stats, documents);

    vapiRef.current = nextVapi;
    voiceCallStartedRef.current = false;
    setVoiceCallState("connecting");
    setVoiceError(null);
    setAssistantTranscript("");
    setUserTranscript("");

    nextVapi.on("call-start", () => {
      voiceCallStartedRef.current = true;
      setVoiceCallState("active");
      setVoiceError(null);
      nextVapi.send({
        type: "add-message",
        message: {
          role: "system",
          content: contextMessage,
        },
        triggerResponseEnabled: true,
      });
    });

    nextVapi.on("call-end", () => {
      nextVapi.removeAllListeners();
      if (vapiRef.current === nextVapi) {
        vapiRef.current = null;
      }
      voiceCallStartedRef.current = false;
      setVoiceCallState("ended");
      setVoiceError(null);
      setAssistantSpeaking(false);
      setMicMuted(false);
    });

    nextVapi.on("speech-start", () => {
      setAssistantSpeaking(true);
    });

    nextVapi.on("speech-end", () => {
      setAssistantSpeaking(false);
    });

    nextVapi.on("message", (message) => {
      if (isStatusUpdateMessage(message) && message.status === "ended") {
        setVoiceCallState("ended");
        setVoiceError(null);
        setAssistantSpeaking(false);
        setMicMuted(false);
        return;
      }

      if (!isTranscriptMessage(message)) {
        return;
      }

      const transcript = stripMarkdownForTranscript(message.transcript.trim());
      if (!transcript) {
        return;
      }

      if (message.role === "assistant") {
        setAssistantTranscript(transcript);
        return;
      }

      if (message.role === "user") {
        setUserTranscript(transcript);
      }
    });

    nextVapi.on("error", (error) => {
      nextVapi.removeAllListeners();
      if (vapiRef.current === nextVapi) {
        vapiRef.current = null;
      }
      const message = getVoiceErrorMessage(error);
      const shouldTreatAsEnded = voiceCallStartedRef.current && isVoiceConversationEndedMessage(message);
      voiceCallStartedRef.current = false;
      setVoiceCallState(shouldTreatAsEnded ? "ended" : "error");
      setAssistantSpeaking(false);
      setMicMuted(false);
      setVoiceError(shouldTreatAsEnded ? null : message);
    });

    try {
      await nextVapi.start(createGuardianVoiceAssistant());
    } catch (error) {
      nextVapi.removeAllListeners();
      if (vapiRef.current === nextVapi) {
        vapiRef.current = null;
      }
      voiceCallStartedRef.current = false;
      setVoiceCallState("error");
      setAssistantSpeaking(false);
      setMicMuted(false);
      setVoiceError(getVoiceErrorMessage(error));
    }
  }, [documents, stats, timeline, voiceBusy, voiceReady]);

  useEffect(() => () => {
    if (processingHideTimeoutRef.current) {
      window.clearTimeout(processingHideTimeoutRef.current);
    }
    if (vapiRef.current) {
      void vapiRef.current.stop();
      vapiRef.current.removeAllListeners();
      vapiRef.current = null;
      voiceCallStartedRef.current = false;
    }
  }, []);

  async function handleFormFillSubmit(file: File, instruction: string) {
    setFormFillLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (instruction) formData.append("instruction", instruction);

      const resp = await fetch(
        `${FORM_FILL_API}/extract`,
        { method: "POST", body: formData, headers: authHeaders() }
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Failed to process form" }));
        throw new Error(err.detail || "Failed to process form");
      }
      const data = await resp.json();
      setFormFillPreview({
        fields: data.fields,
        formFieldCount: data.form_field_count,
        filledCount: data.filled_count,
        unfilledCount: data.unfilled_count,
        originalFile: file,
      });
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: err instanceof Error ? err.message : "Failed to process the form. Please try again.",
          mode: "form-filler",
        },
      ]);
    } finally {
      setFormFillLoading(false);
    }
  }

  async function handleFormFillGenerate(values: Record<string, string>) {
    if (!formFillPreview) return;
    setFormFillLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", formFillPreview.originalFile);
      formData.append("values", JSON.stringify(values));

      const resp = await fetch(
        `${FORM_FILL_API}/generate`,
        { method: "POST", body: formData, headers: authHeaders() }
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Failed to generate PDF" }));
        throw new Error(err.detail || "Failed to generate PDF");
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `filled_${formFillPreview.originalFile.name}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setFormFillPreview(null);
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: `Your filled form "${formFillPreview.originalFile.name}" has been downloaded.`,
          mode: "form-filler",
        },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: nextChatMessageId(),
          role: "assistant",
          text: err instanceof Error ? err.message : "Failed to generate the filled PDF. Please try again.",
          mode: "form-filler",
        },
      ]);
    } finally {
      setFormFillLoading(false);
    }
  }

  async function handleChatChip(chip: AssistantPromptChoice) {
    const activePromptId = chip.prompt_id;
    setChatMessages((prev) => prev.map((msg) => (
      ((activePromptId && msg.id === `assistant-prompt:${activePromptId}`)
        || (chip.question_id && msg.id === `assistant-question:${chip.question_id}`))
        ? { ...msg, chips: undefined }
        : msg
    )));

    if (chip.action_type === "chat_answer" && chip.question_id) {
      setChatAnswered((prev) => {
        const next = new Set(prev);
        next.add(chip.question_id as string);
        return next;
      });
      try {
        await fetch(`${chatApi}/answer`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ question_id: chip.question_id, answer: chip.value }),
        });
        await refreshDashboard();
      } catch {
        // Non-fatal. Keep the chat flow moving.
      }
      await sendChatMessage(chip.value);
      return;
    }

    if (chip.action_type === "integrity_resolution" && chip.prompt_id && chip.document_id && chip.action) {
      setResolvedAssistantPromptIds((prev) => {
        const next = new Set(prev);
        next.add(chip.prompt_id as string);
        return next;
      });

      setChatMessages((prev) => [
        ...prev,
        { id: nextChatMessageId(), role: "user", text: chip.label, mode: "guardian" },
      ]);
      setChatLoading(true);
      try {
        const resp = await fetch(dashboardPromptApi, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            prompt_id: chip.prompt_id,
            document_id: chip.document_id,
            action: chip.action,
            chain_key: chip.chain_key ?? null,
          }),
        });
        if (!resp.ok) {
          throw new Error("Could not apply mapping resolution");
        }
        await refreshDashboard();
        setChatMessages((prev) => [
          ...prev,
          {
            id: nextChatMessageId(),
            role: "assistant",
            text: "I applied that document-mapping choice and refreshed your timeline.",
            mode: "guardian",
          },
        ]);
      } catch {
        setChatMessages((prev) => [
          ...prev,
          {
            id: nextChatMessageId(),
            role: "assistant",
            text: "I couldn't apply that mapping change. Please try again.",
            mode: "guardian",
          },
        ]);
      } finally {
        setChatLoading(false);
        setTimeout(() => {
          document.getElementById("chat-scroll")?.scrollTo({ top: 99999, behavior: "smooth" });
        }, 100);
      }
    }
  }

  const user = getUser();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#5b8dee] border-t-transparent animate-spin" />
      </div>
    );
  }

  const DOT_STYLE: Record<string, string> = {
    milestone: "bg-gradient-to-br from-emerald-400 to-emerald-500",
    now: "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] shadow-[0_0_10px_rgba(91,141,238,0.3)]",
    deadline: "bg-gray-300",
    filing: "bg-gradient-to-br from-emerald-400 to-emerald-500",
  };

  const serviceSummary = timeline?.service_summary;
  const activeServiceOrders = serviceSummary?.active_orders ?? [];
  const recommendedServices = serviceSummary?.recommended_services ?? [];
  const recentCompletedServices = serviceSummary?.recent_completed ?? [];
  const hasActiveServiceOrders = activeServiceOrders.length > 0;
  const hasServiceRecommendations = recommendedServices.length > 0;
  const hasRecentDeliverables = recentCompletedServices.length > 0;
  const hasServiceCenterContent = hasActiveServiceOrders || hasServiceRecommendations || hasRecentDeliverables;
  const activeServicePreview = activeServiceOrders.slice(0, 2);
  const recommendedServicePreview = recommendedServices.slice(0, 2);
  const recentCompletedPreview = recentCompletedServices.slice(0, 1);

  const renderServiceCenter = ({ mobile = false }: { mobile?: boolean } = {}) => (
    <section
      id={mobile ? undefined : "service-center"}
      className={`overflow-hidden rounded-[24px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.82),rgba(240,246,255,0.94))] backdrop-blur-xl shadow-[0_10px_30px_rgba(91,141,238,0.08)] ${
        mobile ? "mb-6 md:hidden" : "mt-2"
      }`}
    >
      <div className={`${mobile ? "p-5" : "p-4"}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5]">Service Center</div>
            <div className={`mt-2 font-bold leading-tight text-[#0d1424] ${mobile ? "text-[18px]" : "text-[16px]"}`}>
              Service work stays in view
            </div>
            <p className={`mt-2 text-[#556480] ${mobile ? "text-[13px] leading-6" : "text-[12px] leading-5"}`}>
              Active filings, draft workspaces, and the next service to start live alongside your dashboard summary.
            </p>
          </div>
          <div className="rounded-full bg-white/85 px-2.5 py-1 text-[10px] font-semibold text-[#5b8dee]">
            {hasActiveServiceOrders ? `${activeServiceOrders.length} active` : hasServiceRecommendations ? `${recommendedServices.length} next` : "Ready"}
          </div>
        </div>

        {hasActiveServiceOrders ? (
          <div className="mt-4 space-y-3">
            {activeServicePreview.map((order) => {
              const urgent = order.attention_state === "urgent";
              return (
                <button
                  key={order.order_id}
                  type="button"
                  onClick={() => router.push(order.href)}
                  className="w-full rounded-[18px] border border-[#dbe5f2] bg-white/86 px-4 py-3 text-left shadow-[0_8px_18px_rgba(61,84,128,0.05)] transition hover:bg-white"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
                        {(order.product.category || "service").replace(/_/g, " ")}
                      </div>
                      <div className="mt-1 text-[13px] font-semibold leading-5 text-[#0d1424]">{order.product_name}</div>
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold ${urgent ? "border-[#f1dfb3] bg-[#fff7ea] text-[#8d6216]" : "border-[#dbe5f2] bg-[#f8fbff] text-[#3a5a8c]"}`}>
                      {order.status_label}
                    </span>
                  </div>
                  <div className="mt-2 text-[12px] leading-5 text-[#556480]">{order.next_action}</div>
                  {order.filing_deadline ? (
                    <div className="mt-2 text-[11px] text-[#6b7d96]">
                      Deadline {order.filing_deadline}
                      {order.deadline_days != null
                        ? ` · ${order.deadline_days >= 0 ? `${order.deadline_days}d left` : `${Math.abs(order.deadline_days)}d overdue`}`
                        : ""}
                    </div>
                  ) : null}
                </button>
              );
            })}
            {activeServiceOrders.length > activeServicePreview.length ? (
              <div className="text-[11px] text-[#7b8ba5]">
                +{activeServiceOrders.length - activeServicePreview.length} more active service{activeServiceOrders.length - activeServicePreview.length === 1 ? "" : "s"} in your orders list.
              </div>
            ) : null}
          </div>
        ) : null}

        {!hasActiveServiceOrders && hasServiceRecommendations ? (
          <div className="mt-4 space-y-3">
            {recommendedServicePreview.map((service) => (
              <button
                key={service.sku}
                type="button"
                onClick={() => router.push(service.href)}
                className="w-full rounded-[18px] border border-[#dbe5f2] bg-white/86 px-4 py-3 text-left transition hover:bg-white"
              >
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
                  {(service.product.category || "service").replace(/_/g, " ")}
                </div>
                <div className="mt-1 text-[13px] font-semibold leading-5 text-[#0d1424]">{service.name}</div>
                <div className="mt-2 text-[12px] leading-5 text-[#556480]">{service.reason}</div>
              </button>
            ))}
          </div>
        ) : null}

        {!hasActiveServiceOrders && !hasServiceRecommendations && hasRecentDeliverables ? (
          <div className="mt-4 space-y-3">
            {recentCompletedPreview.map((order) => (
              <button
                key={order.order_id}
                type="button"
                onClick={() => router.push(order.href)}
                className="w-full rounded-[18px] border border-[#dbe5f2] bg-white/86 px-4 py-3 text-left transition hover:bg-white"
              >
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">
                  {(order.product.category || "service").replace(/_/g, " ")}
                </div>
                <div className="mt-1 text-[13px] font-semibold leading-5 text-[#0d1424]">{order.product_name}</div>
                <div className="mt-2 text-[12px] leading-5 text-[#556480]">{order.summary || "Result ready."}</div>
              </button>
            ))}
          </div>
        ) : null}

        {!hasServiceCenterContent ? (
          <div className="mt-4 rounded-[18px] border border-dashed border-[#dbe5f2] bg-white/72 px-4 py-3 text-[12px] leading-5 text-[#556480]">
            Start a filing or review from the service catalog, and it will stay visible here across dashboard views.
          </div>
        ) : null}

        <div className={`mt-4 grid gap-2 ${mobile ? "sm:grid-cols-2" : ""}`}>
          <button
            type="button"
            onClick={() => router.push("/account/orders")}
            className="inline-flex items-center justify-center rounded-full border border-blue-100/50 bg-white/85 px-4 py-2 text-[12px] font-semibold text-[#3a5a8c] transition hover:bg-white"
          >
            Open orders
          </button>
          <button
            type="button"
            onClick={() => router.push("/services")}
            className="inline-flex items-center justify-center rounded-full bg-[#5b8dee] px-4 py-2 text-[12px] font-semibold text-white shadow-[0_10px_20px_rgba(91,141,238,0.18)] transition hover:bg-[#4f82de]"
          >
            Browse services
          </button>
        </div>
      </div>
    </section>
  );

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-4 md:px-8 py-3 flex items-center justify-between bg-[#dce4f0]/60 dark:bg-[#0d1118]/80 backdrop-blur-2xl border-b border-blue-200/20 dark:border-white/5 transition-colors">
        <div className="text-lg font-extrabold text-[#0d1424] dark:text-white flex items-center gap-2.5">
          <div className="flex flex-col gap-[3px]" style={{transform:'perspective(200px) rotateX(-8deg) rotateY(12deg)'}}>
            <div className="h-[5px] w-6 rounded-sm" style={{background:'linear-gradient(135deg, #5b8dee, #4a74d4)',transform:'translateX(2px)'}} />
            <div className="h-[5px] w-6 rounded-sm" style={{background:'linear-gradient(135deg, #5b8dee, #4a74d4)',transform:'translateX(-1px)'}} />
            <div className="h-[5px] w-6 rounded-sm" style={{background:'linear-gradient(135deg, #5b8dee, #4a74d4)',transform:'translateX(3px)'}} />
          </div>
          Guardian
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <ThemeToggle />
          <span className="text-sm text-[#556480] dark:text-[#8e9ab5] hidden md:inline">{user?.email}</span>
          <div className="relative">
            <button
              onClick={() => {
                setShowToken((current) => !current);
                setTokenCopied(false);
                setOpenClawError(null);
              }}
              className="px-3 py-2 rounded-lg text-xs md:text-sm font-medium text-[#556480] dark:text-[#8e9ab5] hover:bg-white/60 dark:hover:bg-white/5 transition-all border border-transparent hover:border-blue-100/30 dark:hover:border-white/10"
            >
              Connect to OpenClaw
            </button>
            {showToken && (
              <>
                {/* Backdrop on mobile */}
                <div className="fixed inset-0 bg-black/20 z-40 md:hidden" onClick={() => setShowToken(false)} />
                {/* Popover: centered fixed on mobile, absolute dropdown on desktop */}
                <div className="fixed inset-x-4 top-20 z-50 md:absolute md:inset-auto md:right-0 md:top-full md:mt-2 md:w-80 bg-white/95 backdrop-blur-xl rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.12)] border border-blue-100/30 p-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs font-semibold text-[#0d1424]">Connect Guardian to OpenClaw</div>
                    <button onClick={() => setShowToken(false)} className="text-[#8e9ab5] text-sm md:hidden">&times;</button>
                  </div>
                  <div className="text-[11px] text-[#7b8ba5] mb-3">
                    OpenClaw uses a scoped Guardian token, not your web session. Generate or rotate that token here.
                  </div>
                  {openClawLoading && (
                    <div className="text-[11px] text-[#7b8ba5] py-2">Loading connection status...</div>
                  )}
                  {openClawError && (
                    <div className="text-[11px] text-[#dc2626] mb-3">{openClawError}</div>
                  )}
                  {openClawConnection && (
                    <div className="space-y-3">
                      <div className="rounded-lg border border-blue-100/40 bg-[#f7f9fd] px-3 py-2">
                        <div className="text-[10px] uppercase tracking-[0.14em] text-[#8b97ad] mb-1">Connection</div>
                        <div className="text-[11px] text-[#556480] break-all">
                          API: <code className="bg-white/80 px-1 rounded text-[#3a5a8c]">{openClawConnection.api_url}</code>
                        </div>
                        <div className="text-[11px] text-[#556480] mt-1">
                          Scope: <code className="bg-white/80 px-1 rounded text-[#3a5a8c]">{openClawConnection.scope}</code>
                        </div>
                        {openClawConnection.active_token && (
                          <div className="text-[11px] text-[#556480] mt-1">
                            Active token prefix: <code className="bg-white/80 px-1 rounded text-[#3a5a8c]">{openClawConnection.active_token.token_prefix}</code>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            issueOpenClawToken().catch((error) => {
                              console.error(error);
                            });
                          }}
                          className="px-3 py-2 rounded-lg text-[11px] font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white"
                        >
                          {openClawConnection.active_token ? "Rotate token" : "Generate token"}
                        </button>
                        {openClawToken && (
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(openClawToken);
                              setTokenCopied(true);
                              setTimeout(() => setTokenCopied(false), 2000);
                            }}
                            className="px-3 py-2 rounded-lg text-[11px] font-semibold border border-blue-100/50 text-[#3a5a8c] bg-white/70"
                          >
                            {tokenCopied ? "Copied" : "Copy token"}
                          </button>
                        )}
                      </div>
                      {openClawToken && (
                        <div className="relative">
                          <code className="block text-[10px] bg-[#f0f3f8] rounded-lg p-3 text-[#3a5a8c] break-all max-h-24 overflow-auto font-mono">{openClawToken}</code>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="text-[10px] text-[#7b8ba5] mt-3">
                    In OpenClaw: <code className="bg-[#f0f3f8] px-1 rounded text-[#3a5a8c]">{openClawConnection?.install_command || "openclaw skills install guardian-compliance"}</code> then set the generated value as <code className="bg-[#f0f3f8] px-1 rounded text-[#3a5a8c]">{openClawConnection?.env_var || "GUARDIAN_TOKEN"}</code>.
                  </div>
                </div>
              </>
            )}
          </div>
          {processingIndicator && (
            <div className="hidden md:flex items-center gap-3 rounded-full border border-white/60 bg-white/70 px-3 py-2 shadow-[0_6px_18px_rgba(91,141,238,0.08)]">
              <ProgressRing progress={processingIndicator.progress} size={32} label={processingIndicator.title} />
              <div className="min-w-0">
                <div className="text-[11px] font-semibold text-[#0d1424]">{processingIndicator.title}</div>
                <div className="max-w-[180px] truncate text-[10px] text-[#7b8ba5]">{processingIndicator.detail}</div>
              </div>
            </div>
          )}
          <button onClick={() => setShowUploadPanel(true)} className="inline-flex items-center gap-2 px-3 md:px-4 py-2 rounded-lg bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] dark:from-[#3a5a9c] dark:to-[#2d4578] text-white text-xs md:text-sm font-semibold">
            {processingIndicator && (
              <span className="inline-flex h-2.5 w-2.5 rounded-full border border-white/70 border-t-transparent animate-spin" />
            )}
            + Upload document
          </button>
          <button onClick={() => { logout(); router.push("/"); }} className="text-xs md:text-sm text-[#7b8ba5] dark:text-[#8e9ab5]">
            Sign out
          </button>
        </div>
      </nav>

      <div className="flex flex-col md:flex-row pt-14">
        {/* Sidebar — hidden on mobile, shown on md+ */}
        <div className="hidden md:flex md:flex-col w-64 flex-shrink-0 p-5 bg-white/30 backdrop-blur-xl border-r border-white/50 min-h-screen">
          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Views</div>
            <button onClick={() => setView("timeline")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "timeline" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>Timeline</button>
            <button onClick={() => setView("documents")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "documents" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>
              All Documents
              <span className="ml-2 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-[#5b8dee]/8 text-[#5b8dee]">{documents.length}</span>
            </button>
            <button onClick={() => setView("deadlines")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "deadlines" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>
              Deadlines
              {timeline?.deadlines && <span className="ml-2 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-50 text-amber-600">{timeline.deadlines.filter((d: {days: number}) => d.days <= 30).length || ""}</span>}
            </button>
            <button onClick={() => setView("profile")} className={`w-full text-left text-sm px-3 py-2 rounded-lg mb-1 transition-all ${view === "profile" ? "font-semibold text-[#3d6bc5] bg-[#5b8dee]/8" : "text-[#556480] hover:bg-white/40"}`}>Key Facts</button>
          </div>

          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Categories</div>
            {["student_status", "immigration", "employment", "tax", "business", "personal", "other"].map((cat) => {
              const count = documents.filter((d) => (d.category || "other") === cat).length;
              if (count === 0) return null;
              const colors = categoryPalette[cat] || categoryPalette.other;
              return (
                <div key={cat} className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480]">
                  <span className="w-2 h-2 rounded-full" style={{ background: colors.text }} />
                  {colors.label}
                  <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md" style={{ background: colors.bg, color: colors.text }}>{count}</span>
                </div>
              );
            })}
          </div>

          <div className="mb-7">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7b8ba5] mb-2.5">Risks</div>
            <div className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480]">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Needs attention
              <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md bg-red-50 text-red-500">{stats?.risks || 0}</span>
            </div>
            <div className="flex items-center gap-2.5 px-3 py-2 text-sm text-[#556480]">
              <span className="w-2 h-2 rounded-full bg-[#8e9ab5]" />
              Potential risks
              <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-50 text-[#5b8dee]">{timeline?.advisories.length || 0}</span>
            </div>
          </div>

          {renderServiceCenter()}
        </div>

        {/* Main */}
        <div className="flex-1 p-4 md:p-8 max-w-[900px]">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8">
            {[
              { num: stats?.documents || 0, label: "Documents", color: "#0d1424" },
              { num: stats?.risks || 0, label: "Needs attention", color: "#f59e0b" },
              { num: timeline?.advisories.length || 0, label: "Potential risks", color: "#5b8dee" },
              { num: stats?.next_deadline_days != null ? `${stats.next_deadline_days}d` : "—", label: "Next deadline", color: "#5b8dee" },
            ].map((s) => (
              <div key={s.label} className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 p-4 md:p-5 shadow-[0_2px_12px_rgba(91,141,238,0.04)]">
                <div className="text-3xl font-bold" style={{ color: s.color }}>{s.num}</div>
                <div className="text-[11px] text-[#7b8ba5] mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          <section className="mb-8 overflow-hidden rounded-[28px] border border-white/60 bg-[linear-gradient(135deg,rgba(255,255,255,0.78),rgba(234,241,251,0.92))] backdrop-blur-xl shadow-[0_10px_36px_rgba(91,141,238,0.08)]">
            <div className="p-5 md:p-7">
              <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                <div className="max-w-2xl">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7b8ba5]">Voice Conversation</div>
                  <h2 className="mt-2 text-[24px] font-bold leading-tight text-[#0d1424]">Talk to Guardian</h2>
                  <p className="mt-3 text-[14px] leading-7 text-[#556480]">
                    This uses the same live voice flow as Decid. Guardian speaks first, listens live, and keeps the latest transcript in this panel.
                  </p>
                </div>

                <div className="flex shrink-0 items-center">
                  <button
                    type="button"
                    onClick={() => {
                      if (voiceActive) {
                        void stopVoiceConversation();
                        return;
                      }
                      void startVoiceConversation();
                    }}
                    disabled={voiceBusy}
                    aria-label={voiceActive ? "Stop live voice" : "Start live voice"}
                    className={`inline-flex items-center gap-3 rounded-full px-5 py-3 text-[14px] font-semibold transition-all ${
                      voiceActive
                        ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] dark:from-[#3a5a9c] dark:to-[#2d4578] text-white shadow-[0_12px_28px_rgba(91,141,238,0.2)]"
                        : "border border-blue-100/50 dark:border-white/10 bg-white/85 dark:bg-white/5 text-[#3a5a8c] dark:text-[#8aa8e0] hover:bg-white dark:hover:bg-white/10"
                    } disabled:cursor-not-allowed disabled:opacity-50`}
                  >
                    <span className={`inline-flex h-10 w-10 items-center justify-center rounded-full ${
                      voiceActive ? "bg-white/18" : "bg-[#5b8dee]/8 dark:bg-[#5b8dee]/15"
                    }`}>
                      <span className={`block h-4 w-4 rounded-full ${
                        voiceActive ? "bg-white" : "bg-[#5b8dee] dark:bg-[#8aa8e0]"
                      }`} />
                    </span>
                    {!voiceReady
                      ? "Voice unavailable"
                      : voiceBusy
                        ? "Connecting..."
                        : voiceActive
                          ? "Stop voice"
                          : voiceEnded
                            ? "Start another review"
                            : "Start live voice"}
                  </button>
                </div>
              </div>

              <div className="mt-6 rounded-[24px] border border-white/70 bg-white/55 p-4 shadow-[0_6px_22px_rgba(91,141,238,0.06)]">
                <div className="flex items-center justify-between gap-3 border-b border-blue-100/35 pb-3">
                  <div>
                    <div className="text-[13px] font-semibold text-[#0d1424]">Transcript</div>
                    <div className="text-[12px] text-[#7b8ba5]">
                      {!voiceReady
                        ? "Waiting for the Vapi public key"
                        : voiceBusy
                          ? "Connecting the live voice assistant"
                        : voiceEnded
                          ? "Conversation ended"
                        : voiceListening
                          ? "Listening for your reply"
                          : assistantSpeaking
                            ? "Guardian is speaking"
                            : voiceActive
                              ? "Conversation paused"
                              : "No voice conversation yet"}
                    </div>
                  </div>
                  <div className="text-[11px] font-medium text-[#7b8ba5]">
                    {voiceActive || voiceEnded ? `Voice: ${GUARDIAN_VOICE_ID}` : "Assistant-led review"}
                  </div>
                </div>

                {voiceError && (
                  <div className="mt-4 rounded-2xl border border-red-200 bg-red-50/80 px-4 py-3 text-[12px] text-red-700">
                    {voiceError}
                  </div>
                )}

                {!voiceError && voiceEnded && (
                  <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-[12px] text-[#4f6fb4]">
                    Conversation ended. Start another review when you&apos;re ready.
                  </div>
                )}

                <div className="mt-4 space-y-3 rounded-[22px] border border-blue-100/40 bg-[#f8fbff] p-4">
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">Guardian</div>
                    {voiceBusy ? (
                      <div className="mt-2 flex gap-1.5">
                        <div className="h-2 w-2 rounded-full bg-[#5b8dee] animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="h-2 w-2 rounded-full bg-[#5b8dee] animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="h-2 w-2 rounded-full bg-[#5b8dee] animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    ) : (
                      <p className="mt-2 whitespace-pre-wrap text-[14px] leading-7 text-[#556480]">
                        {assistantTranscript || "Guardian will summarize the dashboard here once the live voice review starts."}
                      </p>
                    )}
                  </div>

                  <div className="border-t border-blue-100/35 pt-3">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b8ba5]">You</div>
                    <p className="mt-2 whitespace-pre-wrap text-[14px] leading-7 text-[#556480]">
                      {userTranscript || "Your latest spoken reply will appear here."}
                    </p>
                  </div>

                  {!voiceReady && (
                    <p className="border-t border-blue-100/35 pt-3 text-[12px] leading-6 text-[#7b8ba5]">
                      Add <code className="rounded bg-white/80 px-1 text-[#3a5a8c]">NEXT_PUBLIC_VAPI_PUBLIC_KEY</code> in <code className="rounded bg-white/80 px-1 text-[#3a5a8c]">frontend/.env.local</code> to use the same voice stack as Decid.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Mobile view toggle */}
          <div className="flex md:hidden gap-1.5 mb-4 overflow-x-auto">
            {(["timeline", "deadlines", "documents", "profile"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} className={`flex-shrink-0 px-3 py-2 rounded-xl text-xs font-medium transition-all ${view === v ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white" : "bg-white/50 text-[#556480]"}`}>
                {v === "documents" ? `Docs` : v === "profile" ? "Facts" : v === "deadlines" ? "Deadlines" : "Timeline"}
              </button>
            ))}
          </div>

          {renderServiceCenter({ mobile: true })}

          {/* Documents View */}
          {view === "documents" && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-[#0d1424]">All Documents</h2>
                <button onClick={() => setShowUploadPanel(true)} className="text-[13px] font-medium text-[#5b8dee]">+ Upload</button>
              </div>
              {(() => {
                const DOC_TO_CAT: Record<string, string> = {
                  i20: "Student Status", i94: "Student Status",
                  i797: "Immigration", i485: "Immigration", i765: "Immigration", i131: "Immigration",
                  i983: "Employment", employment_letter: "Employment", ead: "Employment",
                  tax_return: "Tax", w2: "Tax",
                };
                const grouped: Record<string, typeof documents> = {};
                for (const doc of documents) {
                  const cat = DOC_TO_CAT[doc.doc_type] || "Business";
                  if (!grouped[cat]) grouped[cat] = [];
                  grouped[cat].push(doc);
                }
                const DOC_LABELS: Record<string, string> = {
                  employment_letter: "Employment Letter", i983: "Form I-983", ead: "EAD Card", i20: "I-20",
                  i797: "I-797", i94: "I-94", i485: "I-485", i765: "I-765", i131: "I-131 (Advance Parole)", tax_return: "Tax Return", w2: "W-2", other: "Other",
                };
                return Object.entries(grouped).map(([category, docs]) => (
                  <div key={category} className="mb-6">
                    <div className="text-[11px] font-semibold text-[#7b8ba5] uppercase tracking-widest mb-2">{category}</div>
                    <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
                      {docs.map((doc, i) => (
                        <div key={doc.id} className={`flex items-center gap-3 px-5 py-3.5 ${i > 0 ? "border-t border-blue-50/40" : ""}`}>
                          <div className="w-8 h-8 rounded-lg bg-[#5b8dee]/6 flex items-center justify-center text-xs font-bold text-[#5b8dee]">
                            {(DOC_LABELS[doc.doc_type] || doc.doc_type).charAt(0)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[13px] font-semibold text-[#0d1424] truncate">{doc.filename}</div>
                            <div className="text-[11px] text-[#7b8ba5]">
                              {DOC_LABELS[doc.doc_type] || doc.doc_type} · {doc.file_size ? `${Math.round(doc.file_size / 1024)}KB` : ""} · {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ""}
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              openDashboardDocument(doc.id).catch((error) => {
                                console.error(error);
                              });
                            }}
                            className="text-[12px] font-medium text-[#5b8dee] hover:text-[#4a74d4] flex-shrink-0"
                          >
                            View
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ));
              })()}
              {documents.length === 0 && (
                <div className="text-center py-12">
                  <div className="text-[#8e9ab5] text-sm mb-3">No documents yet</div>
                  <button onClick={() => setShowUploadPanel(true)} className="text-[13px] font-medium text-[#5b8dee]">Upload your first document</button>
                </div>
              )}
            </div>
          )}

          {/* Deadlines View */}
          {view === "deadlines" && (
            <div>
              <h2 className="text-lg font-bold text-[#0d1424] mb-6">Upcoming Deadlines</h2>
              {timeline?.deadlines && timeline.deadlines.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {(timeline.deadlines as { title: string; date: string; days: number; category: string; severity: string; action: string }[]).map((d, i) => {
                    const isOverdue = d.days < 0;
                    const isUrgent = d.days >= 0 && d.days <= 30;
                    const severityColor = isOverdue
                      ? { bg: "rgba(239,68,68,0.08)", text: "#dc2626", border: "rgba(239,68,68,0.12)" }
                      : isUrgent
                      ? { bg: "rgba(245,158,11,0.08)", text: "#d97706", border: "rgba(245,158,11,0.12)" }
                      : { bg: "rgba(91,141,238,0.06)", text: "#5b8dee", border: "rgba(91,141,238,0.08)" };
                    const catColor: Record<string, string> = { immigration: "#3d6bc5", tax: "#059669", entity: "#7c3aed" };

                    return (
                      <div key={`${d.title}-${i}`} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 px-5 py-4 shadow-[0_2px_12px_rgba(91,141,238,0.04)]">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex-1">
                            <div className="text-[14px] font-semibold text-[#0d1424]">{d.title}</div>
                            <div className="text-[12px] text-[#556480] mt-1">{d.action}</div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="text-[20px] font-bold" style={{ color: severityColor.text }}>
                              {isOverdue ? `${Math.abs(d.days)}d overdue` : `${d.days}d`}
                            </div>
                            <div className="text-[11px] text-[#8e9ab5]">{d.date}</div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full capitalize" style={{ background: severityColor.bg, color: severityColor.text, border: `1px solid ${severityColor.border}` }}>
                            {isOverdue ? "Overdue" : isUrgent ? "Due soon" : "Upcoming"}
                          </span>
                          <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full capitalize" style={{ background: "rgba(91,141,238,0.06)", color: catColor[d.category] || "#556480", border: "1px solid rgba(91,141,238,0.08)" }}>
                            {d.category}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="text-[#8e9ab5] text-sm mb-3">No deadlines computed yet</div>
                  <div className="text-[12px] text-[#7b8ba5]">Upload documents to surface your upcoming deadlines</div>
                </div>
              )}
            </div>
          )}

          {/* Key Facts View */}
          {view === "profile" && (
            <div>
              <h2 className="text-lg font-bold text-[#0d1424] mb-6">Key Facts</h2>

              {(() => {
                const CAT_LABELS: Record<string, string> = {
                  student_status: "Student Status",
                  immigration: "Immigration",
                  employment: "Employment",
                  tax: "Tax",
                  entity: "Business",
                };
                const CAT_ORDER = ["student_status", "immigration", "employment", "tax", "entity"];
                const grouped: Record<string, { label: string; value: string }[]> = {};

                for (const fact of (timeline?.key_facts || []) as { label: string; value: string; category?: string }[]) {
                  const cat = fact.category || "immigration";
                  if (!grouped[cat]) grouped[cat] = [];
                  grouped[cat].push(fact);
                }

                return CAT_ORDER.map((cat) => {
                  const facts = grouped[cat];
                  if (!facts || facts.length === 0) return null;
                  return (
                    <div key={cat} className="mb-5">
                      <div className="text-[11px] font-semibold text-[#7b8ba5] uppercase tracking-widest mb-2">{CAT_LABELS[cat] || cat}</div>
                      <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
                        {facts.map((fact, i) => (
                          <div key={`${fact.label}-${i}`} className={`flex justify-between px-5 py-3.5 ${i > 0 ? "border-t border-blue-50/40" : ""}`}>
                            <span className="text-[13px] text-[#556480]">{fact.label}</span>
                            <span className="text-[13px] font-semibold text-[#0d1424] text-right max-w-[60%] truncate">{fact.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                });
              })()}

              {(!timeline?.key_facts || timeline.key_facts.length === 0) && (
                <div className="text-center py-12">
                  <div className="text-[#8e9ab5] text-sm mb-3">No facts extracted yet</div>
                  <div className="text-[12px] text-[#7b8ba5]">Run a check or upload documents to populate your key facts</div>
                </div>
              )}
            </div>
          )}

          {/* Timeline */}
          {view === "timeline" && (<><div className="relative pl-7">
            <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#5b8dee] to-[#5b8dee]/10" />

            {timeline?.events.map((event, i) => (
              <div key={i} className="relative mb-6">
                <div className={`absolute -left-[18px] top-1.5 w-3.5 h-3.5 rounded-full border-[3px] border-white ${DOT_STYLE[event.type] || "bg-gray-300"}`} />

                <div className={`text-[11px] font-semibold tracking-wide mb-1 ${event.type === "now" ? "text-[#5b8dee]" : "text-[#8e9ab5]"}`}>
                  {event.type === "now" ? "TODAY" : event.date.toUpperCase()}
                </div>
                <div className={`text-[15px] font-semibold mb-2 ${event.type === "now" ? "text-[#0d1424]" : "text-[#0d1424]"}`}>
                  {event.title}
                </div>

                {event.chain && event.chain.type === "employment" && (
                  <div className="flex items-center gap-2 mb-2.5">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8e9ab5]">
                      Employment chain
                    </span>
                    <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#5b8dee]/8 text-[#3d6bc5] border border-[#5b8dee]/12">
                      {event.chain.label}
                    </span>
                  </div>
                )}

                {/* Documents */}
                {event.documents.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {event.documents.map((doc) => renderDocumentChip(doc))}
                  </div>
                )}

                {/* Risks */}
                {event.risks && event.risks.length > 0 && event.risks.map((risk) => (
                  <div key={risk.id} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 px-5 py-4 mb-2 shadow-sm">
                    <div className="font-semibold text-[13px] text-[#0d1424] mb-1">{risk.title}</div>
                    <div className="text-[12px] text-[#556480] mb-2">{risk.action}</div>
                    {risk.documents && risk.documents.length > 0 && (
                      <div className="mb-2.5">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8e9ab5] mb-1.5">
                          Detected from
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {risk.documents.map((doc) => renderDocumentChip(doc, { compact: true }))}
                        </div>
                      </div>
                    )}
                    <div className="flex gap-2">
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(245,158,11,0.12)", color: "#b45309", border: "1px solid rgba(245,158,11,0.15)" }}>
                        {risk.consequence}
                      </span>
                      {risk.immigration_impact && (
                        <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(239,68,68,0.1)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.12)" }}>
                          Immigration impact
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}

            {/* Upload Prompts */}
            {timeline?.upload_prompts.map((prompt, i) => (
              <div key={i} className="relative mb-6">
                <div className="absolute -left-[18px] top-1.5 w-3.5 h-3.5 rounded-full border-[3px] border-white bg-amber-400" />
                <div
                  onClick={() => { setUploadDocType(prompt.doc_type); fileRef.current?.click(); }}
                  className="px-5 py-4 rounded-2xl border border-dashed border-[#5b8dee]/20 bg-[#5b8dee]/4 cursor-pointer hover:bg-[#5b8dee]/8 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#5b8dee]/8 flex items-center justify-center text-sm">📤</div>
                    <div>
                      <div className="text-[13px] font-semibold text-[#3d6bc5]">{prompt.prompt}</div>
                      <div className="text-[11px] text-[#7b8ba5] mt-0.5">{prompt.why}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Potential risks — with upload action buttons */}
          {timeline && timeline.advisories.length > 0 && (
            <div className="mt-8">
              <div className="text-xs font-semibold text-[#7b8ba5] uppercase tracking-widest mb-3">Worth looking into</div>
              <div className="bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 overflow-hidden">
                {timeline.advisories.map((a, i) => (
                  <div key={a.id} className={`px-5 py-4 ${i > 0 ? "border-t border-blue-50/40" : ""}`}>
                    <div className="flex items-start gap-3">
                      <div className="flex-1 text-[13px]">
                        <span className="font-semibold text-[#3d6bc5]">{a.title}</span>
                        <span className="text-[#556480]"> — {a.action}</span>
                      </div>
                      <span className="text-[11px] font-semibold px-3 py-1 rounded-full flex-shrink-0" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.1)" }}>
                        {a.consequence}
                      </span>
                    </div>
                    <button
                      onClick={() => { setUploadDocType(a.title.toLowerCase().replace(/[^a-z0-9]/g, "_")); setShowUploadPanel(true); }}
                      className="mt-2 text-[12px] font-medium text-[#5b8dee] hover:text-[#4a74d4] transition-colors"
                    >
                      Upload related document →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          </>)}

          {/* Hidden upload inputs */}
          <input
            ref={fileRef}
            type="file"
            accept={DASHBOARD_ACCEPT}
            multiple
            className="hidden"
            onChange={handleNativeInputSelection}
          />
          <input
            ref={folderRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleNativeInputSelection}
          />

          {/* Upload Panel Modal */}
          {showUploadPanel && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d1424]/20 backdrop-blur-sm p-4">
              <div className="w-full max-w-xl bg-white/80 backdrop-blur-xl rounded-2xl border border-white/60 p-6 shadow-[0_16px_64px_rgba(91,141,238,0.15)]">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-bold text-[#0d1424]">Upload documents</h2>
                    <div className="text-[12px] text-[#7b8ba5] mt-1">Drag files or a folder here, or browse and review duplicates before upload.</div>
                  </div>
                  <button onClick={() => { setShowUploadPanel(false); setUploadError(null); }} className="text-[#7b8ba5] hover:text-[#0d1424] text-xl">&times;</button>
                </div>

                {uploadError && (
                  <div className="mb-4 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-[12px] text-red-700">
                    {uploadError}
                  </div>
                )}

                <div
                  onClick={() => { if (!uploading) fileRef.current?.click(); }}
                  onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={handleDropOnUploadPanel}
                  className={`flex flex-col items-center px-6 py-10 rounded-xl border-2 border-dashed transition-all cursor-pointer mb-4 ${
                    uploading
                      ? "border-blue-300 bg-blue-50/30"
                      : dragActive
                      ? "border-blue-400 bg-blue-50/60"
                      : "border-blue-200/40 bg-white/50 hover:border-blue-300/60 hover:bg-white/70"
                  }`}
                >
                  {uploading ? (
                    <div className="text-sm text-[#5b8dee] font-medium">Preparing uploads...</div>
                  ) : (
                    <>
                      <div className="text-[15px] font-semibold text-[#0d1424] mb-1">Drop files or folders here</div>
                      <div className="text-xs text-[#8e9ab5]">PDF, JPG, PNG, CSV, TXT, DOCX. We hash every file and warn before keeping duplicates.</div>
                    </>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 mb-5">
                  <button
                    onClick={() => fileRef.current?.click()}
                    disabled={uploading}
                    className="px-3.5 py-2 rounded-xl text-[12px] font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white disabled:opacity-50"
                  >
                    Choose files
                  </button>
                  <button
                    onClick={() => folderRef.current?.click()}
                    disabled={uploading}
                    className="px-3.5 py-2 rounded-xl text-[12px] font-semibold bg-white/70 border border-blue-100/30 text-[#3a5a8c] disabled:opacity-50"
                  >
                    Choose folder
                  </button>
                </div>

                <div className="text-[11px] font-semibold text-[#7b8ba5] uppercase tracking-widest mb-2">Optional — apply one type to this batch</div>
                <div className="flex flex-wrap gap-1.5 mb-5">
                  {[
                    { type: "employment_letter", label: "Employment Letter" },
                    { type: "i983", label: "I-983" },
                    { type: "ead", label: "EAD Card" },
                    { type: "i20", label: "I-20" },
                    { type: "i797", label: "I-797" },
                    { type: "i485", label: "I-485" },
                    { type: "i765", label: "I-765" },
                    { type: "i131", label: "I-131 (Advance Parole)" },
                    { type: "tax_return", label: "Tax Return" },
                    { type: "w2", label: "W-2" },
                  ].map((doc) => (
                    <button
                      key={doc.type}
                      onClick={() => setUploadDocType(uploadDocType === doc.type ? "" : doc.type)}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${
                        uploadDocType === doc.type
                          ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white shadow-sm"
                          : "bg-white/60 border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90"
                      }`}
                    >
                      {doc.label}
                    </button>
                  ))}
                </div>

                <p className="text-[11px] text-[#8e9ab5] text-center">
                  Folder paths are preserved as source context. Exact duplicate files are detected by SHA-256 hash before upload.
                </p>
              </div>
            </div>
          )}

          {/* Upload Review Modal */}
          {showUploadReview && (
            <div className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0d1424]/25 backdrop-blur-sm p-4">
              <div className="w-full max-w-3xl bg-white/90 backdrop-blur-xl rounded-2xl border border-white/60 p-6 shadow-[0_16px_64px_rgba(91,141,238,0.18)] max-h-[85vh] flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-bold text-[#0d1424]">Review upload batch</h2>
                    <div className="text-[12px] text-[#7b8ba5] mt-1">Duplicates default to skip. Keep only the files you want to store.</div>
                  </div>
                  <button
                    onClick={() => { resetUploadState(); setUploading(false); }}
                    className="text-[#7b8ba5] hover:text-[#0d1424] text-xl"
                  >
                    &times;
                  </button>
                </div>

                {uploadError && (
                  <div className="mb-4 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-[12px] text-red-700">
                    {uploadError}
                  </div>
                )}

                <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                  {preparedUploads.map((item, index) => {
                    const canToggle = item.status === "ready" || item.status === "duplicate";
                    const actionLabel = item.action === "upload" ? (item.status === "duplicate" ? "Keep duplicate" : "Upload") : "Skip";
                    return (
                      <div key={`${item.fileName}-${index}`} className="rounded-2xl border border-white/60 bg-white/55 px-4 py-4">
                        <div className="flex items-start gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="text-[13px] font-semibold text-[#0d1424] truncate">{item.fileName}</div>
                            <div className="text-[11px] text-[#7b8ba5] mt-1">
                              {item.resolvedDocType || "Unknown type"} · {Math.max(1, Math.round(item.fileSize / 1024))}KB
                              {item.sourcePath ? ` · ${item.sourcePath}` : ""}
                            </div>
                            {item.message && (
                              <div className={`text-[12px] mt-2 ${item.status === "duplicate" ? "text-amber-700" : "text-red-700"}`}>
                                {item.message}
                              </div>
                            )}
                            {item.duplicates.length > 0 && (
                              <div className="mt-3 space-y-2">
                                {item.duplicates.map((duplicate) => (
                                  <div key={duplicate.id} className="rounded-xl border border-amber-200 bg-amber-50/70 px-3 py-2 text-[11px] text-amber-900">
                                    <div className="font-semibold">{duplicate.filename}</div>
                                    <div className="text-amber-800/80">
                                      {duplicate.doc_type}
                                      {duplicate.source_path ? ` · ${duplicate.source_path}` : ""}
                                      {duplicate.uploaded_at ? ` · ${new Date(duplicate.uploaded_at).toLocaleDateString()}` : ""}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-2 flex-shrink-0">
                            <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${
                              item.status === "ready"
                                ? "bg-emerald-50 text-emerald-700"
                                : item.status === "duplicate"
                                ? "bg-amber-50 text-amber-700"
                                : "bg-red-50 text-red-700"
                            }`}>
                              {item.status}
                            </span>
                            <button
                              disabled={!canToggle || uploading}
                              onClick={() => setPreparedUploads((current) => current.map((currentItem, currentIndex) => (
                                currentIndex === index
                                  ? { ...currentItem, action: currentItem.action === "upload" ? "skip" : "upload" }
                                  : currentItem
                              )))}
                              className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold ${
                                item.action === "upload"
                                  ? "bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white"
                                  : "bg-white/70 border border-blue-100/30 text-[#3a5a8c]"
                              } disabled:opacity-50`}
                            >
                              {actionLabel}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between gap-3 mt-5 pt-4 border-t border-blue-100/30">
                  <div className="text-[12px] text-[#556480]">
                    {preparedUploads.filter((item) => item.action === "upload").length} of {preparedUploads.length} selected for upload
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { resetUploadState(); setUploading(false); }}
                      className="px-3.5 py-2 rounded-xl text-[12px] font-semibold bg-white/70 border border-blue-100/30 text-[#3a5a8c]"
                    >
                      Cancel
                    </button>
                    <button
                      disabled={uploading || !preparedUploads.some((item) => item.action === "upload")}
                      onClick={() => {
                        setShowUploadReview(false);
                        setUploadError(null);
                        void executeUploadBatch(preparedUploads, { reopenReviewOnError: false });
                      }}
                      className="px-3.5 py-2 rounded-xl text-[12px] font-semibold bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white disabled:opacity-50"
                    >
                      {uploading ? "Uploading..." : "Upload selected"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right-side Chat Panel */}
      <div className={`fixed top-14 right-0 bottom-0 z-30 transition-all duration-300 ${chatOpen ? "w-80 md:w-96" : "w-0"}`}>
        {chatOpen && (
          <div className="h-full bg-white/40 dark:bg-[#1a1f2e]/80 backdrop-blur-xl border-l border-white/50 dark:border-white/5 flex flex-col transition-colors">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-blue-50/40 flex-shrink-0">
              <div>
                <div className="text-[14px] font-semibold text-[#0d1424]">
                  {chatMode === "guardian" ? "Guardian Assistant" : "Form Filler"}
                </div>
                <div className="text-[11px] text-[#7b8ba5]">
                  {chatMode === "guardian" ? "Ask anything about your compliance" : "Upload a fillable PDF to auto-complete"}
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="text-[#7b8ba5] hover:text-[#0d1424] text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/50 transition-all">&times;</button>
            </div>
            <ModeBar active={chatMode} onChange={setChatMode} />

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4" id="chat-scroll">
              {visibleChatMessages.length === 0 && (
                <div className="bg-white/50 backdrop-blur rounded-2xl p-4 border border-white/60">
                  {chatMode === "guardian" ? (
                    <>
                      <div className="text-[13px] text-[#0d1424] leading-relaxed mb-1">Hi! I&apos;m your Guardian assistant.</div>
                      <div className="text-[12px] text-[#556480] leading-relaxed">I can answer questions about your immigration, tax, or business compliance. I also have context about your uploaded documents and findings.</div>
                    </>
                  ) : (
                    <>
                      <div className="text-[13px] text-[#0d1424] leading-relaxed mb-1">Upload a fillable PDF to auto-complete it.</div>
                      <div className="text-[12px] text-[#556480] leading-relaxed">This mode only shows form-filling output. Guardian questions and compliance prompts stay in Guardian mode.</div>
                    </>
                  )}
                </div>
              )}
              {visibleChatMessages.map((msg) => (
                <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : ""}>
                  {msg.role === "assistant" ? (
                    <div className="bg-white/50 backdrop-blur rounded-2xl p-4 border border-white/60 chat-md">
                      <ReactMarkdown components={{
                        p: (props: ComponentPropsWithoutRef<"p">) => <p className="text-[13px] text-[#0d1424] leading-relaxed mb-2 last:mb-0" {...props} />,
                        strong: (props: ComponentPropsWithoutRef<"strong">) => <strong className="font-semibold text-[#0d1424]" {...props} />,
                        ul: (props: ComponentPropsWithoutRef<"ul">) => <ul className="text-[13px] text-[#0d1424] leading-relaxed mb-2 ml-4 space-y-1 list-disc" {...props} />,
                        ol: (props: ComponentPropsWithoutRef<"ol">) => <ol className="text-[13px] text-[#0d1424] leading-relaxed mb-2 ml-4 space-y-1 list-decimal" {...props} />,
                        li: (props: ComponentPropsWithoutRef<"li">) => <li className="text-[13px] text-[#0d1424]" {...props} />,
                        h1: (props: ComponentPropsWithoutRef<"h1">) => <div className="text-[14px] font-bold text-[#0d1424] mb-2" {...props} />,
                        h2: (props: ComponentPropsWithoutRef<"h2">) => <div className="text-[13px] font-bold text-[#0d1424] mb-1.5 mt-3" {...props} />,
                        h3: (props: ComponentPropsWithoutRef<"h3">) => <div className="text-[13px] font-semibold text-[#3d6bc5] mb-1 mt-2" {...props} />,
                        code: (props: ComponentPropsWithoutRef<"code">) => <code className="text-[12px] px-1.5 py-0.5 rounded-md bg-[#5b8dee]/8 text-[#3d6bc5] font-mono" {...props} />,
                        a: (props: ComponentPropsWithoutRef<"a">) => <a className="text-[#5b8dee] underline" {...props} />,
                      }}>{msg.text}</ReactMarkdown>
                      {msg.references && msg.references.length > 0 && (
                        <details className="mt-2 group">
                          <summary className="text-[11px] text-[#7b8ba5] cursor-pointer hover:text-[#3d6bc5] transition-colors select-none">
                            Referenced {msg.references.length} document{msg.references.length > 1 ? "s" : ""}
                          </summary>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {msg.references.map((ref) => (
                              <span
                                key={ref.id}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] bg-[#5b8dee]/6 text-[#3a5a8c] border border-[#5b8dee]/10"
                              >
                                <span className="opacity-50">&#128196;</span>
                                {ref.filename.length > 30 ? ref.filename.slice(0, 28) + "..." : ref.filename}
                              </span>
                            ))}
                          </div>
                        </details>
                      )}
                      {msg.chips && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {msg.chips.map((chip) => (
                            <button
                              key={`${msg.id}-${chip.label}`}
                              onClick={() => handleChatChip(chip)}
                              className="px-3.5 py-2 rounded-xl text-[12px] font-medium bg-white/70 border border-blue-100/30 text-[#3a5a8c] hover:bg-white/90 hover:border-blue-200/40 transition-all"
                            >
                              {chip.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="inline-block px-4 py-2.5 rounded-2xl text-[13px] font-medium bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white max-w-[85%]">
                      {msg.text}
                    </div>
                  )}
                </div>
              ))}
              {chatMode === "guardian" && chatLoading && (
                <div className="bg-white/50 backdrop-blur rounded-2xl p-4 border border-white/60">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'0ms'}} />
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'150ms'}} />
                    <div className="w-2 h-2 rounded-full bg-[#5b8dee] animate-bounce" style={{animationDelay:'300ms'}} />
                  </div>
                </div>
              )}
              {chatMode === "form-filler" && formFillPreview && (
                <FormPreviewCard
                  fields={formFillPreview.fields}
                  formFieldCount={formFillPreview.formFieldCount}
                  filledCount={formFillPreview.filledCount}
                  unfilledCount={formFillPreview.unfilledCount}
                  onGenerate={handleFormFillGenerate}
                  onCancel={() => setFormFillPreview(null)}
                  disabled={formFillLoading}
                />
              )}
            </div>

            {/* Input — mode-conditional */}
            {chatMode === "guardian" ? (
              <div className="p-4 border-t border-blue-50/40 flex-shrink-0">
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  const input = (e.target as HTMLFormElement).elements.namedItem("msg") as HTMLInputElement;
                  const msg = input.value.trim();
                  if (!msg || chatLoading) return;
                  input.value = "";
                  await sendChatMessage(msg);
                }} className="flex gap-2">
                  <input
                    name="msg"
                    type="text"
                    placeholder="Ask about your compliance..."
                    className="flex-1 px-4 py-2.5 rounded-xl border border-white/70 bg-white/60 text-[13px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    disabled={chatLoading}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white text-[13px] font-medium flex-shrink-0 disabled:opacity-50"
                  >
                    Send
                  </button>
                </form>
              </div>
            ) : (
              <FormFillerUpload
                onSubmit={handleFormFillSubmit}
                disabled={formFillLoading}
              />
            )}
          </div>
        )}
      </div>

      {/* Chat toggle button — fixed bottom-right when panel is closed */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 px-4 py-3 rounded-2xl bg-white/60 backdrop-blur-xl border border-white/60 shadow-[0_4px_24px_rgba(91,141,238,0.1)] hover:shadow-[0_8px_32px_rgba(91,141,238,0.15)] transition-all hover:-translate-y-0.5 group"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] flex items-center justify-center flex-shrink-0 p-1.5">
            <div className="flex flex-col gap-[2px] w-full">
              <div className="h-[3px] rounded-sm bg-white" style={{width:'100%',transform:'translateX(1px)'}} />
              <div className="h-[3px] rounded-sm bg-white" style={{width:'100%',transform:'translateX(-0.5px)'}} />
              <div className="h-[3px] rounded-sm bg-white" style={{width:'100%',transform:'translateX(1.5px)'}} />
            </div>
          </div>
          <span className="text-[12px] font-medium text-[#3a5a8c] hidden md:inline">
            {chatMode === "guardian"
              ? (hasGuardianQuestion ? "We have a question for you" : "Guardian Assistant")
              : "Form Filler"}
          </span>
          {chatMode === "guardian" && hasGuardianQuestion && (
            <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
          )}
        </button>
      )}
    </div>
  );
}
