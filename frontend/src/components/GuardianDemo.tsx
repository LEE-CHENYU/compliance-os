"use client";

/**
 * GuardianDemo — the looping "/guardian" command animation from
 * prototypes/guardian-command.html, ported to a self-contained client
 * component for the landing page.
 *
 * Faithful to the prototype: types `/guardian F-1 internship in 2 weeks`,
 * shows the slash menu, streams three agentic tool steps (search data room
 * -> validate source-of-truth -> assess CPT risk), then types a grounded
 * answer. Loops.
 *
 * Differences from the standalone prototype (so it blends into the page):
 *  - No full-page background; the landing already paints the blue gradient
 *    + dotted grid. Orbs are local (position:absolute) so the glass card
 *    still has colour to refract.
 *  - All CSS is scoped under `.gd-root` and keyframes are `gd-`-prefixed to
 *    avoid colliding with the landing's global styles.
 */

import { useEffect, useRef } from "react";

const SHIELD =
  '<svg viewBox="0 0 24 24" fill="none"><path d="M12 2.5 4.5 5.5v5.4c0 4.6 3.1 8 7.5 9.6 4.4-1.6 7.5-5 7.5-9.6V5.5L12 2.5Z" fill="#5b8dee" fill-opacity=".18" stroke="#5b8dee" stroke-width="1.5" stroke-linejoin="round"/><path d="m8.8 12 2.3 2.3 4.1-4.6" stroke="#4a74d4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const CHECK =
  '<svg viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="8" fill="#eaf1ff" stroke="#5b8dee" stroke-width="1.3"/><path d="m5.6 9 2.2 2.2 4.6-5" stroke="#4a74d4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';

