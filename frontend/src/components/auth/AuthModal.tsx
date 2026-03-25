"use client";

import { useState } from "react";
import { register, linkCheckToUser, isLoggedIn } from "@/lib/auth";

interface AuthModalProps {
  checkId: string;
  onSuccess: () => void;
}

export default function AuthModal({ checkId, onSuccess }: AuthModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password);
      await linkCheckToUser(checkId);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  if (isLoggedIn()) {
    // Already logged in — just link and proceed
    linkCheckToUser(checkId).then(onSuccess);
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d1424]/20 backdrop-blur-sm">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm mx-6 bg-white/70 backdrop-blur-xl rounded-2xl border border-white/60 p-8 shadow-[0_16px_64px_rgba(91,141,238,0.15)]"
      >
        <h2 className="text-xl font-extrabold text-[#0d1424] mb-1">Create your account</h2>
        <p className="text-sm text-[#556480] mb-6">Save your results to your personal data room. We&apos;ll track deadlines and prompt you when something needs attention.</p>

        {error && (
          <div className="mb-4 px-4 py-2 rounded-xl text-sm text-red-600 bg-red-50/60 border border-red-100/40">
            {error}
          </div>
        )}

        <div className="mb-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="Email"
            className="w-full px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
        </div>

        <div className="mb-6">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            placeholder="Password (6+ characters)"
            className="w-full px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white font-semibold text-[15px] shadow-[0_4px_16px_rgba(74,116,212,0.3)] transition-all"
        >
          {loading ? "Creating..." : "Create account & save"}
        </button>
      </form>
    </div>
  );
}
