"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn, getUser, logout } from "@/lib/auth";

function useScrollReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setRevealed(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, revealed };
}

const FORMS = ["I-20","I-94","I-983","I-797","EAD (I-766)","I-765","I-129","I-485","I-131","AR-11","DS-160","1040-NR","Form 8843","Form 3520","Form 8938","Schedule C","Schedule NEC","W-8BEN","Form 5472","Pro forma 1120","1120-S","EIN Letter","Articles of Org"];
const DEADLINES = ["FBAR (FinCEN 114)","DE Annual Report","60-day Grace Period","90-day Unemployment","10-day Address Report","Advance Parole Validity"];
const PHRASES = ["Substantial Presence Test","Effectively Connected Income","Disregarded Entity","Duration of Status","Material Change","Unauthorized Employment","Cap-Gap Extension","Corporate Veil","SEVIS Termination","Treaty Rate","Adjustment of Status","Concurrent Filing"];
const SLAB_LABELS = ["I-983","Form 5472","1040-NR","FBAR","EAD","AR-11","I-797"];

export default function Home() {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [partyIndex, setPartyIndex] = useState(0);
  const PARTIES = ["USCIS", "the IRS", "your state", "DHS", "FinCEN"];

  // Scroll-triggered reveal for each section
  const formCloud = useScrollReveal(0.1);
  const trackSelect = useScrollReveal(0.1);
  const vault = useScrollReveal(0.15);
  const penaltySection = useScrollReveal(0.1);
  const openclawSection = useScrollReveal(0.1);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
    const user = getUser();
    if (user) setUserEmail(user.email);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setPartyIndex((prev) => (prev + 1) % PARTIES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [PARTIES.length]);

  return (
    <>
      <style jsx global>{`
        body {
          background:
            radial-gradient(ellipse 80% 60% at 20% 10%, rgba(91,141,238,0.1) 0%, transparent 60%),
            radial-gradient(ellipse 60% 50% at 75% 25%, rgba(120,150,210,0.08) 0%, transparent 55%),
            linear-gradient(180deg, #d5dded 0%, #dde5f0 30%, #e8eff6 60%, #f0f4f9 100%);
          background-attachment: fixed;
        }
        body::before {
          content: '';
          position: fixed; inset: 0;
          background-image: radial-gradient(rgba(91,141,238,0.05) 1px, transparent 1px);
          background-size: 32px 32px;
          pointer-events: none; z-index: 0;
        }

        .iso-scene { width: 680px; height: 600px; perspective: 1800px; position: relative; }
        .iso-cube {
          position: absolute; top: 48%; left: 42%;
          transform-style: preserve-3d;
          transform: translate(-50%, -50%) rotateX(-20deg) rotateY(-35deg);
        }
        .slab {
          position: absolute; width: 300px;
          transform-style: preserve-3d;
          animation-timing-function: cubic-bezier(0.25, 1, 0.5, 1);
          animation-fill-mode: both;
        }
        .s-front {
          position: absolute; width: 300px; height: 52px; left: 0; top: 0;
          background: linear-gradient(180deg, #ffffff 0%, #f6f8fd 100%);
          border: 1px solid rgba(91,141,238,0.12);
          border-top-color: #fff;
          box-shadow: 0 8px 40px rgba(50,80,140,0.12), 0 2px 8px rgba(0,0,0,0.04);
        }
        .s-side {
          position: absolute; width: 210px; height: 52px;
          left: 300px; top: 0;
          transform-origin: left center; transform: rotateY(90deg);
          background: linear-gradient(180deg, #e4eaf6 0%, #dae2f2 100%);
          border: 1px solid rgba(91,141,238,0.08);
        }
        .s-cap {
          position: absolute; width: 300px; height: 210px;
          left: 0; top: 0;
          transform-origin: center top; transform: rotateX(-90deg);
          background: linear-gradient(160deg, #ffffff 0%, #f4f7fd 100%);
          border: 1px solid rgba(91,141,238,0.06);
        }
        .s-label {
          position: absolute; left: 20px; top: 50%;
          transform: translateY(-50%);
          font-size: 13px; font-weight: 600;
          color: rgba(50,90,170,0.55);
          text-shadow: 0 0 12px rgba(255,255,255,0.4);
          letter-spacing: 0.02em;
          pointer-events: none; z-index: 2;
        }

        .slab-0 { top: 0;    animation: k0 10s infinite; }
        .slab-1 { top: 62px;  animation: k1 10s infinite; }
        .slab-2 { top: 124px; animation: k2 10s infinite; }
        .slab-3 { top: 186px; animation: k3 10s infinite; }
        .slab-4 { top: 248px; animation: k4 10s infinite; }
        .slab-5 { top: 310px; animation: k5 10s infinite; }
        .slab-6 { top: 372px; animation: k6 10s infinite; }

        @keyframes k0 {
          0%,14%{transform:translateX(0) translateZ(0)}
          18%,38%{transform:translateX(40px) translateZ(0)}
          42%,62%{transform:translateX(40px) translateZ(20px)}
          66%,86%{transform:translateX(-14px) translateZ(0)}
          90%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k1 {
          0%,18%{transform:translateX(0) translateZ(0)}
          22%,42%{transform:translateX(-32px) translateZ(0)}
          46%,66%{transform:translateX(-32px) translateZ(-22px)}
          70%,90%{transform:translateX(16px) translateZ(0)}
          94%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k2 {
          0%,10%{transform:translateX(0) translateZ(0)}
          14%,34%{transform:translateX(52px) translateZ(0)}
          38%,58%{transform:translateX(52px) translateZ(16px)}
          62%,82%{transform:translateX(-20px) translateZ(0)}
          86%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k3 {
          0%,22%{transform:translateX(0) translateZ(0)}
          26%,46%{transform:translateX(-26px) translateZ(28px)}
          50%,70%{transform:translateX(24px) translateZ(0)}
          74%,94%{transform:translateX(24px) translateZ(-16px)}
          98%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k4 {
          0%,16%{transform:translateX(0) translateZ(0)}
          20%,40%{transform:translateX(44px) translateZ(-20px)}
          44%,64%{transform:translateX(-28px) translateZ(0)}
          68%,88%{transform:translateX(-28px) translateZ(24px)}
          92%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k5 {
          0%,20%{transform:translateX(0) translateZ(0)}
          24%,44%{transform:translateX(-36px) translateZ(12px)}
          48%,68%{transform:translateX(18px) translateZ(0)}
          72%,92%{transform:translateX(18px) translateZ(-18px)}
          96%,100%{transform:translateX(0) translateZ(0)}
        }
        @keyframes k6 {
          0%,12%{transform:translateX(0) translateZ(0)}
          16%,36%{transform:translateX(34px) translateZ(0)}
          40%,60%{transform:translateX(34px) translateZ(26px)}
          64%,84%{transform:translateX(-22px) translateZ(0)}
          88%,100%{transform:translateX(0) translateZ(0)}
        }

        .cube-shadow {
          position: absolute; bottom: 0; left: 42%;
          transform: translateX(-50%);
          width: 420px; height: 240px;
          background: radial-gradient(ellipse, rgba(40,70,130,0.1) 0%, transparent 60%);
          pointer-events: none; filter: blur(8px);
        }

        .section-panel {
          position: relative; z-index: 1;
          max-width: 1200px; margin: 0 auto 40px;
          padding: 80px 60px;
          background: rgba(255,255,255,0.45);
          backdrop-filter: blur(20px) saturate(1.1);
          border: 1px solid rgba(255,255,255,0.6);
          border-radius: 28px;
          box-shadow: 0 4px 32px rgba(91,141,238,0.04);
        }

        @keyframes slideIn {
          0% { transform: translateX(20px); opacity: 0; }
          100% { transform: translateX(0); opacity: 1; }
        }
        @keyframes fadeUp {
          0% { transform: translateY(16px); opacity: 0; }
          100% { transform: translateY(0); opacity: 1; }
        }
        @keyframes countUp {
          0% { opacity: 0; transform: scale(0.8); }
          60% { opacity: 1; transform: scale(1.05); }
          100% { opacity: 1; transform: scale(1); }
        }
        /* Scroll-triggered: hidden until .revealed */
        .scroll-section {
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }
        .scroll-section.revealed {
          opacity: 1;
          transform: translateY(0);
        }

        .penalty-card {
          opacity: 0;
          transform: translateY(16px);
        }
        .revealed .penalty-card {
          animation: fadeUp 0.5s ease-out both;
        }
        .revealed .penalty-card:nth-child(1) { animation-delay: 0.1s; }
        .revealed .penalty-card:nth-child(2) { animation-delay: 0.2s; }
        .revealed .penalty-card:nth-child(3) { animation-delay: 0.3s; }
        .revealed .penalty-card:nth-child(4) { animation-delay: 0.4s; }
        .revealed .penalty-card:nth-child(5) { animation-delay: 0.5s; }

        .penalty-hero {
          opacity: 0;
          transform: scale(0.8);
        }
        .revealed .penalty-hero { animation: countUp 0.8s ease-out both; }

        .case-card {
          opacity: 0;
          transform: translateY(16px);
        }
        .revealed .case-card { animation: fadeUp 0.6s ease-out both; }
        .revealed .case-card:nth-child(1) { animation-delay: 0.15s; }
        .revealed .case-card:nth-child(2) { animation-delay: 0.3s; }
        .revealed .case-card:nth-child(3) { animation-delay: 0.45s; }

        /* Mobile responsive rules moved to globals.css for reliable media query support */
      `}</style>

      {/* Nav */}
      <nav style={{position:'fixed',top:0,left:0,right:0,zIndex:100,padding:'14px 40px',display:'flex',alignItems:'center',justifyContent:'space-between',background:'rgba(220,230,244,0.6)',backdropFilter:'blur(24px) saturate(1.2)',borderBottom:'1px solid rgba(91,141,238,0.08)'}}>
        <div style={{fontSize:18,fontWeight:800,letterSpacing:'-0.01em',color:'#0d1424',display:'flex',alignItems:'center',gap:10}}>
          <div style={{width:24,height:24,display:'flex',flexDirection:'column',gap:3,transform:'perspective(200px) rotateX(-8deg) rotateY(12deg)'}}>
            <div style={{height:5,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',borderRadius:1,width:24,transform:'translateX(2px)'}} />
            <div style={{height:5,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',borderRadius:1,width:24,transform:'translateX(-1px)'}} />
            <div style={{height:5,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',borderRadius:1,width:24,transform:'translateX(3px)'}} />
          </div>
          Guardian
        </div>
        <div className="nav-links-desktop" style={{display:'flex',gap:32,fontSize:14,fontWeight:500,color:'#7b8ba5'}}>
          <a href="#cloud" style={{textDecoration:'none',color:'inherit'}}>What we check</a>
          <a href="#how" style={{textDecoration:'none',color:'inherit'}}>How it works</a>
          <button onClick={() => router.push("/services")} style={{background:'transparent',border:'none',padding:0,color:'inherit',font:'inherit',cursor:'pointer'}}>
            Services
          </button>
          <button onClick={() => router.push("/docs/install")} style={{background:'transparent',border:'none',padding:0,color:'inherit',font:'inherit',cursor:'pointer'}}>
            Docs
          </button>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          {loggedIn ? (
            <>
              <span style={{fontSize:13,color:'#556480'}}>{userEmail}</span>
              <button onClick={() => router.push("/dashboard")} style={{padding:'9px 22px',borderRadius:10,background:'#1a2036',color:'white',fontSize:13,fontWeight:600,border:'none',cursor:'pointer'}}>
                Dashboard
              </button>
              <button onClick={() => { logout(); setLoggedIn(false); }} style={{padding:'9px 22px',borderRadius:10,background:'transparent',color:'#7b8ba5',fontSize:13,fontWeight:500,border:'none',cursor:'pointer'}}>
                Sign out
              </button>
            </>
          ) : (
            <>
              <button onClick={() => router.push("/login")} style={{padding:'9px 22px',borderRadius:10,background:'transparent',color:'#5b8dee',fontSize:13,fontWeight:600,border:'none',cursor:'pointer'}}>
                Sign in
              </button>
              <button onClick={() => router.push("/check")} style={{padding:'9px 22px',borderRadius:10,background:'#1a2036',color:'white',fontSize:13,fontWeight:600,border:'none',cursor:'pointer',boxShadow:'0 2px 8px rgba(0,0,0,0.1)'}}>
                Find my risks
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-grid" style={{position:'relative',zIndex:1,minHeight:'100vh',display:'grid',gridTemplateColumns:'1fr 1.3fr',alignItems:'center',maxWidth:1360,margin:'0 auto',padding:'120px 48px 80px',gap:16}}>
        <div style={{maxWidth:500}}>
          <div style={{display:'inline-flex',alignItems:'center',gap:8,padding:'6px 16px',borderRadius:24,fontSize:12,fontWeight:600,color:'#5b8dee',marginBottom:24,background:'rgba(255,255,255,0.6)',backdropFilter:'blur(12px)',border:'1px solid rgba(91,141,238,0.12)'}}>
            <span style={{width:6,height:6,borderRadius:'50%',background:'#5b8dee',boxShadow:'0 0 8px rgba(91,141,238,0.4)'}} />
            Your compliance memory
          </div>
          <h1 style={{fontSize:50,fontWeight:800,letterSpacing:'-0.04em',lineHeight:1.06,marginBottom:20,color:'#0d1424'}}>
            Check your documents before{' '}
            <span key={partyIndex} style={{color:'#5b8dee',display:'inline-block',animation:'slideIn 0.4s ease-out'}}>{PARTIES[partyIndex]}</span>
            {' '}does
          </h1>
          <p style={{fontSize:17,color:'#556480',lineHeight:1.65,marginBottom:36}}>
            We cross-check your immigration and tax filings to find mismatches, missing forms, and deadline risks you don&apos;t know about yet.
          </p>
          <div style={{display:'flex',gap:12,marginBottom:48,alignItems:'center',flexWrap:'wrap'}}>
            <button onClick={() => router.push("/check")} style={{padding:'15px 32px',borderRadius:12,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',color:'white',fontWeight:600,fontSize:15,border:'none',cursor:'pointer',boxShadow:'0 4px 16px rgba(74,116,212,0.3), inset 0 1px 0 rgba(255,255,255,0.12)',whiteSpace:'nowrap'}}>
              Find my risks
            </button>
            <a href="#cloud" style={{padding:'15px 32px',borderRadius:12,background:'rgba(255,255,255,0.7)',color:'#3a5a8c',fontWeight:500,fontSize:15,border:'1px solid rgba(91,141,238,0.1)',textDecoration:'none',backdropFilter:'blur(12px)',whiteSpace:'nowrap',display:'inline-block'}}>
              See what we check
            </a>
            <button onClick={() => router.push("/services")} style={{padding:'15px 32px',borderRadius:12,background:'rgba(255,255,255,0.7)',color:'#3a5a8c',fontWeight:500,fontSize:15,border:'1px solid rgba(91,141,238,0.1)',cursor:'pointer',backdropFilter:'blur(12px)',whiteSpace:'nowrap'}}>
              Browse services
            </button>
          </div>
          <div style={{display:'flex',gap:28}}>
            {[["47","Forms tracked"],["23","Deadlines"],["156","Key phrases"]].map(([n,l]) => (
              <div key={l}>
                <div style={{fontSize:24,fontWeight:700,color:'#0d1424'}}>{n}</div>
                <div style={{fontSize:12,color:'#8e9ab5',marginTop:2}}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* 3D Sliced Cube */}
        <div className="hero-visual-wrap" style={{display:'flex',alignItems:'center',justifyContent:'center',position:'relative',height:640}}>
          <div className="iso-scene">
            <div className="iso-cube">
              {SLAB_LABELS.map((label, i) => (
                <div key={label} className={`slab slab-${i}`}>
                  <div className="s-cap" />
                  <div className="s-front"><span className="s-label">{label}</span></div>
                  <div className="s-side" />
                </div>
              ))}
            </div>
          </div>
          <div className="cube-shadow" />
        </div>
      </section>

      {/* Form Cloud */}
      <div id="cloud" ref={formCloud.ref} className={`section-panel scroll-section${formCloud.revealed ? ' revealed' : ''}`}>
        <h2 style={{fontSize:36,fontWeight:800,letterSpacing:'-0.03em',marginBottom:12,color:'#0d1424',textAlign:'center'}}>
          This is what you&apos;re supposed to track
        </h2>
        <p style={{fontSize:16,color:'#556480',maxWidth:480,margin:'0 auto 40px',lineHeight:1.6,textAlign:'center'}}>
          Forms, deadlines, key phrases, reporting windows. One missed item can cost $25,000 or your status.
        </p>
        <div style={{display:'flex',flexWrap:'wrap',justifyContent:'center',gap:7,maxWidth:820,margin:'0 auto'}}>
          {FORMS.map(f => <span key={f} style={{padding:'8px 16px',borderRadius:8,fontSize:12.5,fontWeight:500,background:'rgba(255,255,255,0.65)',backdropFilter:'blur(8px)',border:'1px solid rgba(91,141,238,0.06)',color:'#3d6bc5',cursor:'default'}}>{f}</span>)}
          {DEADLINES.map(d => <span key={d} style={{padding:'8px 16px',borderRadius:8,fontSize:12.5,fontWeight:600,background:'rgba(255,255,255,0.65)',backdropFilter:'blur(8px)',border:'1px solid rgba(91,141,238,0.06)',color:'#3d6bc5',cursor:'default'}}>{d}</span>)}
          {PHRASES.map(p => <span key={p} style={{padding:'8px 16px',borderRadius:8,fontSize:12.5,fontWeight:400,fontStyle:'italic',background:'rgba(255,255,255,0.65)',backdropFilter:'blur(8px)',border:'1px solid rgba(91,141,238,0.06)',color:'#7b8ba5',cursor:'default'}}>{p}</span>)}
        </div>
      </div>

      {/* Two Tracks */}
      <div ref={trackSelect.ref} className={`section-panel scroll-section${trackSelect.revealed ? ' revealed' : ''}`}>
        <h2 style={{fontSize:36,fontWeight:800,letterSpacing:'-0.03em',textAlign:'center',marginBottom:12,color:'#0d1424'}}>Pick your check</h2>
        <p style={{fontSize:16,color:'#556480',textAlign:'center',marginBottom:40}}>Three focused tracks. Upload documents, get answers.</p>
        <div className="track-grid" style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:16}}>
          {[
            {letter:'A',title:'Young Professional',desc:'Upload your I-983 and employment letter. We cross-check every field and tell you what doesn\'t match.',checks:["Job title consistency","Work location vs I-983","Salary match","Duties vs STEM degree","Employer name vs E-Verify","12-month evaluation status"],href:'/check/stem-opt'},
            {letter:'B',title:'Entrepreneur',desc:'Answer 5 questions and upload your tax return. We check if your entity structure matches what was filed.',checks:["S-Corp eligibility for NRAs","Form 5472 filing status","Entity type vs tax return","Foreign capital documentation","Schedule C on OPT/STEM","1040 vs 1040-NR"],href:'/check/entity'},
            {letter:'C',title:'International Student',desc:'Upload your I-20 and offer letter. We check CPT authorization, travel readiness, and document consistency.',checks:["CPT employer match","Authorization dates","Travel signature","Full-time vs part-time","OPT eligibility","Program end date"],href:'/check/student'},
          ].map(card => (
            <button key={card.title} onClick={() => router.push(card.href)} style={{textAlign:'left',background:'rgba(255,255,255,0.6)',backdropFilter:'blur(16px)',borderRadius:20,padding:36,border:'1px solid rgba(255,255,255,0.7)',cursor:'pointer',transition:'all 0.3s'}}>
              <div style={{width:44,height:44,borderRadius:12,display:'flex',alignItems:'center',justifyContent:'center',fontSize:18,fontWeight:800,color:'#5b8dee',marginBottom:18,background:'rgba(91,141,238,0.06)'}}>{card.letter}</div>
              <h3 style={{fontSize:20,fontWeight:700,marginBottom:8,letterSpacing:'-0.02em'}}>{card.title}</h3>
              <p style={{fontSize:14,color:'#556480',lineHeight:1.6,marginBottom:20}}>{card.desc}</p>
              <div style={{display:'flex',flexDirection:'column',gap:7,fontSize:13,color:'#4a5f80'}}>
                {card.checks.map(c => <span key={c} style={{display:'flex',alignItems:'center',gap:10}}>
                  <span style={{width:4,height:4,borderRadius:1,background:'#b0c4e8',flexShrink:0}} />{c}
                </span>)}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* How it works */}
      <section id="how" style={{maxWidth:680,margin:'0 auto',padding:'80px 48px',position:'relative',zIndex:1}}>
        <h2 style={{fontSize:36,fontWeight:800,letterSpacing:'-0.03em',textAlign:'center',marginBottom:48,color:'#0d1424'}}>How it works</h2>
        {[
          ["01","Choose your check","STEM OPT document cross-check or entity compliance check.","10 sec"],
          ["02","Upload 1\u20132 documents","I-983 + employment letter, or your tax return. We extract every field.","30 sec"],
          ["03","See what we found","Side-by-side comparison. Matches, mismatches, and missing items.","~15 sec"],
          ["04","Answer 3 quick questions","Only about the issues we found. Each one explains why it matters.","1 min"],
          ["05","Get your case snapshot","Timeline, findings, next steps, and things to watch \u2014 all in one view.","Instant"],
          ["06","Save to your data room","Your documents, timeline, and risks \u2014 stored securely. We\u2019ll prompt you when something new needs checking.","Ongoing"],
        ].map(([num,title,desc,time]) => (
          <div key={num} style={{display:'flex',gap:20,padding:'22px 0',borderBottom:'1px solid rgba(91,141,238,0.06)',alignItems:'flex-start'}}>
            <span style={{fontSize:13,fontWeight:700,color:'#c0cde0',minWidth:28,paddingTop:3}}>{num}</span>
            <div style={{flex:1}}>
              <h4 style={{fontSize:16,fontWeight:600,marginBottom:4}}>{title}</h4>
              <p style={{fontSize:14,color:'#556480',lineHeight:1.5}}>{desc}</p>
            </div>
            <span style={{fontSize:12,fontWeight:500,color:'#5b8dee',background:'rgba(91,141,238,0.06)',padding:'4px 12px',borderRadius:8,whiteSpace:'nowrap'}}>{time}</span>
          </div>
        ))}
      </section>

      {/* Data Room */}
      <section ref={vault.ref} className={`section-panel scroll-section${vault.revealed ? ' revealed' : ''}`} style={{maxWidth:900,margin:'0 auto 40px'}}>
        <h2 style={{fontSize:36,fontWeight:800,letterSpacing:'-0.03em',textAlign:'center',marginBottom:12,color:'#0d1424'}}>
          Your personal compliance vault
        </h2>
        <p style={{fontSize:16,color:'#556480',textAlign:'center',maxWidth:540,margin:'0 auto 40px',lineHeight:1.6}}>
          After your first check, Guardian becomes your living case record. Documents organized by timeline, risks tracked automatically, and prompts when something needs attention.
        </p>
        <div className="vault-grid" style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:16}}>
          {[
            {num:'1',title:'Timeline view',desc:'Your immigration journey on one screen. Past events, today, upcoming deadlines \u2014 with documents attached to each moment.'},
            {num:'2',title:'Smart upload prompts',desc:'We tell you exactly what to upload next and why it matters. Each new document triggers automatic re-checking.'},
            {num:'3',title:'Risk monitoring',desc:'New risks surface as deadlines approach or documents change. Resolved issues get cleared automatically.'},
          ].map((item) => (
            <div key={item.title} style={{background:'rgba(255,255,255,0.5)',backdropFilter:'blur(16px)',borderRadius:16,padding:24,border:'1px solid rgba(255,255,255,0.6)'}}>
              <div style={{fontSize:28,fontWeight:800,color:'#5b8dee',marginBottom:12,opacity:0.4}}>{item.num}</div>
              <h3 style={{fontSize:15,fontWeight:700,marginBottom:6,color:'#0d1424'}}>{item.title}</h3>
              <p style={{fontSize:13,color:'#556480',lineHeight:1.5}}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Why Guardian */}
      <section ref={penaltySection.ref} className={`section-panel scroll-section${penaltySection.revealed ? ' revealed' : ''}`} style={{maxWidth:900,margin:'0 auto 40px'}}>
        <h2 style={{fontSize:36,fontWeight:800,letterSpacing:'-0.03em',textAlign:'center',marginBottom:12,color:'#0d1424'}}>
          The most popular tax software is defaulting you into mistakes
        </h2>
        <p style={{fontSize:16,color:'#556480',textAlign:'center',maxWidth:560,margin:'0 auto 32px',lineHeight:1.6}}>
          TurboTax <strong style={{color:'#0d1424'}}>cannot file Form 1040-NR</strong> at all. Other software often <strong style={{color:'#0d1424'}}>defaults you to the wrong form</strong>. One wrong default cascades into:
        </p>

        {/* Penalty hero — glowing callout */}
        <div className="penalty-hero penalty-hero-box" style={{textAlign:'center',margin:'0 auto 40px',maxWidth:400,padding:'32px 40px',borderRadius:24,background:'linear-gradient(135deg, rgba(79,70,229,0.06) 0%, rgba(99,102,241,0.03) 100%)',border:'1px solid rgba(79,70,229,0.1)',boxShadow:'0 8px 40px rgba(79,70,229,0.08), inset 0 1px 0 rgba(255,255,255,0.5)'}}>
          <div style={{fontSize:56,fontWeight:800,color:'#4f46e5',letterSpacing:'-0.04em',lineHeight:1}}>$1.5M+</div>
          <div style={{fontSize:13,color:'#6366f1',fontWeight:500,marginTop:6}}>potential penalty exposure</div>
          <div style={{fontSize:12,color:'#8e9ab5',marginTop:4}}>from one wrong default in your tax software</div>
        </div>

        {/* Penalty cards — staggered animation */}
        <div style={{display:'flex',flexDirection:'column',gap:8,maxWidth:640,margin:'0 auto 40px'}}>
          {[
            {consequence:'50% of your foreign savings',short:'Family bank accounts abroad over $10K? TurboTax defaults to "No."',tag:'FBAR'},
            {consequence:'$25,000 per year, retroactively',short:'Foreign-owned LLC? Required every year, even with $0 revenue.',tag:'Form 5472'},
            {consequence:'25% of every family transfer',short:'Parents sent money for tuition? Over $100K requires reporting.*',tag:'Form 3520'},
            {consequence:'Your visa status contradicted',short:'Filing as a resident when you\u2019re not. Affects future applications.',tag:'Wrong form'},
            {consequence:'$10,000+ in additional penalties',short:'Foreign assets over $50K need a separate form from FBAR.',tag:'FATCA'},
          ].map((item) => (
            <div key={item.tag} className="penalty-card" style={{background:'rgba(255,255,255,0.5)',backdropFilter:'blur(16px)',borderRadius:14,padding:'14px 18px',border:'1px solid rgba(255,255,255,0.6)',boxShadow:'0 2px 12px rgba(79,70,229,0.03)'}}>
              <div style={{display:'flex',alignItems:'start',gap:10,flexWrap:'wrap'}}>
                <div style={{flex:1,minWidth:200}}>
                  <div style={{fontSize:15,fontWeight:700,color:'#1e1b4b'}}>{item.consequence}</div>
                  <div style={{fontSize:12,color:'#7b8ba5',lineHeight:1.4,marginTop:2}}>{item.short}</div>
                </div>
                <span style={{fontSize:10,fontWeight:600,whiteSpace:'nowrap',padding:'3px 9px',borderRadius:20,background:'rgba(79,70,229,0.06)',color:'#6366f1',border:'1px solid rgba(79,70,229,0.08)',flexShrink:0}}>{item.tag}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{maxWidth:640,margin:'-24px auto 32px',textAlign:'left'}}>
          <span style={{fontSize:11,color:'#8e9ab5'}}>*Form 3520, FBAR, and FATCA apply only if you are a US tax resident (meet the Substantial Presence Test). Guardian checks this for you.</span>
        </div>

        {/* Real case studies — glass cards with gradient accent */}
        <div style={{maxWidth:640,margin:'0 auto 36px'}}>
          <div style={{fontSize:11,fontWeight:600,color:'#7b8ba5',textTransform:'uppercase',letterSpacing:'0.08em',marginBottom:12,textAlign:'center'}}>From the courts</div>
          <div className="cases-grid" style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:12}}>
            <div className="case-card" style={{background:'linear-gradient(160deg, rgba(255,255,255,0.6) 0%, rgba(238,242,255,0.4) 100%)',backdropFilter:'blur(16px)',borderRadius:18,padding:'20px 22px',border:'1px solid rgba(79,70,229,0.08)',boxShadow:'0 4px 24px rgba(79,70,229,0.04)'}}>
              <div style={{fontSize:28,fontWeight:800,color:'#4f46e5',marginBottom:2}}>$10.9M</div>
              <div style={{fontSize:12,fontWeight:600,color:'#0d1424',marginBottom:8}}>Mukhi v. Commissioner</div>
              <div style={{fontSize:11,color:'#556480',lineHeight:1.5}}>Form 3520 penalties upheld for unreported foreign trusts. Constitutional challenges rejected.</div>
              <div style={{fontSize:10,color:'#8e9ab5',marginTop:6}}>Tax Court, Nov 2024</div>
            </div>
            <div className="case-card" style={{background:'linear-gradient(160deg, rgba(255,255,255,0.6) 0%, rgba(238,242,255,0.4) 100%)',backdropFilter:'blur(16px)',borderRadius:18,padding:'20px 22px',border:'1px solid rgba(79,70,229,0.08)',boxShadow:'0 4px 24px rgba(79,70,229,0.04)'}}>
              <div style={{fontSize:28,fontWeight:800,color:'#4f46e5',marginBottom:2}}>$2.72M</div>
              <div style={{fontSize:12,fontWeight:600,color:'#0d1424',marginBottom:8}}>Bittner v. United States</div>
              <div style={{fontSize:11,color:'#556480',lineHeight:1.5}}>FBAR penalties across 272 accounts. Supreme Court reduced to $50K per report.</div>
              <div style={{fontSize:10,color:'#8e9ab5',marginTop:6}}>Supreme Court, Feb 2023</div>
            </div>
            <div className="case-card" style={{background:'linear-gradient(160deg, rgba(255,255,255,0.6) 0%, rgba(238,242,255,0.4) 100%)',backdropFilter:'blur(16px)',borderRadius:18,padding:'20px 22px',border:'1px solid rgba(79,70,229,0.08)',boxShadow:'0 4px 24px rgba(79,70,229,0.04)'}}>
              <div style={{fontSize:28,fontWeight:800,color:'#4f46e5',marginBottom:2}}>$91K</div>
              <div style={{fontSize:12,fontWeight:600,color:'#0d1424',marginBottom:8}}>Huang v. United States</div>
              <div style={{fontSize:11,color:'#556480',lineHeight:1.5}}>TurboTax told her foreign gifts don&apos;t need reporting. IRS assessed $91K in Form 3520 penalties. Court ruled TurboTax reliance may be reasonable cause.</div>
              <div style={{fontSize:10,color:'#8e9ab5',marginTop:6}}>N.D. California, Ongoing</div>
            </div>
          </div>
        </div>

        <div style={{textAlign:'center'}}>
          <p style={{fontSize:15,color:'#0d1424',fontWeight:600,maxWidth:420,margin:'0 auto 6px'}}>
            Guardian finds what your tax software missed.
          </p>
          <p style={{fontSize:13,color:'#556480',maxWidth:400,margin:'0 auto 20px',lineHeight:1.5}}>
            We check your documents, surface hidden risks, and tell you what to fix.
          </p>
          <button onClick={() => router.push("/check")} style={{padding:'14px 32px',borderRadius:12,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',color:'white',fontWeight:600,fontSize:15,border:'none',cursor:'pointer',boxShadow:'0 4px 16px rgba(74,116,212,0.3)'}}>
            Find my risks
          </button>
        </div>
      </section>

      {/* Integrations — chat (OpenClaw) + coding agents (MCP) */}
      <section id="integrations" ref={openclawSection.ref} className={`scroll-section${openclawSection.revealed ? ' revealed' : ''}`} style={{position:'relative',zIndex:1,padding:'64px 24px',maxWidth:960,margin:'0 auto'}}>
        <div style={{textAlign:'center',marginBottom:40}}>
          <div style={{display:'inline-flex',alignItems:'center',gap:8,padding:'6px 14px',borderRadius:20,background:'rgba(91,141,238,0.08)',border:'1px solid rgba(91,141,238,0.12)',marginBottom:16}}>
            <span style={{fontSize:11,fontWeight:600,color:'#5b8dee',letterSpacing:'0.04em'}}>INTEGRATIONS</span>
          </div>
          <h2 style={{fontSize:28,fontWeight:800,color:'#0d1424',letterSpacing:'-0.03em',marginBottom:8}}>
            Guardian, wherever you already work
          </h2>
          <p style={{fontSize:15,color:'#556480',maxWidth:560,margin:'0 auto',lineHeight:1.6}}>
            Ask Guardian questions from your chat apps, or connect it directly to your coding agent — same data room, same 23 tools, two surfaces.
          </p>
        </div>

        <div className="integrations-grid" style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20,marginBottom:24}}>
          {/* CHAT — OpenClaw */}
          <div style={{background:'rgba(255,255,255,0.55)',backdropFilter:'blur(18px)',borderRadius:20,padding:'28px',border:'1px solid rgba(255,255,255,0.7)',boxShadow:'0 4px 20px rgba(0,0,0,0.04)',display:'flex',flexDirection:'column'}}>
            <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:6}}>
              <div style={{width:28,height:28,borderRadius:8,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',display:'flex',alignItems:'center',justifyContent:'center',color:'white',fontSize:14,fontWeight:700}}>💬</div>
              <div style={{fontSize:10,fontWeight:700,color:'#5b8dee',letterSpacing:'0.1em'}}>CHAT · OPENCLAW</div>
            </div>
            <h3 style={{fontSize:20,fontWeight:800,color:'#0d1424',letterSpacing:'-0.02em',marginBottom:6}}>Compliance in your chat</h3>
            <p style={{fontSize:13,color:'#556480',lineHeight:1.6,marginBottom:16}}>
              WhatsApp, Telegram, Discord, Slack — any platform you already use via OpenClaw. Best for fast questions and alerts on the go.
            </p>
            <div style={{display:'flex',flexDirection:'column',gap:8,marginBottom:16,flex:1}}>
              {[
                '"Check my compliance status"',
                '"When are my deadlines?"',
                '"Do I need to file FBAR?"',
              ].map((q) => (
                <div key={q} style={{fontSize:12,color:'#3a5a8c',fontWeight:500,background:'rgba(91,141,238,0.06)',padding:'8px 12px',borderRadius:8}}>{q}</div>
              ))}
            </div>
            <div style={{fontSize:11,color:'#8b97ad',lineHeight:1.6,paddingTop:14,borderTop:'1px solid rgba(91,141,238,0.08)'}}>
              <code style={{background:'rgba(91,141,238,0.08)',padding:'2px 6px',borderRadius:4,fontSize:11,color:'#3a5a8c',fontWeight:500}}>openclaw skills install guardian-compliance</code>
              <br />
              then paste your Guardian token.
            </div>
          </div>

          {/* CODE — MCP */}
          <div style={{background:'rgba(255,255,255,0.55)',backdropFilter:'blur(18px)',borderRadius:20,padding:'28px',border:'1px solid rgba(255,255,255,0.7)',boxShadow:'0 4px 20px rgba(0,0,0,0.04)',display:'flex',flexDirection:'column'}}>
            <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:6}}>
              <div style={{width:28,height:28,borderRadius:8,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',display:'flex',alignItems:'center',justifyContent:'center',color:'white',fontSize:14,fontWeight:700}}>{'</>'}</div>
              <div style={{fontSize:10,fontWeight:700,color:'#5b8dee',letterSpacing:'0.1em'}}>CODE · MCP</div>
            </div>
            <h3 style={{fontSize:20,fontWeight:800,color:'#0d1424',letterSpacing:'-0.02em',marginBottom:6}}>Your coding agent, compliance-aware</h3>
            <p style={{fontSize:13,color:'#556480',lineHeight:1.6,marginBottom:16}}>
              Claude Code, Claude Desktop, Codex CLI — Guardian as 23 MCP tools right next to your editor. Best for document triage, case templates, form filing, and Gmail.
            </p>
            <div style={{display:'flex',flexDirection:'column',gap:8,marginBottom:16,flex:1}}>
              {[
                '"Check this folder against the H-1B template"',
                '"Generate my Form 8843"',
                '"Search Gmail for IRS notices"',
              ].map((q) => (
                <div key={q} style={{fontSize:12,color:'#3a5a8c',fontWeight:500,background:'rgba(91,141,238,0.06)',padding:'8px 12px',borderRadius:8}}>{q}</div>
              ))}
            </div>
            <div style={{fontSize:11,color:'#8b97ad',lineHeight:1.6,paddingTop:14,borderTop:'1px solid rgba(91,141,238,0.08)'}}>
              Paste to your agent:
              <br />
              <code style={{background:'rgba(91,141,238,0.08)',padding:'2px 6px',borderRadius:4,fontSize:11,color:'#3a5a8c',fontWeight:500,display:'inline-block',marginTop:2,wordBreak:'break-all'}}>Install Guardian MCP by following https://guardiancompliance.app/AGENTS.md</code>
            </div>
          </div>
        </div>

        {/* Unified setup CTA */}
        <div style={{background:'rgba(255,255,255,0.4)',backdropFilter:'blur(20px)',borderRadius:16,padding:'20px 24px',border:'1px solid rgba(255,255,255,0.5)',boxShadow:'0 4px 20px rgba(0,0,0,0.04)',display:'flex',alignItems:'center',justifyContent:'space-between',gap:16,flexWrap:'wrap'}}>
          <div>
            <div style={{fontSize:13,fontWeight:700,color:'#0d1424',marginBottom:4}}>Set up in 60 seconds</div>
            <div style={{fontSize:12,color:'#556480',lineHeight:1.5}}>Full install instructions for both surfaces, copy-paste config for every host, plus the one-line &quot;let your agent do it&quot; flow.</div>
          </div>
          <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
            <button onClick={() => router.push("/docs/install")} style={{padding:'10px 18px',borderRadius:10,background:'linear-gradient(135deg, #5b8dee, #4a74d4)',color:'white',fontWeight:600,fontSize:13,border:'none',cursor:'pointer',boxShadow:'0 2px 8px rgba(74,116,212,0.25)'}}>
              Read the docs
            </button>
            <button onClick={() => router.push("/connect")} style={{padding:'10px 18px',borderRadius:10,background:'rgba(255,255,255,0.7)',color:'#3a5a8c',fontWeight:600,fontSize:13,border:'1px solid rgba(91,141,238,0.2)',cursor:'pointer'}}>
              Get a token
            </button>
          </div>
        </div>
      </section>

      <footer style={{position:'relative',zIndex:1,padding:48,textAlign:'center',fontSize:13,color:'#8e9ab5',lineHeight:1.7}}>
        Your documents are stored securely and used only for compliance checking.<br />
        Start free — no account needed for your first check. Create an account to save your case.
      </footer>
    </>
  );
}