const CSS = `
.gd-root{position:relative; overflow:hidden; border-radius:32px; padding:30px 0;
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:#0d1424}

/* floating colour orbs the glass card frosts over — gives the blur something to refract */
.gd-root .orb{position:absolute; border-radius:50%; z-index:0; pointer-events:none; filter:blur(54px); will-change:transform}
.gd-root .orb-1{width:340px; height:340px; left:2%;  top:4%;    background:radial-gradient(circle at 50% 50%, rgba(91,141,238,.5), transparent 68%);  animation:gd-float1 15s ease-in-out infinite}
.gd-root .orb-2{width:300px; height:300px; right:0%; bottom:2%; background:radial-gradient(circle at 50% 50%, rgba(108,154,230,.42), transparent 68%); animation:gd-float2 18s ease-in-out infinite}
.gd-root .orb-3{width:260px; height:260px; left:44%; top:54%;   background:radial-gradient(circle at 50% 50%, rgba(149,131,232,.3), transparent 70%);  animation:gd-float1 22s ease-in-out infinite reverse}
@keyframes gd-float1{0%,100%{transform:translate(0,0)}50%{transform:translate(20px,-22px)}}
@keyframes gd-float2{0%,100%{transform:translate(0,0)}50%{transform:translate(-22px,16px)}}

.gd-root .wrap{position:relative; z-index:1; width:100%; max-width:540px; margin:0 auto}
.gd-root .caption{text-align:center; margin:0 0 18px; font-size:13px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:rgba(50,90,170,.62)}

.gd-root .card{
  position:relative;
  background:linear-gradient(180deg, rgba(255,255,255,.6) 0%, rgba(244,248,253,.46) 100%);
  border:1px solid rgba(255,255,255,.55); border-radius:26px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.9),
    inset 0 0 0 1px rgba(255,255,255,.1),
    0 34px 60px -22px rgba(38,66,128,.34),
    0 14px 34px -14px rgba(38,66,128,.22),
    0 2px 6px rgba(18,38,78,.05);
  height:600px; display:flex; flex-direction:column;
  overflow:hidden; backdrop-filter:blur(30px) saturate(1.7); -webkit-backdrop-filter:blur(30px) saturate(1.7);
}
.gd-root .card::before{content:''; position:absolute; inset:0; z-index:0; pointer-events:none; border-radius:inherit;
  background:linear-gradient(125deg, rgba(255,255,255,.5) 0%, rgba(255,255,255,0) 30%, rgba(255,255,255,0) 68%, rgba(255,255,255,.2) 100%)}
/* The card is a fixed-height flex column; the transcript flexes to absorb any
   change (e.g. the status line toggling) so the card — and the content below
   it on the page — never moves across the loop. */
.gd-root .transcript{position:relative; z-index:1; padding:20px 20px 6px; flex:1 1 auto; min-height:0; overflow-y:auto; overflow-x:hidden; scrollbar-width:none; -ms-overflow-style:none; display:flex; flex-direction:column; gap:13px}
.gd-root .transcript::-webkit-scrollbar{display:none}

.gd-root .item{opacity:0; transform:translateY(7px); transition:opacity .35s ease, transform .35s ease}
.gd-root .item.in{opacity:1; transform:none}

.gd-root .user-chip{position:relative; align-self:flex-end; max-width:88%; font-size:14px; padding:9px 14px; border-radius:15px; border-bottom-right-radius:5px;
  background:linear-gradient(135deg,#5b8dee,#4a74d4); color:#fff; overflow:hidden;
  box-shadow:0 10px 22px -6px rgba(74,116,212,.5), inset 0 1px 0 rgba(255,255,255,.4)}
.gd-root .user-chip::after{content:''; position:absolute; inset:0 0 52% 0; background:linear-gradient(180deg,rgba(255,255,255,.22),transparent); pointer-events:none}
.gd-root .user-chip b{font-weight:600; opacity:.92; position:relative}

.gd-root .think{display:flex; align-items:center; gap:8px; font-size:13px; color:#7b8ba5; font-style:italic}
.gd-root .think .spark{font-style:normal; color:#5b8dee; animation:gd-tw 1.6s ease-in-out infinite}
@keyframes gd-tw{0%,100%{opacity:.45}50%{opacity:1}}

.gd-root .step{display:flex; gap:11px}
.gd-root .bullet{flex:0 0 18px; width:18px; height:18px; margin-top:1px; position:relative}
.gd-root .bullet .ring{position:absolute; inset:0; border-radius:50%; border:2px solid rgba(91,141,238,.25); border-top-color:#5b8dee; animation:gd-spin .7s linear infinite}
.gd-root .bullet .chk{position:absolute; inset:0; opacity:0; transition:opacity .2s; filter:drop-shadow(0 1px 2px rgba(40,70,130,.15))}
.gd-root .bullet.done .ring{display:none}
.gd-root .bullet.done .chk{opacity:1}
@keyframes gd-spin{to{transform:rotate(360deg)}}
.gd-root .step-body{flex:1; min-width:0}
.gd-root .step-action{font-size:13.5px; color:#0d1424; font-weight:500}
.gd-root .step-action .tool{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:11.5px; font-weight:600; color:#3d6bc5;
  background:rgba(255,255,255,.5); border:1px solid rgba(255,255,255,.65); padding:1px 7px; border-radius:6px; margin-left:7px; vertical-align:1px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8), 0 1px 3px rgba(40,70,130,.1); backdrop-filter:blur(6px)}
.gd-root .step-result{display:flex; gap:7px; margin-top:4px; font-size:12.5px; color:#556480; opacity:0; transform:translateY(-3px); transition:opacity .3s, transform .3s}
.gd-root .step-result.show{opacity:1; transform:none}
.gd-root .step-result .corner{color:#7b8ba5; flex:0 0 auto}
.gd-root .step-result.risk{color:#b07a1e}
.gd-root .step-result.risk .pill{background:linear-gradient(180deg,rgba(255,247,232,.72),rgba(252,240,214,.56)); border:1px solid rgba(176,122,30,.28);
  border-radius:8px; padding:3px 9px; font-weight:500; backdrop-filter:blur(6px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.65), 0 2px 9px rgba(176,122,30,.12)}

.gd-root .answer{display:flex; gap:11px; max-width:96%}
.gd-root .avatar{flex:0 0 28px; width:28px; height:28px; border-radius:9px; margin-top:1px;
  background:linear-gradient(135deg,rgba(234,241,255,.82),rgba(219,230,251,.6)); border:1px solid rgba(255,255,255,.7);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.9), 0 3px 8px -2px rgba(40,70,130,.18); display:flex; align-items:center; justify-content:center; backdrop-filter:blur(6px)}
.gd-root .avatar svg{width:15px; height:15px}
.gd-root .answer .bubble{background:linear-gradient(180deg,rgba(255,255,255,.64),rgba(255,255,255,.44)); border:1px solid rgba(255,255,255,.6);
  border-radius:16px; border-bottom-left-radius:5px; padding:12px 15px; font-size:14.5px; line-height:1.55; color:#0d1424;
  backdrop-filter:blur(12px) saturate(1.4); box-shadow:inset 0 1px 0 rgba(255,255,255,.8), 0 8px 22px -8px rgba(40,70,130,.22)}
.gd-root .answer .bubble .ask{color:#3d6bc5; font-weight:600}

.gd-root .footer{position:relative; z-index:1; border-top:1px solid rgba(255,255,255,.55);
  background:linear-gradient(180deg,rgba(255,255,255,.28),rgba(255,255,255,.46)); box-shadow:inset 0 1px 0 rgba(255,255,255,.6)}
/* status always reserves its height (only opacity animates) so the footer —
   and therefore the whole card — stays a constant height across the loop. */
.gd-root .status{display:flex; align-items:center; gap:9px; padding:11px 20px 0; font-size:12.5px; color:#556480; height:34px; opacity:0; overflow:hidden; transition:opacity .25s}
.gd-root .status.on{opacity:1}
.gd-root .status .dot{width:7px; height:7px; border-radius:50%; background:#5b8dee; box-shadow:0 0 8px rgba(91,141,238,.6); animation:gd-pp 1s ease-in-out infinite}
@keyframes gd-pp{0%,100%{opacity:.35; transform:scale(.8)}50%{opacity:1; transform:scale(1)}}
.gd-root .status .label{font-weight:500}

.gd-root .composer-area{position:relative; padding:14px 16px 16px}
.gd-root .slash-menu{position:absolute; left:16px; right:16px; bottom:calc(100% - 4px);
  background:rgba(255,255,255,.72); backdrop-filter:blur(26px) saturate(1.8); -webkit-backdrop-filter:blur(26px) saturate(1.8);
  border:1px solid rgba(255,255,255,.65); border-radius:14px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.85), 0 20px 54px -12px rgba(38,66,128,.32); padding:6px; opacity:0; transform:translateY(8px) scale(.98);
  transition:opacity .2s ease, transform .2s ease; pointer-events:none; transform-origin:bottom}
.gd-root .slash-menu.show{opacity:1; transform:none}
.gd-root .slash-head{font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#7b8ba5; padding:7px 9px 5px}
.gd-root .cmd{display:flex; align-items:center; gap:10px; padding:8px 9px; border-radius:10px; transition:opacity .2s}
.gd-root .cmd.dim{opacity:.4}
.gd-root .cmd.active{background:rgba(91,141,238,.13); box-shadow:inset 2px 0 0 #5b8dee, inset 0 1px 0 rgba(255,255,255,.5)}
.gd-root .cmd .ic{width:24px; height:24px; border-radius:7px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg,rgba(234,241,255,.85),rgba(219,230,251,.6)); border:1px solid rgba(255,255,255,.7); box-shadow:inset 0 1px 0 rgba(255,255,255,.9)}
.gd-root .cmd .ic svg{width:13px; height:13px}
.gd-root .cmd .name{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:12.5px; font-weight:600; color:#3d6bc5}
.gd-root .cmd .desc{font-size:11.5px; color:#556480; margin-left:auto}

.gd-root .composer{display:flex; align-items:center; gap:10px; border-radius:16px; padding:11px 11px 11px 15px;
  background:linear-gradient(180deg,rgba(255,255,255,.58),rgba(255,255,255,.42)); border:1px solid rgba(255,255,255,.6);
  backdrop-filter:blur(12px) saturate(1.5); -webkit-backdrop-filter:blur(12px) saturate(1.5);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8), 0 4px 16px -4px rgba(40,70,130,.14); transition:border-color .2s, box-shadow .2s}
.gd-root .composer.focus{border-color:rgba(91,141,238,.5);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.8), 0 0 0 4px rgba(91,141,238,.14), 0 6px 20px -4px rgba(40,70,130,.18)}
.gd-root .field{flex:1; font-size:15px; line-height:1.4; min-height:21px; white-space:pre-wrap; word-break:break-word}
.gd-root .field .ph{color:#7b8ba5}
.gd-root .field .cmd-token{color:#3d6bc5; font-weight:600}
.gd-root .caret{display:inline-block; width:2px; height:17px; background:#5b8dee; vertical-align:-3px; margin-left:1px; border-radius:1px; animation:gd-blink 1.05s step-end infinite}
@keyframes gd-blink{50%{opacity:0}}
.gd-root .send{flex:0 0 36px; width:36px; height:36px; border-radius:11px; border:none; background:rgba(91,141,238,.16); color:#9fb4dd;
  display:flex; align-items:center; justify-content:center; box-shadow:inset 0 1px 0 rgba(255,255,255,.45); transition:.2s}
.gd-root .send.on{background:linear-gradient(135deg,#5b8dee,#4a74d4); color:#fff; box-shadow:0 8px 20px -4px rgba(74,116,212,.5), inset 0 1px 0 rgba(255,255,255,.4)}
.gd-root .send.pulse{animation:gd-pulse .35s ease}
@keyframes gd-pulse{50%{transform:scale(.9)}}
.gd-root .send svg{width:17px; height:17px}

.gd-root .hint{text-align:center; margin:16px 0 0; font-size:12.5px; color:#7b8ba5}
.gd-root .hint b{color:#3d6bc5; font-weight:600}
`;

