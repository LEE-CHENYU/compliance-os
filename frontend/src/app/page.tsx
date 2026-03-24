"use client";

import { useRouter } from "next/navigation";

const FORMS = [
  "I-20", "I-94", "I-983", "I-797", "EAD (I-766)", "I-129", "AR-11", "DS-160",
  "1040-NR", "Form 8843", "Form 3520", "Form 8938", "Schedule C", "Schedule NEC", "W-8BEN",
  "Form 5472", "Pro forma 1120", "1120-S", "EIN Letter", "Articles of Org",
];
const DEADLINES = ["FBAR (FinCEN 114)", "DE Annual Report", "60-day Grace Period", "90-day Unemployment", "10-day Address Report"];
const PHRASES = [
  "Substantial Presence Test", "Effectively Connected Income", "Disregarded Entity",
  "Duration of Status", "Material Change", "Unauthorized Employment", "Cap-Gap Extension",
  "Corporate Veil", "SEVIS Termination", "Treaty Rate",
];

export default function Home() {
  const router = useRouter();

  return (
    <>
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-10 py-3.5 flex items-center justify-between bg-[#e0e8f3]/60 backdrop-blur-2xl border-b border-blue-200/20">
        <div className="text-lg font-extrabold text-[#0d1424] tracking-tight">Guardian</div>
        <div className="flex gap-8 text-sm font-medium text-[#7b8ba5]">
          <a href="#cloud" className="hover:text-[#1a2036]">What we check</a>
          <a href="#how" className="hover:text-[#1a2036]">How it works</a>
        </div>
        <button
          onClick={() => router.push("/check/stem-opt")}
          className="px-5 py-2 rounded-lg bg-[#1a2036] text-white text-sm font-semibold shadow-md hover:shadow-lg transition-all"
        >
          Find my risks
        </button>
      </nav>

      {/* Hero */}
      <section className="min-h-screen pt-28 pb-16 px-12 max-w-[1360px] mx-auto grid grid-cols-[1fr_1.3fr] items-center gap-6">
        <div className="max-w-[500px]">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold text-[#5b8dee] bg-white/60 backdrop-blur border border-blue-200/20 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[#5b8dee] shadow-[0_0_8px_rgba(91,141,238,0.4)]" />
            Your compliance memory
          </div>
          <h1 className="text-[50px] font-extrabold leading-[1.06] tracking-[-0.04em] text-[#0d1424] mb-5">
            Check your documents before USCIS does
          </h1>
          <p className="text-[17px] text-[#556480] leading-relaxed mb-9">
            We cross-check your immigration and tax filings to find mismatches, missing forms, and deadline risks you don&apos;t know about yet.
          </p>
          <div className="flex gap-3 mb-12">
            <button
              onClick={() => router.push("/check/stem-opt")}
              className="px-8 py-4 rounded-xl bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] text-white font-semibold text-[15px] shadow-[0_4px_16px_rgba(74,116,212,0.3)] hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)] hover:-translate-y-0.5 transition-all"
            >
              Find my risks
            </button>
            <a
              href="#cloud"
              className="px-8 py-4 rounded-xl bg-white/70 text-[#3a5a8c] font-medium text-[15px] border border-blue-200/20 backdrop-blur hover:bg-white/85 transition-all"
            >
              See what we check
            </a>
          </div>
          <div className="flex gap-7">
            {[
              ["47", "Forms tracked"],
              ["23", "Deadlines"],
              ["156", "Key phrases"],
            ].map(([num, label]) => (
              <div key={label}>
                <div className="text-2xl font-bold text-[#0d1424]">{num}</div>
                <div className="text-xs text-[#8e9ab5] mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Cube placeholder — will be replaced with Three.js later */}
        <div className="flex items-center justify-center h-[600px] relative">
          <div className="text-center text-[#8e9ab5] text-sm">
            <div className="w-48 h-48 rounded-lg bg-white/40 backdrop-blur border border-white/60 shadow-lg mx-auto mb-4 flex items-center justify-center text-[#5b8dee] font-semibold">
              3D Cube
            </div>
            <p>Interactive visual loads here</p>
          </div>
        </div>
      </section>

      {/* Form Cloud */}
      <section id="cloud" className="max-w-[1200px] mx-auto mb-10">
        <div className="bg-white/45 backdrop-blur-xl border border-white/60 rounded-[28px] shadow-sm px-16 py-20">
          <h2 className="text-4xl font-extrabold tracking-tight text-center text-[#0d1424] mb-3">
            This is what you&apos;re supposed to track
          </h2>
          <p className="text-base text-[#556480] text-center max-w-[480px] mx-auto mb-10 leading-relaxed">
            Forms, deadlines, key phrases, reporting windows. One missed item can cost $25,000 or your status.
          </p>
          <div className="flex flex-wrap justify-center gap-1.5 max-w-[820px] mx-auto">
            {FORMS.map((f) => (
              <span key={f} className="px-4 py-2 rounded-lg text-[12.5px] font-medium bg-white/65 backdrop-blur border border-blue-200/10 text-[#3d6bc5] hover:bg-white/85 hover:-translate-y-0.5 transition-all cursor-default">
                {f}
              </span>
            ))}
            {DEADLINES.map((d) => (
              <span key={d} className="px-4 py-2 rounded-lg text-[12.5px] font-semibold bg-white/65 backdrop-blur border border-blue-200/10 text-[#3d6bc5] hover:bg-white/85 hover:-translate-y-0.5 transition-all cursor-default">
                {d}
              </span>
            ))}
            {PHRASES.map((p) => (
              <span key={p} className="px-4 py-2 rounded-lg text-[12.5px] italic font-normal bg-white/65 backdrop-blur border border-blue-200/10 text-[#7b8ba5] hover:bg-white/85 hover:-translate-y-0.5 transition-all cursor-default">
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Two Tracks */}
      <section className="max-w-[1200px] mx-auto mb-10">
        <div className="bg-white/45 backdrop-blur-xl border border-white/60 rounded-[28px] shadow-sm px-16 py-20">
          <h2 className="text-4xl font-extrabold tracking-tight text-center text-[#0d1424] mb-3">
            Pick your check
          </h2>
          <p className="text-base text-[#556480] text-center mb-10">
            Two focused tracks. Upload documents, get answers.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => router.push("/check/stem-opt")}
              className="text-left bg-white/60 backdrop-blur rounded-2xl p-9 border border-white/70 hover:bg-white/80 hover:-translate-y-1 hover:shadow-[0_16px_48px_rgba(91,141,238,0.08)] hover:border-blue-200/30 transition-all"
            >
              <div className="w-11 h-11 rounded-xl bg-blue-50 border border-blue-100/50 flex items-center justify-center text-xl mb-5">🎓</div>
              <h3 className="text-xl font-bold mb-2 tracking-tight">STEM OPT Check</h3>
              <p className="text-sm text-[#556480] leading-relaxed mb-5">
                Upload your I-983 and employment letter. We cross-check every field and tell you what doesn&apos;t match.
              </p>
              <div className="flex flex-col gap-1.5 text-[13px] text-[#4a5f80]">
                {["Job title consistency", "Work location vs I-983", "Salary match", "Duties vs STEM degree", "Employer name vs E-Verify", "12-month evaluation status"].map((c) => (
                  <span key={c} className="flex items-center gap-2.5">
                    <span className="w-1 h-1 rounded-sm bg-blue-200" />
                    {c}
                  </span>
                ))}
              </div>
            </button>
            <button
              onClick={() => router.push("/check/entity")}
              className="text-left bg-white/60 backdrop-blur rounded-2xl p-9 border border-white/70 hover:bg-white/80 hover:-translate-y-1 hover:shadow-[0_16px_48px_rgba(91,141,238,0.08)] hover:border-blue-200/30 transition-all"
            >
              <div className="w-11 h-11 rounded-xl bg-blue-50 border border-blue-100/50 flex items-center justify-center text-xl mb-5">🏢</div>
              <h3 className="text-xl font-bold mb-2 tracking-tight">Entity Check</h3>
              <p className="text-sm text-[#556480] leading-relaxed mb-5">
                Answer 5 questions and upload your tax return. We check if your entity structure matches what was filed.
              </p>
              <div className="flex flex-col gap-1.5 text-[13px] text-[#4a5f80]">
                {["S-Corp eligibility for NRAs", "Form 5472 filing status", "Entity type vs tax return", "Foreign capital documentation", "Schedule C on OPT/STEM", "1040 vs 1040-NR"].map((c) => (
                  <span key={c} className="flex items-center gap-2.5">
                    <span className="w-1 h-1 rounded-sm bg-blue-200" />
                    {c}
                  </span>
                ))}
              </div>
            </button>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-[680px] mx-auto py-20 px-12">
        <h2 className="text-4xl font-extrabold tracking-tight text-center text-[#0d1424] mb-12">How it works</h2>
        {[
          ["01", "Choose your check", "STEM OPT document cross-check or entity compliance check.", "10 sec"],
          ["02", "Upload 1–2 documents", "I-983 + employment letter, or your tax return. We extract every field.", "30 sec"],
          ["03", "See what we found", "Side-by-side comparison. Matches, mismatches, and missing items.", "~15 sec"],
          ["04", "Answer 3 quick questions", "Only about the issues we found. Each one explains why it matters.", "1 min"],
          ["05", "Get your case snapshot", "Timeline, findings, next steps, and things to watch — all in one view.", "Instant"],
        ].map(([num, title, desc, time]) => (
          <div key={num} className="flex gap-5 py-5 border-b border-blue-200/15 items-start">
            <span className="text-[13px] font-bold text-[#c0cde0] w-7 pt-0.5">{num}</span>
            <div className="flex-1">
              <h4 className="text-base font-semibold mb-1">{title}</h4>
              <p className="text-sm text-[#556480] leading-relaxed">{desc}</p>
            </div>
            <span className="text-xs font-medium text-[#5b8dee] bg-blue-50/60 px-3 py-1 rounded-lg whitespace-nowrap">{time}</span>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer className="text-center py-12 text-[13px] text-[#8e9ab5] leading-relaxed">
        Documents sent to OpenAI for field extraction only. Never stored or shared beyond that.<br />
        No account needed. Your check URL is your bookmark. Return anytime.
      </footer>
    </>
  );
}
