"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-2xl font-extrabold text-[#0d1424] mb-2">Guardian</div>
          <p className="text-sm text-[#556480]">
            {isRegister ? "Create your account" : "Sign in to your case"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-8 shadow-[0_4px_24px_rgba(91,141,238,0.06)]">
          {error && (
            <div className="mb-4 px-4 py-2 rounded-xl text-sm text-red-600 bg-red-50/60 border border-red-100/40">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label className="block text-sm font-medium text-[#0d1424] mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
              placeholder="you@example.com"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-[#0d1424] mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-3 rounded-xl border border-white/70 bg-white/60 text-[15px] focus:border-[#5b8dee] focus:outline-none focus:ring-2 focus:ring-blue-200/30"
              placeholder={isRegister ? "At least 6 characters" : "Your password"}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white font-semibold text-[15px] shadow-[0_4px_16px_rgba(74,116,212,0.3)] hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)] transition-all"
          >
            {loading ? "..." : isRegister ? "Create account" : "Sign in"}
          </button>

          <div className="text-center mt-4">
            <button
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(""); }}
              className="text-sm text-[#5b8dee] hover:underline"
            >
              {isRegister ? "Already have an account? Sign in" : "Need an account? Create one"}
            </button>
          </div>
        </form>

        <div className="text-center mt-6">
          <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            &larr; Back to home
          </button>
        </div>
      </div>
    </div>
  );
}