export default function GuardianDemo() {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const q = (s: string) => root.querySelector(s) as HTMLElement;

    const T = q("#gd-transcript"),
      typed = q("#gd-typed"),
      ph = q("#gd-ph"),
      caret = q("#gd-caret"),
      menu = q("#gd-menu"),
      composer = q("#gd-composer"),
      send = q("#gd-send"),
      other = q("#gd-cmd-other"),
      status = q("#gd-status"),
      statusLabel = q("#gd-status-label");

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const sleep = (ms: number) =>
      new Promise<void>((res, rej) => {
        if (cancelled) return rej();
        timer = setTimeout(res, ms);
      });

    const esc = (s: string) =>
      s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] as string));

    let value = "";
    function render() {
      const m = value.match(/^(\/\S*)([\s\S]*)$/);
      typed.innerHTML = m
        ? '<span class="cmd-token">' + esc(m[1]) + "</span>" + esc(m[2])
        : esc(value);
      ph.style.display = value ? "none" : "inline";
    }
    async function typeStr(str: string, sp: number) {
      for (const ch of str) {
        value += ch;
        render();
        await sleep(sp + Math.random() * 28);
      }
    }

    function add(cls: string, html: string) {
      const e = document.createElement("div");
      e.className = "item " + cls;
      e.innerHTML = html;
      T.appendChild(e);
      requestAnimationFrame(() => { e.classList.add("in"); T.scrollTop = T.scrollHeight; });
      T.scrollTop = T.scrollHeight;
      return e;
    }
    // keep the newest content (and the composer) in view; older items scroll up
    function scrollDown() { T.scrollTop = T.scrollHeight; }
    function setStatus(t: string) {
      statusLabel.textContent = t;
      status.classList.add("on");
    }
    function hideStatus() {
      status.classList.remove("on");
    }

    async function step(
      action: string,
      tool: string,
      result: string,
      opts: { risk?: boolean; work?: number; after?: number } = {}
    ) {
      const e = add(
        "step",
        '<span class="bullet"><span class="ring"></span><span class="chk">' +
          CHECK +
          "</span></span>" +
          '<div class="step-body"><div class="step-action">' +
          esc(action) +
          '<span class="tool">' +
          esc(tool) +
          "</span></div>" +
          '<div class="step-result' +
          (opts.risk ? " risk" : "") +
          '"><span class="corner">⎿</span>' +
          (opts.risk
            ? '<span class="pill">' + esc(result) + "</span>"
            : "<span>" + esc(result) + "</span>") +
          "</div></div>"
      );
      await sleep(opts.work || 780);
      e.querySelector(".bullet")!.classList.add("done");
      e.querySelector(".step-result")!.classList.add("show");
      scrollDown();
      await sleep(opts.after || 360);
    }

    function reset() {
      T.innerHTML = "";
      value = "";
      render();
      menu.classList.remove("show");
      other.style.display = "flex";
      composer.classList.remove("focus");
      send.classList.remove("on", "pulse");
      caret.style.display = "inline-block";
      hideStatus();
    }

    async function run() {
      try {
        while (!cancelled) {
          reset();
          await sleep(800);
          composer.classList.add("focus");
          await sleep(400);

          await typeStr("/", 70);
          menu.classList.add("show");
          await sleep(170);
          await typeStr("guardian", 64);
          other.style.display = "none";
          await sleep(520);
          await typeStr(" ", 90);
          menu.classList.remove("show");
          await sleep(130);
          await typeStr("F-1 internship in 2 weeks", 46);

          await sleep(560);
          send.classList.add("on");
          await sleep(430);
          send.classList.add("pulse");
          await sleep(170);
          caret.style.display = "none";
          add("user-chip", "<b>/guardian</b> F-1 internship in 2 weeks");
          value = "";
          render();
          composer.classList.remove("focus");
          send.classList.remove("on", "pulse");
          await sleep(520);

          add(
            "think",
            '<span class="spark">✦</span> Let me pull your documents and check this against the CPT rules before I answer.'
          );
          await sleep(900);

          setStatus("Searching your data room…");
          await step(
            "Searched your data room",
            "guardian_documents",
            "I-20 (current) · internship offer letter",
            { work: 820 }
          );

          setStatus("Validating against your facts…");
          await step(
            "Cross-checked your source-of-truth facts",
            "get_user_facts",
            "F-1 · started Aug 2024 · 2 terms done · DSO on file",
            { work: 880 }
          );

          setStatus("Assessing risk…");
          await step(
            "Ran the CPT eligibility & timing check",
            "run_compliance_check",
            "Risk: working before CPT is authorized = unauthorized employment",
            { risk: true, work: 900 }
          );

          setStatus("Writing…");
          await sleep(500);
          hideStatus();

          const a = add(
            "answer",
            '<span class="avatar">' + SHIELD + '</span><div class="bubble"></div>'
          );
          const bub = a.querySelector(".bubble") as HTMLElement;
          const ANSWER =
            "You're CPT-eligible — 2 terms done — so a paid internship is fine. The hard rule: no work before CPT is authorized on a new I-20. You start in 2 weeks, so email your DSO today. ";
          const ASK =
            "One fork so I route you right: someone else's company, or one you co-founded?";
          for (const ch of ANSWER) {
            bub.textContent += ch;
            scrollDown();
            await sleep(13);
          }
          const span = document.createElement("span");
          span.className = "ask";
          bub.appendChild(span);
          for (const ch of ASK) {
            span.textContent += ch;
            scrollDown();
            await sleep(13);
          }

          await sleep(4200);
        }
      } catch {
        /* cancelled — stop silently */
      }
    }
    run();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return (
    <div className="gd-root" ref={rootRef}>
      <style dangerouslySetInnerHTML={{ __html: CSS }} />
      <span className="orb orb-1" />
      <span className="orb orb-2" />
      <span className="orb orb-3" />
      <div className="wrap">
        <p className="caption">Start Guardian, on purpose</p>

        <div className="card">
          <div className="transcript" id="gd-transcript" />

          <div className="footer">
            <div className="status" id="gd-status">
              <span className="dot" />
              <span className="label" id="gd-status-label">
                Working…
              </span>
            </div>
            <div className="composer-area">
              <div className="slash-menu" id="gd-menu">
                <div className="slash-head">Commands</div>
                <div className="cmd active">
                  <span className="ic">
                    <svg viewBox="0 0 24 24" fill="none">
                      <path
                        d="M12 2.5 4.5 5.5v5.4c0 4.6 3.1 8 7.5 9.6 4.4-1.6 7.5-5 7.5-9.6V5.5L12 2.5Z"
                        fill="#5b8dee"
                        fillOpacity=".18"
                        stroke="#5b8dee"
                        strokeWidth="1.5"
                        strokeLinejoin="round"
                      />
                      <path
                        d="m8.8 12 2.3 2.3 4.1-4.6"
                        stroke="#4a74d4"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  <span className="name">/guardian</span>
                  <span className="desc">Start Guardian</span>
                </div>
                <div className="cmd dim" id="gd-cmd-other">
                  <span className="ic">
                    <svg viewBox="0 0 24 24" fill="none">
                      <rect x="4" y="4" width="16" height="16" rx="4" stroke="#7b8ba5" strokeWidth="1.5" />
                    </svg>
                  </span>
                  <span className="name">/clear</span>
                  <span className="desc">Clear conversation</span>
                </div>
              </div>
              <div className="composer" id="gd-composer">
                <div className="field" id="gd-field">
                  <span className="ph" id="gd-ph">
                    Message Guardian…
                  </span>
                  <span id="gd-typed" />
                  <span className="caret" id="gd-caret" />
                </div>
                <button className="send" id="gd-send" aria-label="Send">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path
                      d="M5 12h13M12 5l7 7-7 7"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <p className="hint">
          Type <b>/guardian</b> anytime — or <b>/guardian &lt;your situation&gt;</b> to route straight to
          your case.
        </p>
      </div>
    </div>
  );
}
