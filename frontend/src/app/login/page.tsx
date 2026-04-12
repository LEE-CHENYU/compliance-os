"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login, register, getGoogleAuthUrl, handleGoogleCallback } from "@/lib/auth";
import { isForm8843GtmNextPath, trackForm8843FunnelEvent } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export default function LoginPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-[#8e9ab5]">Loading...</div>}>
      <LoginPage />
    </Suspense>
  );
}

function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") || "/dashboard";
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const authViewTrackedRef = useRef(false);

  useEffect(() => {
    if (!isForm8843GtmNextPath(nextPath) || authViewTrackedRef.current) {
      return;
    }
    authViewTrackedRef.current = true;
    trackForm8843FunnelEvent("form_8843_gtm_auth_viewed", {
      auth_mode: isRegister ? "register" : "signin",
      next_path: nextPath,
    });
  }, [isRegister, nextPath]);

  // Handle Google OAuth callback
  useEffect(() => {
    const token = params.get("token");
    if (token) {
      const user = handleGoogleCallback(params);
      if (user) {
        if (isForm8843GtmNextPath(nextPath)) {
          trackForm8843FunnelEvent("form_8843_gtm_auth_succeeded", {
            auth_mode: "google",
            next_path: nextPath,
          });
        }
        router.push(nextPath);
      }
    }
  }, [nextPath, params, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    if (isForm8843GtmNextPath(nextPath)) {
      trackForm8843FunnelEvent("form_8843_gtm_auth_submitted", {
        auth_mode: isRegister ? "register" : "signin",
        auth_method: "password",
        next_path: nextPath,
      });
    }
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      if (isForm8843GtmNextPath(nextPath)) {
        trackForm8843FunnelEvent("form_8843_gtm_auth_succeeded", {
          auth_mode: isRegister ? "register" : "signin",
          auth_method: "password",
          next_path: nextPath,
        });
      }
      router.push(nextPath);
    } catch (err: unknown) {
      if (isForm8843GtmNextPath(nextPath)) {
        trackForm8843FunnelEvent("form_8843_gtm_auth_failed", {
          auth_mode: isRegister ? "register" : "signin",
          auth_method: "password",
          next_path: nextPath,
          error_message: err instanceof Error ? err.message : "Something went wrong",
        });
      }
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    try {
      if (isForm8843GtmNextPath(nextPath)) {
        trackForm8843FunnelEvent("form_8843_gtm_auth_submitted", {
          auth_mode: isRegister ? "register" : "signin",
          auth_method: "google",
          next_path: nextPath,
        });
      }
      const url = await getGoogleAuthUrl(nextPath);
      window.location.href = url;
    } catch {
      setError("Google sign-in is not configured yet");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-2xl font-extrabold text-[#0d1424] mb-2">Guardian</div>
          <p className="text-sm text-[#556480]">
            {isRegister ? "Create your account" : "Sign in to your data room"}
          </p>
        </div>

        <div className="bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60 p-8 shadow-[0_4px_24px_rgba(91,141,238,0.06)]">
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

          {/* Email/Password form */}
          <form onSubmit={handleSubmit}>
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
        </div>

        <div className="text-center mt-6">
          <button onClick={() => router.push("/")} className="text-sm text-[#7b8ba5] hover:text-[#1a2036]">
            &larr; Back to home
          </button>
        </div>
      </div>
    </div>
  );
}
