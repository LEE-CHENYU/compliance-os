"use client";

import { useState } from "react";
import { register, linkCheckToUser, isLoggedIn, getGoogleAuthUrl } from "@/lib/auth";

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

  async function handleGoogleSignIn() {
    try {
      // Store checkId so we can link after Google redirect
      if (typeof window !== "undefined") {
        localStorage.setItem("guardian_pending_check", checkId);
      }
      const url = await getGoogleAuthUrl();
      window.location.href = url;
    } catch {
      setError("Google sign-in is not configured yet");
    }
  }

  if (isLoggedIn()) {
    linkCheckToUser(checkId).then(onSuccess);
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0d1424]/20 backdrop-blur-sm">
      <div className="w-full max-w-sm mx-6 bg-white/70 backdrop-blur-xl rounded-2xl border border-white/60 p-8 shadow-[0_16px_64px_rgba(91,141,238,0.15)]">
        <h2 className="text-xl font-extrabold text-[#0d1424] mb-1">Create your account</h2>
        <p className="text-sm text-[#556480] mb-6">Save your results to your personal data room. We&apos;ll track deadlines and prompt you when something needs attention.</p>

        {/* Google Sign-In */}
        <button
          onClick={handleGoogleSignIn}
          className="w-full flex items-center justify-center gap-3 py-3 rounded-xl bg-white border border-gray-200 text-[14px] font-medium text-[#3c4043] hover:bg-gray-50 hover:shadow-sm transition-all mb-4"
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-[#8e9ab5]">or</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {error && (
          <div className="mb-4 px-4 py-2 rounded-xl text-sm text-red-600 bg-red-50/60 border border-red-100/40">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
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
    </div>
  );
}
