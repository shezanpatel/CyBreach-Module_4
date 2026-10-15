import { useState, useEffect, useCallback } from "react";
import { apiRequest } from "./api";

function CyBreachArena() {
/* ============================================================
   DESIGN TOKENS — single source of truth for all colours/sizes
   In a real project these would live in a theme file or
   Tailwind config. Here they're inline so everything is in
   one file you can hand to a teammate.
============================================================ */
const T = {
  bg: "#09181d",
  surface: "#441bfb51",
  surface2: "#2f78d6",
  surface3: "#700fa1b6",
  boxShadow: "0 10px 30px rgba(65,25,140,.30)",
  border: "rgba(255,255,255,.08)",
  neon: "#00E5FF",
  text: "#F5F7FA",
  muted: "#94A3B8",
  safe: "#22C55E",
  warning: "#F59E0B",
  danger: "#EF4444",
  fontDisplay: "'Cinzel', serif"
};

/* ============================================================
   GOOGLE FONTS injection — IBM Plex Mono + IBM Plex Sans
   Technical, enterprise-security feel.
============================================================ */
useEffect(() => {
  const fontLink = document.createElement("link");
  fontLink.href =
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Cinzel:wght@400;500;600;700;800&display=swap";
  fontLink.rel = "stylesheet";
  document.head.appendChild(fontLink);

  return () => {
    document.head.removeChild(fontLink);
  };
}, []);

/* ============================================================
   GLOBAL STYLES — injected once via a <style> tag.
   Keeps component JSX clean while letting us use keyframe
   animations that can't be done with inline styles.
============================================================ */
const globalCSS = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
  }
  body {
    background: ${T.bg};
    color: ${T.text};
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
  }
  /* CRT scanline — the signature element carried over from HTML version */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      0deg, transparent, transparent 2px,
      rgba(0,0,0,0.025) 2px, rgba(0,0,0,0.025) 4px
    );
    pointer-events: none;
    z-index: 9999;
  }
  @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.35} }
  @keyframes blink    { 0%,100%{opacity:1} 50%{opacity:.15} }
  @keyframes slideIn  { from{transform:translateX(110%);opacity:0} to{transform:translateX(0);opacity:1} }
  @keyframes fadeOut  { to{opacity:0;transform:translateX(110%)} }
  @keyframes flashBg  { 0%{background:rgba(0,229,255,.10)} 100%{background:${T.surface}} }
  @keyframes scanBar  { 0%{width:0%} 70%{width:82%} 100%{width:100%} }
  @keyframes countUp  { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
  @keyframes fadeIn   { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }

  /* ============================================================
     PARTICLE BACKGROUND — fixed canvas sits behind all content
  ============================================================ */
  .cba-particles {
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    pointer-events: none;
  }

  /* ============================================================
     SCROLL-REVEAL — elements start hidden/offset, then animate
     into place once they cross the viewport (via IntersectionObserver)
  ============================================================ */
  .cba-reveal {
    opacity: 0;
    transform: translateY(28px);
    transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1), transform 0.7s cubic-bezier(0.16,1,0.3,1);
    will-change: opacity, transform;
  }
  .cba-reveal-visible {
    opacity: 1;
    transform: translateY(0);
  }

  /* ============================================================
     BUTTON ANIMATION — shared hover-lift / press / sheen effect
     applied via className="cba-btn" on interactive buttons
  ============================================================ */
  .cba-btn {
    position: relative;
    overflow: hidden;
    transition: transform 0.2s cubic-bezier(0.16,1,0.3,1), box-shadow 0.25s ease, filter 0.2s ease, border-color 0.2s ease;
  }
  .cba-btn::before {
    content: '';
    position: absolute;
    top: 0; left: -75%;
    width: 50%; height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,0.25), transparent);
    transform: skewX(-20deg);
    transition: left 0.6s ease;
    pointer-events: none;
  }
  .cba-btn:hover::before { left: 130%; }
  .cba-btn:hover {
    transform: translateY(-2px);
    filter: brightness(1.08);
  }
  .cba-btn:active {
    transform: translateY(0) scale(0.96);
    filter: brightness(0.95);
  }

  /* Generic hover-lift for cards/panels that don't manage hover via JS */
  .cba-hover-lift {
    transition: transform 0.25s cubic-bezier(0.16,1,0.3,1), box-shadow 0.25s ease, border-color 0.25s ease;
  }
  .cba-hover-lift:hover {
    transform: translateY(-4px);
    border-color: rgba(0,229,255,0.35) !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.35);
  }

  ::-webkit-scrollbar { width:4px; }
  ::-webkit-scrollbar-track { background: ${T.bg}; }
  ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius:4px; }

  /* ============================================================
     RESPONSIVE BREAKPOINTS
     Inline styles set the desktop layout; these !important rules
     (which DO beat plain inline styles in the CSS cascade) collapse
     grids and the nav on narrower screens instead of letting fixed
     multi-column layouts force a horizontal overflow.
  ============================================================ */
  @media (max-width: 960px) {
    .cba-nav { padding: 10px 18px !important; }
    .cba-nav-inner { width: 100% !important; flex-wrap: wrap; gap: 8px; }
    .cba-nav-brand { font-size: 16px !important; white-space: nowrap; }
    .cba-nav-tabs {
      order: 3; flex: 0 0 100%; width: 100%;
      justify-content: space-between; gap: 0 !important;
      overflow: visible;
    }
    .cba-nav-tabs button { padding: 7px 8px !important; font-size: 11px !important; letter-spacing: 0.03em !important; }
    .cba-user-badge { gap: 8px !important; padding: 4px 8px !important; }
    .cba-user-avatar { width: 32px !important; height: 32px !important; }
    .cba-user-details div:nth-child(2) { display: none; }
    .cba-sign-out { padding: 7px 8px !important; font-size: 11px !important; }
    .cba-hero-grid { grid-template-columns: 1fr 1fr !important; }
    .cba-agents-grid { grid-template-columns: 1fr 1fr !important; }
    .cba-two-col { grid-template-columns: 1fr !important; }
    .cba-shield { display: none !important; }
  }
  @media (min-width: 961px) and (max-width: 1200px) {
    .cba-nav { padding: 10px 16px !important; }
    .cba-nav-inner { width: 100% !important; gap: 8px; }
    .cba-nav-brand { font-size: 15px !important; white-space: nowrap; }
    .cba-nav-tabs { flex: 1; min-width: 0; justify-content: center; gap: 0 !important; }
    .cba-nav-tabs button { padding: 6px 5px !important; font-size: 11px !important; letter-spacing: 0.02em !important; }
    .cba-user-badge { gap: 7px !important; padding: 4px 6px !important; }
    .cba-user-avatar { width: 32px !important; height: 32px !important; }
    .cba-user-details div:nth-child(2) { display: none; }
    .cba-sign-out { padding: 7px 8px !important; font-size: 11px !important; }
  }
  @media (max-width: 640px) {
    .cba-hero-grid { grid-template-columns: 1fr !important; }
    .cba-agents-grid { grid-template-columns: 1fr !important; }
    .cba-container { padding: 20px 16px !important; }
    .cba-nav { padding: 12px 16px !important; }
    .cba-nav-inner { flex-direction: column; align-items: flex-start !important; gap: 12px; }
    .cba-nav-tabs { width: 100%; justify-content: flex-start; overflow-x: auto; }
    .cba-nav-tabs button { flex: 0 0 auto; }
    .cba-plan-grid { grid-template-columns: 1fr 1fr !important; }
  }
`;

/* ============================================================
   DATA — static seed data for agents, leaderboard, badges.
   In production this would come from API calls.
============================================================ */
const AGENTS = [
  { id:"vuln",       icon:"🔍", name:"Vulnerability Scan",  cost:5,  desc:"Scans assets for known CVEs and misconfigurations." },
  { id:"malware",    icon:"🧬", name:"Malware Analysis",     cost:20, desc:"Deep analysis of suspicious files and processes." },
  { id:"threat",     icon:"🌐", name:"Threat Intelligence",  cost:25, desc:"Cross-references your environment with live threat feeds." },
  { id:"compliance", icon:"📋", name:"Compliance Audit",     cost:20, desc:"Maps controls against NIST, ISO 27001, PCI-DSS." },
];

const INITIAL_LEADERBOARD = [
  { rank:1, name:"SecureNet Labs", score:96, delta:+8  },
  { rank:2, name:"Apex Cyber",     score:91, delta:-2  },
  { rank:3, name:"Zeroday Corp",   score:88, delta:+3  },
  { rank:4, name:"Your Org",       score:74, delta:+4, isYou:true },
  { rank:5, name:"ByteShield",     score:71, delta:-1  },
];

const INITIAL_BADGES = [
  { id:"first",   icon:"🛡️", name:"First Detection", tier:"Bronze",   unlocked:true  },
  { id:"speed",   icon:"⚡", name:"Speed Runner",     tier:"Silver",   unlocked:true  },
  { id:"streak",  icon:"🔥", name:"7-Day Streak",     tier:"Gold",     unlocked:true  },
  { id:"hunter",  icon:"💎", name:"Threat Hunter",    tier:"Platinum", unlocked:false },
];

const INITIAL_ACTIVITY = [
  { icon:"◈", type:"credit", text:"+100 credits added via UPI top-up",           time:"2 HOURS AGO" },
  { icon:"✦", type:"badge",  text:"Gold badge earned — 7-Day Streak",            time:"YESTERDAY"   },
  { icon:"▷", type:"scan",   text:"Vulnerability Scan completed — 3 findings",   time:"2 DAYS AGO"  },
  { icon:"⚠", type:"alert",  text:"Low balance alert — credits below 50",        time:"4 DAYS AGO"  },
];

/* ============================================================
   UTILITY HOOKS
============================================================ */

function useAnimatedNumber(target, duration = 900) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = null;
    let rafId;

    const from = 0;
    function step(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (target - from) * eased));
      if (progress < 1) rafId = requestAnimationFrame(step);
    }

    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [target, duration]);
  return display;
}

function useToasts() {
  const [toasts, setToasts] = useState([]);
  const add = useCallback((msg, type = "info") => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  }, []);
  return { toasts, add };
}

/* ============================================================
   SCROLL-REVEAL HOOK + WRAPPER
   Uses IntersectionObserver to add a "visible" class the first
   time an element scrolls into view. Stays visible afterwards
   (no re-hiding on scroll-out) for a calmer feel.
============================================================ */
function Reveal({ children, delay = 0, style, as: Tag = "div" }) {
  const elRef = useState(() => ({ current: null }))[0];
  const [visible, setVisible] = useState(false);

  const setRef = useCallback((node) => {
    elRef.current = node;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -60px 0px" }
    );
    observer.observe(node);
  }, [elRef]);

  return (
    <Tag
      ref={setRef}
      className={`cba-reveal${visible ? " cba-reveal-visible" : ""}`}
      style={{ transitionDelay: `${delay}ms`, ...style }}
    >
      {children}
    </Tag>
  );
}

/* ============================================================
   PARTICLE BACKGROUND
   Lightweight canvas field of drifting nodes with connecting
   lines when close together — a subtle "network / security mesh"
   effect that sits fixed behind all page content.
============================================================ */
function ParticleField({ color = "#00E5FF", density = 70 }) {
  const setCanvasRef = useCallback((canvas) => {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width, height, particles, rafId;
    let alive = true;

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    }

    function makeParticles() {
      const count = Math.min(density, Math.floor((width * height) / 18000));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.6 + 0.6,
      }));
    }

    function tick() {
      if (!alive) return;
      ctx.clearRect(0, 0, width, height);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;
      }

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 130) {
            ctx.strokeStyle = color;
            ctx.globalAlpha = (1 - dist / 130) * 0.12;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      ctx.globalAlpha = 0.55;
      ctx.fillStyle = color;
      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      rafId = requestAnimationFrame(tick);
    }

    resize();
    makeParticles();
    tick();

    function onResize() { resize(); makeParticles(); }
    window.addEventListener("resize", onResize);

    canvas._cleanup = () => {
      alive = false;
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", onResize);
    };
  }, [color, density]);

  useEffect(() => {
    return () => {};
  }, []);

  return <canvas ref={setCanvasRef} className="cba-particles" />;
}

/* ============================================================
   SMALL REUSABLE COMPONENTS
============================================================ */

function Eyebrow({ children, color = T.neon }) {
  return (
    <div style={{
      fontFamily:"'IBM Plex Mono',monospace",
      fontSize:11, letterSpacing:"0.13em",
      textTransform:"uppercase", color, marginBottom:6
    }}>{children}</div>
  );
}

function Panel({ children, style, glow }) {
  return (
    <div style={{
      background: T.surface,
      border: `1px solid ${glow ? "rgba(0,229,255,0.25)" : T.border}`,
      borderRadius:8, padding:22,
      boxShadow: glow ? "0 0 24px rgba(0,229,255,0.12)" : "none",
      ...style,
    }}>{children}</div>
  );
}

function SectionHeader({ title, action, onAction }) {
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
      <div style={{ fontFamily:T.fontDisplay, fontSize:15, fontWeight:600, letterSpacing:"0.06em", textTransform:"uppercase" }}>
        {title}
      </div>
      {action && (
        <button onClick={onAction} style={{ background:"none", border:"none", color:T.neon, fontSize:13, cursor:"pointer", fontWeight:600 }}>
          {action} →
        </button>
      )}
    </div>
  );
}

function DeltaBadge({ value }) {
  const up = value >= 0;
  return (
    <span style={{
      fontFamily:"'IBM Plex Mono',monospace", fontSize:10,
      padding:"2px 6px", borderRadius:2,
      background: up ? "rgba(34,197,94,0.09)" : "rgba(239,68,68,0.09)",
      color: up ? T.safe : T.danger,
    }}>
      {up ? "▲" : "▼"} {Math.abs(value)}
    </span>
  );
}

function RunButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="cba-btn"
      style={{
        width:"100%", marginTop:12, padding:"9px 0",
        background:"transparent",
        border:"1px solid rgba(0,229,255,0.35)",
        color:T.neon,
        fontFamily:"'IBM Plex Mono',monospace", fontSize:11,
        letterSpacing:"0.1em", textTransform:"uppercase",
        borderRadius:8, cursor:"pointer",
        transition:"background 0.2s, border-color 0.2s",
      }}
      onMouseEnter={e => { e.target.style.background = "rgba(0,229,255,0.09)"; }}
      onMouseLeave={e => { e.target.style.background = "transparent"; }}
    >
      Run simulated scan
    </button>
  );
}

function AgentCard({ agent, onRun }) {
  const [hovered, setHovered] = useState(false);

  function handleRun() {
    onRun(agent);
  }

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
      background: T.surface3,
      border: `1px solid ${hovered ? T.neonDim : T.border}`,
      borderRadius:8, padding:20,
      boxShadow: hovered ? "0 10px 28px rgba(0,0,0,0.35)" : "none",
      transform: hovered ? "translateY(-3px)" : "translateY(0)",
      transition:"border-color 0.25s, box-shadow 0.25s, transform 0.25s",
      display:"flex", flexDirection:"column",
      animation:"fadeIn 0.35s ease",
    }}>
      <div style={{ height:2, background:T.border, borderRadius:2, marginBottom:16, transition:"background 0.3s" }} />

      <span style={{ fontSize:30, marginBottom:12 }}>{agent.icon}</span>

      <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:14, fontWeight:700, letterSpacing:"0.02em", marginBottom:5 }}>
        {agent.name}
      </div>
      <div style={{ fontSize:12.5, color:T.muted, lineHeight:1.55, flex:1, marginBottom:14 }}>
        {agent.desc}
      </div>

      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:16, fontWeight:700, color:T.neon }}>
          ◈ {agent.cost} CR
        </div>
        <span style={{
          fontFamily:"'IBM Plex Mono',monospace", fontSize:9,
          letterSpacing:"0.1em", padding:"3px 7px", borderRadius:2,
          background:"rgba(0,229,255,0.07)",
          color:T.neon,
          border:"1px solid rgba(0,229,255,0.2)",
        }}>
          DEMO
        </span>
      </div>

      <RunButton onClick={handleRun} />
    </div>
  );
}

function ToastStack({ toasts }) {
  return (
    <div style={{ position:"fixed", bottom:24, right:24, display:"flex", flexDirection:"column", gap:8, zIndex:300 }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background: T.surface,
          border:`1px solid ${t.type === "success" ? "rgba(34,197,94,0.3)" : "rgba(0,229,255,0.2)"}`,
          borderLeft:`3px solid ${t.type === "success" ? T.safe : T.neon}`,
          borderRadius:8, padding:"11px 16px",
          minWidth:280, fontSize:14,
          boxShadow:"0 8px 24px rgba(0,0,0,0.5)",
          animation:"slideIn 0.3s ease",
          color: T.text,
        }}>{t.msg}</div>
      ))}
    </div>
  );
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&":"&amp;",
    "<":"&lt;",
    ">":"&gt;",
    "\"":"&quot;",
    "'":"&#39;",
  })[character]);
}

function buildHtmlDocument(title, content) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    body{font:15px/1.5 Arial,sans-serif;color:#18212c;background:#f3f6f8;margin:0;padding:32px}
    main{max-width:820px;margin:0 auto;background:#fff;padding:44px;border:1px solid #d8e0e7;border-radius:12px}
    h1{font-size:26px;margin:6px 0 8px} h2{font-size:16px;margin:24px 0 8px}
    .eyebrow{font:700 11px/1.4 Arial,sans-serif;letter-spacing:.12em;color:#087e8b}
    .notice{padding:12px 14px;background:#fff8e8;border-left:3px solid #d58b00;margin:18px 0}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:20px 0}
    .muted{color:#637181;font-size:12px}.right{text-align:right}
    table{width:100%;border-collapse:collapse;margin:18px 0}
    th,td{text-align:left;padding:11px 8px;border-bottom:1px solid #d8e0e7}
    th:last-child,td:last-child{text-align:right}
    @media print{body{padding:0;background:#fff}main{border:0;border-radius:0;padding:0;max-width:none}}
    @media(max-width:600px){body{padding:10px}main{padding:22px}.grid{grid-template-columns:1fr}}
  </style>
</head>
<body><main>${content}</main></body></html>`;
}

function downloadHtmlFile(filename, title, content) {
  const html = buildHtmlDocument(title, content);
  const blob = new Blob([html], { type:"text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function demoReceiptHtmlContent(receipt) {
  const money = amount => `$${Number(amount).toFixed(2)}`;
  const rows = receipt.line_items.map(item => `
    <tr><td>${escapeHtml(item.description)}<div class="muted">${Number(item.credits).toLocaleString()} demo credits · quantity ${Number(item.quantity)}</div></td><td>${money(item.amount)}</td></tr>
  `).join("");
  const content = `
    <div class="eyebrow">CYBREACH ARENA · LOCAL DEMO</div>
    <h1>Payment receipt</h1>
    <div class="notice"><strong>SIMULATED · NO MONEY CHARGED.</strong> This is proof of a demo transaction only, not a tax invoice or evidence of a real payment.</div>
    <div class="grid">
      <div><div class="muted">RECEIPT NUMBER</div><strong>${escapeHtml(receipt.receipt_number)}</strong><div class="muted">${escapeHtml(new Date(receipt.issued_at).toLocaleString())}</div></div>
      <div><div class="muted">PAYMENT STATUS</div><strong>Approved (simulated)</strong><div class="muted">Reference: ${escapeHtml(receipt.payment.reference)}</div></div>
      <div><div class="muted">BILLED TO</div><strong>${escapeHtml(receipt.customer.name)}</strong><div>${escapeHtml(receipt.customer.email)}</div><div>${escapeHtml(receipt.customer.billing_address).replace(/\r?\n/g, "<br>")}</div></div>
      <div><div class="muted">PAYMENT METHOD</div><strong>${escapeHtml(receipt.payment.method_label)}</strong><div class="muted">Sandbox instrument; no real payment credentials used.</div></div>
    </div>
    <table><thead><tr><th>Description</th><th>Amount</th></tr></thead><tbody>${rows}</tbody></table>
    <table>
      <tbody>
        <tr><td>Subtotal</td><td>${money(receipt.subtotal)}</td></tr>
        <tr><td>Tax <span class="muted">(not calculated in demo)</span></td><td>${money(receipt.tax)}</td></tr>
        <tr><th>Total · ${escapeHtml(receipt.currency)}</th><th>${money(receipt.total)}</th></tr>
      </tbody>
    </table>
    <div class="muted">Credits added: ${Number(receipt.credits_added).toLocaleString()} CR. ${escapeHtml(receipt.notice)}</div>`;
  return content;
}

function downloadDemoReceipt(receipt) {
  downloadHtmlFile(
    `${receipt.receipt_number}.html`,
    `Receipt ${receipt.receipt_number}`,
    demoReceiptHtmlContent(receipt),
  );
}

function printDemoReceipt(receipt) {
  const printWindow = window.open("", "_blank", "popup,width=900,height=720");
  if (!printWindow) {
    downloadDemoReceipt(receipt);
    return;
  }

  const html = buildHtmlDocument(
    `Receipt ${receipt.receipt_number}`,
    demoReceiptHtmlContent(receipt),
  );
  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.requestAnimationFrame(() => {
    printWindow.requestAnimationFrame(() => {
      printWindow.focus();
      printWindow.print();
    });
  });
}

function demoReportData(engagement) {
  return {
    report_id:`REPORT-${engagement.id}`,
    generated_at:new Date().toISOString(),
    execution_source:"Pod Delta in-memory demo simulator",
    pod_beta_execution_invoked:false,
    demo_only:true,
    run:engagement,
  };
}

function downloadDemoReport(engagement) {
  const report = demoReportData(engagement);
  const rows = (engagement.results || []).map(item => `
    <tr><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.severity).toUpperCase()}</td><td>SIMULATED</td></tr>
  `).join("");
  const content = `
    <div class="eyebrow">CYBREACH ARENA · DEMO SECURITY REPORT</div>
    <h1>${escapeHtml(engagement.campaign_title)}</h1>
    <div class="notice"><strong>SIMULATED REPORT.</strong> Generated by the Pod Delta demo simulator. No targets were contacted, no security tests were executed, and Pod Beta's engagement runner was not invoked.</div>
    <div class="grid">
      <div><div class="muted">REPORT ID</div><strong>${escapeHtml(report.report_id)}</strong></div>
      <div><div class="muted">RUN STATUS</div><strong>${escapeHtml(engagement.status)}</strong></div>
      <div><div class="muted">CAMPAIGN</div><strong>${escapeHtml(engagement.campaign_title)}</strong><div class="muted">${escapeHtml(engagement.campaign_id)}</div></div>
      <div><div class="muted">COMPLETED</div><strong>${escapeHtml(new Date(engagement.completed_at).toLocaleString())}</strong></div>
    </div>
    <p><strong>Credit cost:</strong> ${Number(engagement.credit_cost)} CR &nbsp; <strong>Sample findings:</strong> ${Number(engagement.finding_count)}</p>
    <h2>Sample findings</h2>
    <table><thead><tr><th>Finding</th><th>Severity</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="muted">${escapeHtml(engagement.notice)}</p>`;
  downloadHtmlFile(`${report.report_id}.html`, `Security report ${engagement.campaign_title}`, content);
}

function downloadDemoReportJson(engagement) {
  const report = demoReportData(engagement);
  const blob = new Blob([JSON.stringify(report, null, 2)], { type:"application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${report.report_id}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function createCheckoutId() {
  return globalThis.crypto?.randomUUID?.()
    || `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function TopUpModal({ open, onClose, onPurchase, purchasing, receipt }) {
  const [packageId, setPackageId] = useState("operator");
  const [paymentMethod, setPaymentMethod] = useState("demo_card");
  const [step, setStep] = useState("details");
  const [checkoutId, setCheckoutId] = useState(createCheckoutId);
  const [customer, setCustomer] = useState({
    name:"Arena Demo Manager",
    email:"manager@cybreach.demo",
    billingAddress:"100 Demo Street, Example City",
  });

  useEffect(() => {
    if (open) {
      setStep(receipt ? "receipt" : "details");
      if (!receipt) setCheckoutId(createCheckoutId());
    }
  }, [open, receipt]);

  if (!open) return null;
  const packages = [
    ["starter", "Starter", 250, 4.99],
    ["operator", "Operator", 750, 9.99],
    ["enterprise", "Enterprise", 2000, 19.99],
  ];
  const selectedPackage = packages.find(([id]) => id === packageId) || packages[1];
  const inputStyle = {
    width:"100%", boxSizing:"border-box", padding:"11px 12px",
    background:T.bg, border:`1px solid ${T.border}`, color:T.text,
    borderRadius:8, font:"inherit",
  };
  const labelStyle = { display:"grid", gap:7, color:T.muted, fontSize:12 };
  const primaryButtonStyle = {
    width:"100%", padding:13, background:T.neon, color:"#000",
    fontFamily:"'IBM Plex Mono',monospace", fontSize:12, fontWeight:700,
    letterSpacing:"0.08em", textTransform:"uppercase", border:"none",
    borderRadius:8, cursor:purchasing ? "wait" : "pointer",
    opacity:purchasing ? .7 : 1,
  };
  const money = value => `$${Number(value).toFixed(2)}`;

  function close() {
    if (!purchasing) onClose();
  }

  function startNewCheckout() {
    setStep("details");
    setCheckoutId(createCheckoutId());
  }

  return (
    <div
      onClick={event => { if (event.target === event.currentTarget) close(); }}
      style={{
        position:"fixed", inset:0, background:"rgba(0,0,0,0.82)",
        backdropFilter:"blur(8px)", display:"flex", alignItems:"center",
        justifyContent:"center", zIndex:200, padding:16,
      }}
    >
      <div style={{
        background:T.surface, border:"1px solid rgba(0,229,255,0.2)",
        borderRadius:10, padding:28, width:"min(620px, 94vw)",
        maxHeight:"92vh", overflowY:"auto",
        boxShadow:"0 0 60px rgba(0,0,0,0.8), 0 0 24px rgba(0,229,255,0.08)",
        position:"relative", animation:"fadeIn 0.25s ease",
      }}>
        <button
          onClick={close}
          disabled={purchasing}
          aria-label="Close checkout"
          style={{ position:"absolute", top:14, right:14, background:"none", border:"none", color:T.muted, fontSize:18, cursor:"pointer" }}
        >✕</button>

        {step !== "receipt" ? (
          <>
            <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:18, fontWeight:700, color:T.neon, marginBottom:5 }}>
              ◈ Purchase credits
            </div>
            <div style={{ color:T.muted, fontSize:13, marginBottom:18 }}>
              Complete the billing details and review your simulated payment.
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:22 }}>
              {["1 · BILLING", "2 · PAYMENT", "3 · RECEIPT"].map((label, index) => {
                const active = (step === "details" && index === 0) || (step === "payment" && index === 1);
                return <div key={label} style={{ padding:"9px 5px", textAlign:"center", borderBottom:`2px solid ${active ? T.neon : T.border}`, color:active ? T.neon : T.muted, fontSize:10, letterSpacing:"0.04em" }}>{label}</div>;
              })}
            </div>
            {step === "details" ? (
              <form onSubmit={event => { event.preventDefault(); setStep("payment"); }}>
                <div style={{ display:"grid", gap:14, marginBottom:18 }}>
                  <label style={labelStyle}>
                    Full name
                    <input autoComplete="name" required minLength={2} maxLength={120} value={customer.name} onChange={event => setCustomer({ ...customer, name:event.target.value })} style={inputStyle} />
                  </label>
                  <label style={labelStyle}>
                    Billing email
                    <input type="email" autoComplete="email" required maxLength={254} value={customer.email} onChange={event => setCustomer({ ...customer, email:event.target.value })} style={inputStyle} />
                  </label>
                  <label style={labelStyle}>
                    Billing address
                    <textarea autoComplete="street-address" required minLength={5} maxLength={300} rows={2} value={customer.billingAddress} onChange={event => setCustomer({ ...customer, billingAddress:event.target.value })} style={{ ...inputStyle, resize:"vertical" }} />
                  </label>
                </div>
                <div style={{ color:T.muted, fontSize:11, marginBottom:16 }}>Receipt details are held only in this local demo session.</div>
                <button type="submit" className="cba-btn" style={primaryButtonStyle}>Continue to payment →</button>
              </form>
            ) : (
              <>
                <div style={{ padding:14, border:`1px solid ${T.border}`, borderRadius:8, marginBottom:16 }}>
                  <div style={{ color:T.muted, fontSize:10, letterSpacing:"0.08em", marginBottom:8 }}>ORDER SUMMARY</div>
                  <div style={{ display:"grid", gap:8, marginBottom:14 }}>
                    {packages.map(([id, label, credits, price]) => (
                      <button key={id} type="button" onClick={() => setPackageId(id)} aria-pressed={packageId === id} style={{
                        display:"flex", justifyContent:"space-between", padding:11, textAlign:"left",
                        color:T.text, background:packageId === id ? "rgba(0,229,255,.10)" : "transparent",
                        border:`1px solid ${packageId === id ? T.neon : T.border}`, borderRadius:8, cursor:"pointer",
                      }}>
                        <span>{label} · {credits.toLocaleString()} CR</span><strong>{money(price)}</strong>
                      </button>
                    ))}
                  </div>
                  <div style={{ display:"flex", justifyContent:"space-between", color:T.muted, fontSize:12 }}><span>Tax</span><span>$0.00 · not calculated in demo</span></div>
                  <div style={{ display:"flex", justifyContent:"space-between", marginTop:9, paddingTop:9, borderTop:`1px solid ${T.border}` }}><strong>Total</strong><strong style={{ color:T.neon }}>{money(selectedPackage[3])} DEMO</strong></div>
                </div>
                <div style={{ display:"grid", gap:9, marginBottom:16 }}>
                  <div style={{ color:T.muted, fontSize:11, letterSpacing:"0.08em" }}>SIMULATED PAYMENT INSTRUMENT</div>
                  {[
                    ["demo_card", "Demo card · ending 4242", "Sandbox instrument · no card number or CVV collected"],
                    ["demo_upi", "Demo UPI · demo@arena.test", "Sandbox UPI alias · no bank credentials requested"],
                  ].map(([method, title, subtitle]) => (
                    <label key={method} style={{ display:"flex", alignItems:"flex-start", gap:10, padding:12, border:`1px solid ${paymentMethod === method ? T.neon : T.border}`, borderRadius:8, cursor:"pointer" }}>
                      <input type="radio" name="demo-payment-method" value={method} checked={paymentMethod === method} onChange={() => setPaymentMethod(method)} />
                      <span><strong style={{ display:"block", color:T.text, fontSize:12 }}>{title}</strong><small style={{ color:T.muted }}>{subtitle}</small></span>
                    </label>
                  ))}
                </div>
                <div style={{ padding:12, color:T.warning, background:"rgba(245,158,11,.08)", borderLeft:`2px solid ${T.warning}`, marginBottom:16, fontSize:11, lineHeight:1.55 }}>
                  DEMO ONLY — these sandbox instruments always approve. No real payment is made, and no card or bank details are collected.
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 2fr", gap:10 }}>
                  <button type="button" disabled={purchasing} onClick={() => setStep("details")} className="cba-btn" style={{ ...primaryButtonStyle, background:"transparent", color:T.muted, border:`1px solid ${T.border}` }}>← Billing details</button>
                  <button type="button" disabled={purchasing} onClick={() => onPurchase(packageId, paymentMethod, customer, checkoutId)} className="cba-btn" style={primaryButtonStyle}>
                    {purchasing ? "PROCESSING SIMULATED PAYMENT…" : `Pay ${money(selectedPackage[3])} · add ${selectedPackage[2].toLocaleString()} CR`}
                  </button>
                </div>
              </>
            )}
          </>
        ) : receipt ? (
          <>
            <div style={{ color:T.text }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:16, paddingBottom:18, borderBottom:`1px solid ${T.border}` }}>
                <div>
                  <div style={{ color:T.neon, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, letterSpacing:"0.12em" }}>CYBREACH ARENA · DEMO</div>
                  <h2 style={{ margin:"8px 0 4px", fontSize:23 }}>Payment receipt</h2>
                  <div style={{ color:T.warning, fontSize:11, fontWeight:700 }}>SIMULATED · NO MONEY CHARGED</div>
                </div>
                <div style={{ textAlign:"right", fontSize:11, color:T.muted }}>
                  <div>Receipt</div><strong style={{ color:T.text }}>{receipt.receipt_number}</strong>
                  <div style={{ marginTop:7 }}>{new Date(receipt.issued_at).toLocaleString()}</div>
                </div>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:18, padding:"18px 0" }}>
                <div><div style={{ color:T.muted, fontSize:10, marginBottom:6 }}>BILLED TO</div><strong>{receipt.customer.name}</strong><div style={{ marginTop:4 }}>{receipt.customer.email}</div><div style={{ whiteSpace:"pre-line", marginTop:4 }}>{receipt.customer.billing_address}</div></div>
                <div><div style={{ color:T.muted, fontSize:10, marginBottom:6 }}>PAYMENT METHOD</div><strong>{receipt.payment.method_label}</strong><div style={{ marginTop:5, color:T.muted, fontSize:11 }}>Reference: {receipt.payment.reference}</div><div style={{ marginTop:5, color:T.muted, fontSize:11 }}>Status: Approved (simulated)</div></div>
              </div>
              <div style={{ borderTop:`1px solid ${T.border}`, borderBottom:`1px solid ${T.border}`, padding:"14px 0" }}>
                {receipt.line_items.map(item => <div key={item.description} style={{ display:"flex", justifyContent:"space-between", gap:12 }}><div><strong>{item.description}</strong><div style={{ color:T.muted, fontSize:11, marginTop:4 }}>{item.credits.toLocaleString()} demo credits · quantity {item.quantity}</div></div><strong>{money(item.amount)}</strong></div>)}
              </div>
              <div style={{ display:"grid", gap:7, maxWidth:280, margin:"14px 0 0 auto", fontSize:12 }}>
                <div style={{ display:"flex", justifyContent:"space-between" }}><span>Subtotal</span><span>{money(receipt.subtotal)}</span></div>
                <div style={{ display:"flex", justifyContent:"space-between", color:T.muted }}><span>Tax</span><span>{money(receipt.tax)} · not calculated</span></div>
                <div style={{ display:"flex", justifyContent:"space-between", paddingTop:8, borderTop:`1px solid ${T.border}`, fontSize:15 }}><strong>Total · USD</strong><strong>{money(receipt.total)}</strong></div>
              </div>
              <div style={{ marginTop:20, padding:12, border:`1px solid ${T.border}`, borderRadius:8, fontSize:11, lineHeight:1.6 }}>
                <strong>Demo proof of transaction.</strong> {receipt.notice} This receipt confirms a simulated purchase only and is not a tax invoice or proof of a real-world charge.
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginTop:18 }}>
                <button type="button" onClick={() => downloadDemoReceipt(receipt)} className="cba-btn" style={{ ...primaryButtonStyle, padding:"11px 8px", background:"transparent", color:T.neon, border:`1px solid ${T.neon}`, fontSize:10 }}>Download HTML receipt</button>
                <button type="button" onClick={() => printDemoReceipt(receipt)} className="cba-btn" style={{ ...primaryButtonStyle, padding:"11px 8px", background:"transparent", color:T.neon, border:`1px solid ${T.neon}`, fontSize:10 }}>Print / Save PDF</button>
                <button type="button" onClick={onClose} className="cba-btn" style={{ ...primaryButtonStyle, padding:"11px 8px", fontSize:10 }}>Done</button>
              </div>
              <button type="button" onClick={startNewCheckout} style={{ display:"block", margin:"14px auto 0", background:"none", border:0, color:T.muted, cursor:"pointer", fontSize:11 }}>Start another demo checkout</button>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function TransactionLog({ transactions }) {
  const [filter, setFilter] = useState("all");

  const types = ["all", "credit", "debit", "refund"];

  const colors = {
    credit: T.safe,
    debit: T.neon,
    refund: T.warning || "#F59E0B"
  };

  const icons = {
    credit: "⬇",
    debit: "⬆",
    refund: "↺"
  };

  const data =
    filter === "all"
      ? transactions
      : transactions.filter(t => t.type === filter);

  return (
    <Panel>
      <SectionHeader title="Transaction Log" />

      {/* Filters */}
      <div style={{ display: "flex", gap: 8, margin: "14px 0 18px" }}>
        {types.map(type => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            style={{
              padding: "6px 14px",
              borderRadius: 20,
              border: `1px solid ${filter === type ? colors[type] || T.neon : T.border}`,
              background: filter === type ? "rgba(0,229,255,.08)" : "transparent",
              color: filter === type ? colors[type] || T.neon : T.muted,
              font: "11px IBM Plex Mono",
              cursor: "pointer",
              textTransform: "uppercase"
            }}
          >
            {type}
          </button>
        ))}
      </div>

      {/* List */}
      {data.length ? data.map((tx, i) => (

        <div
          key={i}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "14px 16px",
            marginBottom: 10,
            border: `1px solid ${T.border}`,
            borderRadius: 10,
            background: "rgba(255,255,255,.02)",
            transition: ".2s"
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = colors[tx.type];
            e.currentTarget.style.transform = "translateX(4px)";
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = T.border;
            e.currentTarget.style.transform = "translateX(0)";
          }}
        >

          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>

            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                background: `${colors[tx.type]}22`,
                color: colors[tx.type],
                display: "grid",
                placeItems: "center",
                fontWeight: 700
              }}
            >
              {icons[tx.type]}
            </div>

            <div>
              <div style={{ fontWeight: 600 }}>{tx.desc}</div>
              <div
                style={{
                  font: "11px IBM Plex Mono",
                  color: T.muted,
                  marginTop: 3
                }}
              >
                {tx.time}
              </div>
            </div>

          </div>

          <div
            style={{
              font: "700 15px IBM Plex Mono",
              color: colors[tx.type]
            }}
          >
            {tx.type === "credit" ? "+" : "-"}{tx.amount} {tx.currency || "CR"}
          </div>

        </div>

      )) : (
        <div
          style={{
            padding: 30,
            textAlign: "center",
            color: T.muted
          }}
        >
          No Transactions Found
        </div>
      )}
    </Panel>
  );
}
function LeaderboardPanel({ entries }) {

  const rankStyle = (rank) => {
    switch(rank){
      case 1:
        return {
          bg:"linear-gradient(135deg,#FFD700,#F59E0B)",
          glow:"0 0 12px rgba(255,215,0,.45)"
        };
      case 2:
        return {
          bg:"linear-gradient(135deg,#E5E7EB,#94A3B8)",
          glow:"0 0 10px rgba(255,255,255,.25)"
        };
      case 3:
        return {
          bg:"linear-gradient(135deg,#CD7F32,#92400E)",
          glow:"0 0 10px rgba(205,127,50,.35)"
        };
      default:
        return {
          bg:"rgba(255,255,255,.05)",
          glow:"none"
        };
    }
  };

  const topScore = Math.max(...entries.map(e=>e.score));

  return (

    <Panel>

      <SectionHeader
        title="Global Leaderboard"
        action="View Full Ranking"
        onAction={()=>{}}
      />

      <div style={{
        display:"flex",
        flexDirection:"column",
        gap:14,
        marginTop:12
      }}>

      {entries.map((row,i)=>{

        const medal = row.rank===1 ? "🥇"
                    : row.rank===2 ? "🥈"
                    : row.rank===3 ? "🥉"
                    : "#"+row.rank;

        const pct = (row.score/topScore)*100;

        return(

        <div
          key={i}
          style={{
            display:"flex",
            alignItems:"center",
            gap:16,
            padding:"16px",
            border:`1px solid ${T.border}`,
            borderRadius:12,
            background:
              row.isYou
                ? "linear-gradient(90deg,rgba(0,229,255,.08),rgba(255,255,255,.02))"
                : "rgba(255,255,255,.02)",
            transition:"0.25s",
            cursor:"pointer",
          }}
          onMouseEnter={e=>{
            e.currentTarget.style.transform="translateX(6px)";
            e.currentTarget.style.borderColor=T.neon;
          }}
          onMouseLeave={e=>{
            e.currentTarget.style.transform="translateX(0)";
            e.currentTarget.style.borderColor=T.border;
          }}
        >

          {/* Rank */}

          <div
            style={{
              width:42,
              height:42,
              borderRadius:"50%",
              display:"flex",
              justifyContent:"center",
              alignItems:"center",
              background:rankStyle(row.rank).bg,
              boxShadow:rankStyle(row.rank).glow,
              fontSize:18
            }}
          >
            {medal}
          </div>

          {/* Avatar */}

          <div
            style={{
              width:42,
              height:42,
              borderRadius:"50%",
              background:"linear-gradient(135deg,#00E5FF,#2563EB)",
              display:"flex",
              alignItems:"center",
              justifyContent:"center",
              fontFamily:"IBM Plex Mono",
              fontWeight:700,
              color:"#000"
            }}
          >
            {row.name.charAt(0)}
          </div>

          {/* Name */}

          <div style={{flex:1}}>

            <div style={{
              display:"flex",
              alignItems:"center",
              gap:8
            }}>

              <span style={{
                fontWeight:600,
                color:T.text
              }}>
                {row.name}
              </span>

              {row.isYou && (

                <span style={{
                  background:T.neon,
                  color:"#000",
                  padding:"2px 7px",
                  borderRadius:20,
                  fontSize:10,
                  fontWeight:700,
                  fontFamily:"IBM Plex Mono"
                }}>
                  YOU
                </span>

              )}

            </div>

            <div
              style={{
                height:5,
                marginTop:8,
                borderRadius:20,
                overflow:"hidden",
                background:"rgba(255,255,255,.06)"
              }}
            >
              <div
                style={{
                  width:`${pct}%`,
                  height:"100%",
                  background:
                    row.rank===1
                    ? "#FFD700"
                    : T.neon
                }}
              />
            </div>

          </div>

          {/* Score */}

          <div
            style={{
              textAlign:"right",
              minWidth:90
            }}
          >

            <div style={{
              fontFamily:"IBM Plex Mono",
              fontSize:20,
              fontWeight:700,
              color:T.text
            }}>
              {row.score}
            </div>

            <div style={{
              color:
                row.delta>0
                ? T.safe
                : T.danger,
              fontFamily:"IBM Plex Mono",
              fontSize:12
            }}>
              {row.delta>0 ? "▲":"▼"} {Math.abs(row.delta)}
            </div>

          </div>

        </div>

        )

      })}

      </div>

    </Panel>

  );
}

function BadgesPanel({ badges }) {

  const tier = {
    Bronze: { color: "#CD7F32", glow: "rgba(205,127,50,.35)" },
    Silver: { color: "#C0C0C0", glow: "rgba(192,192,192,.35)" },
    Gold: { color: "#FACC15", glow: "rgba(250,204,21,.35)" },
    Platinum: { color: T.neon, glow: "rgba(0,229,255,.35)" }
  };

  return (
    <Panel>

      <SectionHeader
        title="Achievement Badges"
        action="View All →"
        onAction={() => {}}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
          gap: 16,
          marginTop: 14
        }}
      >

        {badges
          .filter(b => b.unlocked)
          .map((b, i) => {

            const c = tier[b.tier] || {
              color: T.muted,
              glow: "transparent"
            };

            return (

              <div
                key={b.id}
                style={{
                  position: "relative",
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: "18px",
                  borderRadius: 14,
                  background:
                    "linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.015))",
                  border: `1px solid ${T.border}`,
                  transition: ".25s",
                  animation: `fadeIn ${0.1 + i * 0.08}s ease`
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.borderColor = c.color;
                  e.currentTarget.style.boxShadow = `0 0 24px ${c.glow}`;
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.borderColor = T.border;
                  e.currentTarget.style.boxShadow = "none";
                }}
              >

                {/* Glow Circle */}

                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: "50%",
                    background: `${c.color}22`,
                    border: `2px solid ${c.color}`,
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    fontSize: 30,
                    boxShadow: `0 0 20px ${c.glow}`,
                    flexShrink: 0
                  }}
                >
                  {b.icon}
                </div>

                {/* Content */}

                <div style={{ flex: 1 }}>

                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 700,
                      color: T.text
                    }}
                  >
                    {b.name}
                  </div>

                  <div
                    style={{
                      marginTop: 5,
                      fontFamily: "'IBM Plex Mono', monospace",
                      fontSize: 11,
                      color: c.color,
                      letterSpacing: ".08em",
                      textTransform: "uppercase"
                    }}
                  >
                    {b.tier} Badge
                  </div>

                  <div
                    style={{
                      marginTop: 10,
                      height: 4,
                      borderRadius: 20,
                      background: "rgba(255,255,255,.05)"
                    }}
                  >
                    <div
                      style={{
                        width: "100%",
                        height: "100%",
                        borderRadius: 20,
                        background: c.color
                      }}
                    />
                  </div>

                </div>

                {/* Verified */}

                <div
                  style={{
                    position: "absolute",
                    top: 12,
                    right: 12,
                    fontSize: 10,
                    fontFamily: "'IBM Plex Mono', monospace",
                    color: T.safe,
                    letterSpacing: ".08em"
                  }}
                >
                  ● SAMPLE
                </div>

              </div>

            );

          })}

      </div>

    </Panel>
  );
}
function ActivityFeed({ items }) {

  const iconStyles = {
    credit: {
      bg: "linear-gradient(135deg,#00e5ff,#0099ff)",
      glow: "0 0 15px rgba(0,229,255,.35)"
    },
    badge: {
      bg: "linear-gradient(135deg,#22c55e,#16a34a)",
      glow: "0 0 15px rgba(34,197,94,.35)"
    },
    scan: {
      bg: "linear-gradient(135deg,#f59e0b,#d97706)",
      glow: "0 0 15px rgba(245,158,11,.35)"
    },
    alert: {
      bg: "linear-gradient(135deg,#ef4444,#dc2626)",
      glow: "0 0 15px rgba(239,68,68,.35)"
    }
  };

  return (
    <Panel glow>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 18
        }}
      >
        <SectionHeader title="Recent Activity" />

        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 18,
            background: "rgba(0,229,255,.08)",
            color: T.neon,
            padding: "4px 10px",
            borderRadius: 20,
            border: "1px solid rgba(0,229,255,.2)"
          }}
        >
          {items.length} EVENTS
        </div>

      </div>

      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column"
        }}
      >

        {/* Timeline */}

        <div
          style={{
            position: "absolute",
            left: 19,
            top: 10,
            bottom: 10,
            width: 2,
            background: "rgba(255,255,255,.05)"
          }}
        />

        {items.map((item, i) => {

          const style = iconStyles[item.type];

          return (

            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 16,
                padding: "15px 10px",
                borderRadius: 10,
                border:
                  i < items.length - 1
                    ? "1px solid rgba(255,255,255,.03)"
                    : "1px solid transparent",
                marginBottom: 6,
                transition: ".25s",
                animation: `fadeIn ${0.15 + i * .08}s ease`
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,.03)";
                e.currentTarget.style.transform = "translateX(5px)";
                e.currentTarget.style.border =
                  "1px solid rgba(0,229,255,.12)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.transform = "translateX(0px)";
                e.currentTarget.style.border =
                  i < items.length - 1
                    ? "1px solid rgba(255,255,255,.03)"
                    : "1px solid transparent";
              }}
            >

              {/* Icon */}

              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: "50%",
                  background: style.bg,
                  boxShadow: style.glow,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  color: "#fff",
                  fontSize: 20,
                  flexShrink: 0,
                  zIndex: 2
                }}
              >
                {item.icon}
              </div>

              {/* Text */}

              <div style={{ flex: 1 }}>

                <div
                  style={{
                    fontSize: 13,
                    color: T.text,
                    lineHeight: 1.6,
                    fontWeight: 500
                  }}
                >
                  {item.text}
                </div>

                <div
                  style={{
                    display: "inline-block",
                    marginTop: 8,
                    padding: "4px 8px",
                    borderRadius: 20,
                    background: "rgba(255, 255, 255, 0.12)",
                    color: T.muted,
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: 14,
                    letterSpacing: ".08em"
                  }}
                >
                  {item.time}
                </div>

              </div>

            </div>

          );

        })}

      </div>

    </Panel>
  );

}

function LoginScreen({ onLogin }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [accountId, setAccountId] = useState("manager@cybreach.demo");
  const [password, setPassword] = useState("ArenaDemo2026!");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin(accountId, password);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#0a0d12",
        position: "relative",
        overflow: "hidden"
      }}
    >
      <ParticleField color={T.neon} density={55} />

      {/* Grid Background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px)",
          backgroundSize: "40px 40px",
          opacity: .2
        }}
      />

      {/* Glowing Shield */}
      <div
        style={{
          position: "absolute",
          width: 450,
          height: 450,
          right: -80,
          top: -60,
          filter: "blur(6px)",
          opacity: .12
        }}
      >
        <svg viewBox="0 0 200 220">
          <path
            fill={T.neon}
            d="M100 8L182 36V105c0 52-35 87-82 108C53 192 18 157 18 105V36z"
          />
          <path
            d="M65 110l23 22 48-50"
            stroke="#fff"
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Login Card */}

      <div
        style={{
          width: 420,
          background: "rgba(17,22,29,.9)",
          backdropFilter: "blur(18px)",
          border: "1px solid rgba(0,229,255,.15)",
          borderRadius: 16,
          padding: 35,
          boxShadow:
            "0 0 40px rgba(0,229,255,.08),0 20px 60px rgba(0,0,0,.6)",
          zIndex: 2
        }}
      >

        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            margin: "0 auto 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,229,255,.08)",
            border: "1px solid rgba(0,229,255,.18)",
            boxShadow: "0 0 30px rgba(0,229,255,.2)",
            fontSize: 34
          }}
        >
          🛡️
        </div>

        <div
          style={{
            textAlign: "center",
            color: T.neon,
            fontSize: 30,
            fontWeight: 700,
            letterSpacing: "0.04em",
            fontFamily: T.fontDisplay
          }}
        >
          CYBREACH ARENA
        </div>

        <div
          style={{
            textAlign: "center",
            color: T.muted,
            marginTop: 10,
            marginBottom: 30,
            fontSize: 13
          }}
        >
          Local-only demo account · simulated activity
        </div>

        <form onSubmit={submit}>

          {error && (
            <div
              style={{
                marginTop: 12,
                color: "#ff6464",
                fontSize: 12
              }}
            >
              {error}
            </div>
          )}

          <label style={{ display:"grid", gap:7, marginTop:18, color:T.muted, fontSize:12 }}>
            Demo account ID
            <input
              autoComplete="username"
              value={accountId}
              onChange={event => setAccountId(event.target.value)}
              style={{ padding:12, border:`1px solid ${T.border}`, borderRadius:8, background:T.bg, color:T.text }}
            />
          </label>
          <label style={{ display:"grid", gap:7, marginTop:14, color:T.muted, fontSize:12 }}>
            Demo password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              style={{ padding:12, border:`1px solid ${T.border}`, borderRadius:8, background:T.bg, color:T.text }}
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="cba-btn"
            style={{
              width: "100%",
              marginTop: 20,
              padding: 14,
              border: 0,
              borderRadius: 10,
              cursor: loading ? "wait" : "pointer",
              opacity: loading ? 0.75 : 1,
              background:"linear-gradient(90deg,#00e5ff,#00b7d4)",
              color:"#001318",
              fontWeight:700,
              letterSpacing:".12em",
              fontFamily:"'IBM Plex Mono',monospace",
              boxShadow:"0 0 25px rgba(0,229,255,.25)"
            }}
          >
            {loading ? "SIGNING IN..." : "SIGN IN TO DEMO ARENA"}
          </button>

        </form>

        <div
          style={{
            marginTop:18,
            padding:12,
            border:"1px solid rgba(0,229,255,.15)",
            borderRadius:8,
            color:T.muted,
            fontSize:11,
            lineHeight:1.7,
            fontFamily:"'IBM Plex Mono',monospace"
          }}
        >
          DEMO CREDENTIALS<br />
          ID: <strong style={{ color:T.neon }}>manager@cybreach.demo</strong><br />
          Password: <strong style={{ color:T.neon }}>ArenaDemo2026!</strong><br />
          Local demo only · no real account or payment
        </div>

      </div>

    </div>
  );
}
function CampaignLibrary({ campaigns, error }) {
  if (error) {
    return <Panel><SectionHeader title="Campaign Library" /><p style={{ color:T.warn }}>{error}</p></Panel>;
  }
  if (!campaigns?.length) {
    return <Panel><SectionHeader title="Campaign Library" /><p style={{ color:T.muted }}>No campaigns returned by Pod Beta.</p></Panel>;
  }
  return (
    <Panel>
      <SectionHeader title="Campaign Library" action={`${campaigns.length} FROM POD BETA`} />
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))", gap:12 }}>
        {campaigns.map(campaign => (
          <div key={campaign.campaign_id} style={{ padding:16, border:`1px solid ${T.border}`, borderRadius:10, background:"rgba(255,255,255,.02)" }}>
            <div style={{ color:T.neon, font:"11px 'IBM Plex Mono',monospace", textTransform:"uppercase" }}>{campaign.tier}</div>
            <h3 style={{ marginTop:8, fontSize:16 }}>{campaign.title}</h3>
            <p style={{ marginTop:8, color:T.muted, lineHeight:1.5 }}>{campaign.description}</p>
            <div style={{ marginTop:12, color:T.text, font:"12px 'IBM Plex Mono',monospace" }}>
              {campaign.credit_cost} credits · {(campaign.regions || []).join(", ")}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function BenchmarkPanel({ token }) {
  const [cohorts, setCohorts] = useState([]);
  const [minimumPeerCount, setMinimumPeerCount] = useState(null);
  const [cohort, setCohort] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cohortsLoading, setCohortsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setCohortsLoading(true);
    setError("");
    apiRequest("/api/v1/arena/benchmark/cohorts", { token })
      .then(response => {
        if (!active) return;
        setCohorts(response.cohorts || []);
        setMinimumPeerCount(response.minimum_peer_count);
        setCohort(current => (
          current && response.cohorts?.some(item =>
            item.industry === current.industry
            && item.region === current.region
            && item.size_band === current.size_band
          )
            ? current
            : response.cohorts?.[0] || null
        ));
      })
      .catch(requestError => {
        if (active) setError(`Could not load supported peer cohorts: ${requestError.message}`);
      })
      .finally(() => {
        if (active) setCohortsLoading(false);
      });
    return () => { active = false; };
  }, [token]);

  async function compare(event) {
    event.preventDefault();
    if (!cohort) return;
    setError("");
    setLoading(true);
    try {
      setResult(await apiRequest("/api/v1/arena/benchmark", {
        token, method:"POST", body:cohort,
      }));
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  const industries = [...new Set(cohorts.map(item => item.industry))];
  const regions = [...new Set(cohorts.filter(item => item.industry === cohort?.industry).map(item => item.region))];
  const sizeBands = [...new Set(cohorts.filter(item => item.industry === cohort?.industry && item.region === cohort?.region).map(item => item.size_band))];

  function updateCohort(field, value) {
    setResult(null);
    setError("");
    if (field === "industry") {
      const matching = cohorts.filter(item => item.industry === value);
      if (matching.length) setCohort({ industry:value, region:matching[0].region, size_band:matching[0].size_band });
      return;
    }
    if (field === "region") {
      const matching = cohorts.filter(item => item.industry === cohort?.industry && item.region === value);
      if (matching.length) setCohort({ ...cohort, region:value, size_band:matching[0].size_band });
      return;
    }
    const matching = cohorts.find(item => item.industry === cohort?.industry && item.region === cohort?.region && item.size_band === value);
    if (matching) setCohort({ ...cohort, size_band:value });
  }

  const fieldStyle = { padding:10, background:T.bg, border:`1px solid ${T.border}`, color:T.text, borderRadius:8 };
  return (
    <Panel>
      <SectionHeader title="Synthetic Benchmark" action="POD GAMMA" />
      <p style={{ color:T.muted, marginBottom:16 }}>Choose a seeded synthetic cohort from Pod Gamma. These demo figures are not based on real organizations or private peer data.</p>
      <form onSubmit={compare} style={{ display:"flex", flexWrap:"wrap", gap:10, marginBottom:18 }}>
        {[
          ["industry", industries],
          ["region", regions],
          ["size_band", sizeBands],
        ].map(([key, values]) => (
          <label key={key} style={{ display:"grid", gap:5, color:T.muted, fontSize:11, textTransform:"uppercase" }}>
            {key.replace("_"," ")}
            <select
              value={cohort?.[key] || ""}
              onChange={event => updateCohort(key, event.target.value)}
              disabled={cohortsLoading || values.length === 0}
              style={fieldStyle}
            >
              {values.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
        ))}
        <button className="cba-btn" type="submit" disabled={loading || cohortsLoading || !cohort} style={{ alignSelf:"end", padding:"10px 16px", background:T.neon, border:0, borderRadius:8, color:"#001318", fontWeight:700, cursor:"pointer", opacity:loading || cohortsLoading || !cohort ? .65 : 1 }}>
          {cohortsLoading ? "Loading cohorts…" : loading ? "Comparing…" : "Compare cohort"}
        </button>
      </form>
      {!cohortsLoading && cohorts.length > 0 && (
        <p style={{ color:T.muted, fontSize:11, marginBottom:12 }}>
          {cohorts.length} seeded cohorts · minimum {minimumPeerCount} peers · synthetic demo data only
        </p>
      )}
      {error && <p role="alert" style={{ color:T.warn }}>{error}</p>}
      {!cohortsLoading && !error && cohorts.length === 0 && <p role="status" style={{ color:T.muted }}>Pod Gamma returned no cohorts that meet the minimum peer threshold.</p>}
      {result && (
        <div style={{ padding:14, border:`1px solid ${T.border}`, borderRadius:8 }}>
          {result.label && <div style={{ color:T.warn, font:"11px 'IBM Plex Mono',monospace", textTransform:"uppercase" }}>{result.label}</div>}
          <div style={{ display:"flex", flexWrap:"wrap", gap:24, marginTop:10 }}>
            <span>Peer group: <strong>{result.peer_count}</strong></span>
            <span>Median: <strong>{result.peer_median}</strong></span>
            <span>25th–75th: <strong>{result.peer_25th}–{result.peer_75th}</strong></span>
          </div>
        </div>
      )}
    </Panel>
  );
}

function ConnectionsPanel({ connections, loading, refresh }) {
  return (
    <Panel>
      <SectionHeader title="Pod Connectivity" action={loading ? "CHECKING…" : "REFRESH"} onAction={refresh} />
      <p style={{ color:T.muted, marginBottom:14 }}>Browser requests are routed through Pod Delta. Service URLs and credentials are not exposed to the browser.</p>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))", gap:10 }}>
        {(connections ? [connections.pod_delta, ...connections.upstreams] : []).map(item => (
          <div key={item.service} style={{ display:"flex", justifyContent:"space-between", padding:12, border:`1px solid ${T.border}`, borderRadius:8 }}>
            <span>{item.service.replaceAll("_"," ")}</span>
            <strong style={{ color:item.status === "healthy" ? T.safe : T.warn }}>{item.status}</strong>
          </div>
        ))}
      </div>
      {connections?.mode === "development_demo" && (
        <p style={{ marginTop:14, color:T.warn, fontSize:12 }}>Development-only identity. Do not use this mode in production.</p>
      )}
      {!connections && !loading && <p style={{ color:T.warn }}>No connection status received yet.</p>}
    </Panel>
  );
}

function RecommendationsPanel({ data, error }) {
  if (error) return <Panel><SectionHeader title="Engagement Recommendations" /><p style={{ color:T.warn }}>{error}</p></Panel>;
  if (!data) return <Panel><SectionHeader title="Engagement Recommendations" /><p style={{ color:T.muted }}>No recommendation response received from Pod Beta.</p></Panel>;
  return (
    <Panel style={{ marginTop:16 }}>
      <SectionHeader title="Engagement Recommendations" action="POD BETA" />
      <p style={{ color:T.muted, marginBottom:12 }}>{data.unresolved_gap_count} unresolved validated gaps</p>
      {data.guidance_notice && <p style={{ color:T.muted, fontSize:12, marginBottom:12 }}>{data.guidance_notice}</p>}
      {(data.recommendations || []).map((item, index) => (
        <div key={`${item.campaign_id}-${index}`} style={{ padding:"12px 0", borderTop:`1px solid ${T.border}` }}>
          <strong>{item.title}</strong>
          <div style={{ marginTop:5, color:T.muted, fontSize:12 }}>{item.reason} · {item.credit_cost} credits</div>
        </div>
      ))}
    </Panel>
  );
}

function NotificationsPanel({ notifications, preferences, error, demoMode }) {
  if (error) return <Panel><SectionHeader title="Notifications" /><p style={{ color:T.warn }}>{error}</p></Panel>;
  const items = notifications?.notifications || [];
  return (
    <Panel>
      <SectionHeader title="Arena Notifications" action={demoMode ? "SIMULATED DEMO EVENTS" : `${notifications?.total ?? 0} EVENTS`} />
      {demoMode && (
        <p style={{ color:T.warning, marginBottom:12 }}>
          Demo events are generated by simulated top-ups and scans. No email or external notification is sent.
        </p>
      )}
      {preferences && (
        <p style={{ color:T.muted, fontSize:12, marginBottom:12 }}>
          Preferences · email {preferences.email_enabled ? "on" : "off"} · in-app {preferences.in_app_enabled ? "on" : "off"} · frequency {preferences.frequency}
        </p>
      )}
      {items.map(item => (
        <div key={item.id} style={{ padding:"12px 0", borderTop:`1px solid ${T.border}` }}>
          <strong>{item.title}</strong>
          <div style={{ color:T.muted, marginTop:5 }}>{item.message}</div>
          <div style={{ color:T.muted, marginTop:5, fontSize:11 }}>{item.channel} · {item.status} · {item.created_at}</div>
        </div>
      ))}
      {!items.length && <p style={{ color:T.muted }}>No notifications have been generated yet.</p>}
    </Panel>
  );
}

function AnalyticsPanel({ data, error }) {
  if (error) return <Panel><SectionHeader title="Tenant Analytics" /><p style={{ color:T.warn }}>{error}</p></Panel>;
  if (!data) return <Panel><SectionHeader title="Tenant Analytics" /><p style={{ color:T.muted }}>No analytics response received from Pod Delta.</p></Panel>;
  const fields = [
    ["Resilience score", data.resilience_score],
    ["Active users", `${data.active_users}/${data.total_users}`],
    ["Visits", data.total_visits],
    ["Uptime", `${data.uptime_percentage}%`],
    ["Errors", data.error_count],
  ];
  return (
    <Panel>
      <SectionHeader title={`Tenant Analytics · ${data.tenant_name}`} action={data.source === "simulated_demo" ? "SIMULATED DEMO DATA" : "POD DELTA"} />
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:12 }}>
        {fields.map(([label, value]) => (
          <div key={label} style={{ padding:14, border:`1px solid ${T.border}`, borderRadius:8 }}>
            <div style={{ color:T.muted, fontSize:11 }}>{label}</div>
            <strong style={{ display:"block", marginTop:8, fontSize:20 }}>{value}</strong>
          </div>
        ))}
      </div>
      {data.source === "simulated_demo" && (
        <p style={{ color:T.warning, fontSize:11, marginTop:14 }}>
          These metrics are generated for the demo account and are not production analytics.
        </p>
      )}
    </Panel>
  );
}

function DashboardOverview({ connections, campaigns, leaderboard, leaderboardConnected, demoIdentity, walletData, analytics, onNavigate }) {
  const services = connections
    ? [connections.pod_delta, ...connections.upstreams]
    : [];
  const healthyServices = services.filter(service => service.status === "healthy").length;
  const cards = [
    {
      label:"Connected services",
      value:services.length ? `${healthyServices}/${services.length}` : "Checking",
      detail:"Pod Delta gateway health",
      color:healthyServices === services.length && services.length ? T.safe : T.warning,
    },
    {
      label:"Campaign catalog",
      value:campaigns.length,
      detail:"Definitions from Pod Beta",
      color:T.neon,
    },
    {
      label:"Leaderboard",
      value:leaderboardConnected ? leaderboard.length : "Unavailable",
      detail:"Entries from Pod Gamma",
      color:leaderboardConnected ? T.neon : T.warning,
    },
    {
      label:demoIdentity ? "Demo wallet" : "Account data",
      value:demoIdentity ? `${walletData?.available_balance ?? "…"} CR` : "Account session",
      detail:demoIdentity ? `${analytics?.total_engagements ?? 0} simulated scans completed` : "Wallet and personal records",
      color:T.muted,
    },
  ];

  return (
    <>
      <Panel style={{ marginBottom:16, padding:24 }}>
        <Eyebrow>{demoIdentity ? "Local demo account · all transactions are simulated" : "Authenticated account"}</Eyebrow>
        <h2 style={{ fontFamily:T.fontDisplay, fontSize:28, margin:"8px 0" }}>
          Welcome to your Arena dashboard
        </h2>
        <p style={{ color:T.muted, margin:0, lineHeight:1.6 }}>
          Monitor connected pods, explore campaign and leaderboard data, and try a fully simulated wallet and scan workflow.
          {demoIdentity && " Demo payments never charge money and scan simulations never contact targets."}
        </p>
      </Panel>

      <div className="cba-hero-grid" style={{ display:"grid", gridTemplateColumns:"repeat(4,minmax(0,1fr))", gap:12, marginBottom:18 }}>
        {cards.map(card => (
          <Panel key={card.label}>
            <Eyebrow>{card.label}</Eyebrow>
            <strong style={{ display:"block", marginTop:10, color:card.color, font:"700 26px 'IBM Plex Mono',monospace" }}>
              {card.value}
            </strong>
            <span style={{ display:"block", marginTop:6, color:T.muted, fontSize:12 }}>{card.detail}</span>
          </Panel>
        ))}
      </div>

      <div className="cba-two-col" style={{ display:"grid", gridTemplateColumns:"1.15fr .85fr", gap:14 }}>
        <Panel>
          <SectionHeader title="Service status" action="View details" onAction={() => onNavigate("Services")} />
          {services.map(service => (
            <div key={service.service} style={{ display:"flex", justifyContent:"space-between", gap:12, padding:"11px 0", borderTop:`1px solid ${T.border}` }}>
              <span style={{ color:T.text }}>{service.service.replaceAll("_"," ")}</span>
              <strong style={{ color:service.status === "healthy" ? T.safe : T.warning, textTransform:"uppercase", fontSize:11 }}>
                {service.status}
              </strong>
            </div>
          ))}
          {!services.length && <p style={{ color:T.muted }}>Checking connected services...</p>}
        </Panel>

        <Panel>
          <SectionHeader title="Explore the Arena" />
          <div style={{ display:"grid", gap:9 }}>
            {[
              ["Campaigns","Browse Pod Beta campaign definitions"],
              ["Leaderboard","View Pod Gamma rankings"],
              ["Benchmark","Compare a seeded synthetic cohort"],
            ].map(([tab, description]) => (
              <button
                key={tab}
                onClick={() => onNavigate(tab)}
                style={{ display:"flex", justifyContent:"space-between", gap:12, alignItems:"center", textAlign:"left", padding:12, color:T.text, background:"rgba(255,255,255,.03)", border:`1px solid ${T.border}`, borderRadius:8, cursor:"pointer" }}
              >
                <span>
                  <strong style={{ display:"block" }}>{tab}</strong>
                  <small style={{ color:T.muted }}>{description}</small>
                </span>
                <span style={{ color:T.neon }}>→</span>
              </button>
            ))}
          </div>
          {demoIdentity && (
            <p style={{ color:T.muted, fontSize:12, lineHeight:1.6, margin:"14px 0 0" }}>
              Wallet, scan findings, notifications, and analytics here are sample data for this demo account only.
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}

function Nav({ activeTab, setActiveTab, demoIdentity, onLogout }) {
  const tabs = ["Dashboard","Campaigns","Leaderboard","Benchmark","Wallet","Notifications","Analytics","Services"];
  return (
    <nav className="cba-nav" style={{
      display:"flex", alignItems:"center", justifyContent:"center",
      padding:"14px 32px",
      borderBottom:`1px solid ${T.border}`,
      background:"rgba(13,13,14,0.95)",
      backdropFilter:"blur(12px)",
      position:"sticky", top:0, zIndex:100,
    }}>
      <div className="cba-nav-inner" style={{ width:"98%", maxWidth:1600, display:"flex", alignItems:"center", justifyContent:"space-between" }}>
      <div className="cba-nav-brand" style={{ fontFamily:T.fontDisplay, fontSize:19, fontWeight:700, color:T.neon, letterSpacing:"0.04em", display:"flex", alignItems:"center", gap:8 }}>
        <span style={{ animation:"pulse 2s ease-in-out infinite", display:"inline-block" }}>◈</span>
        CYBREACH ARENA
      </div>

      <div className="cba-nav-tabs" style={{ display:"flex", gap:4 }}>
        {tabs.map(t => (
          <button
            key={t}
            className="cba-nav-tab"
            onClick={() => setActiveTab(t)}
            style={{
              background:"none", border:"none",
              color: activeTab===t ? T.neon : T.muted,
              fontFamily:"'IBM Plex Sans',sans-serif",
              fontSize:14, fontWeight: activeTab===t ? 700 : 500,
              letterSpacing:"0.06em",
              padding:"6px 14px",
              cursor:"pointer",
              borderBottom: activeTab===t ? `2px solid ${T.neon}` : "2px solid transparent",
              transition:"color 0.2s, border-color 0.2s",
              textTransform:"uppercase",
            }}
          >{t}</button>
        ))}
      </div>

      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <div
  className="cba-user-badge"
  style={{
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "6px 10px",
    border: `1px solid ${T.border}`,
    borderRadius: 10,
    background: "rgba(255,255,255,0.03)",
    transition: "all .2s ease",
  }}
>
  {/* Avatar */}
  <div
    className="cba-user-avatar"
    style={{
      width: 38,
      height: 38,
      borderRadius: "50%",
      background: `linear-gradient(135deg, ${T.neon}, #2563EB)`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#000",
      fontFamily: "'IBM Plex Mono', monospace",
      fontWeight: 700,
      boxShadow: `0 0 15px ${T.neon}55`,
    }}
  >
    LD
  </div>

  {/* User Details */}
  <div className="cba-user-details" style={{ lineHeight: 1.2 }}>
    <div
      style={{
        color: T.text,
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      {demoIdentity ? "Local Demo" : "Authenticated User"}
    </div>

    <div
      style={{
        color: T.muted,
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
      }}
    >
      {demoIdentity ? "DEVELOPMENT SESSION" : "ACCOUNT SESSION"}
    </div>
  </div>
</div>
      <button
        className="cba-sign-out"
        onClick={onLogout}
        aria-label="Sign out"
        style={{ padding:"8px 10px", color:T.text, background:"transparent", border:`1px solid ${T.border}`, borderRadius:7, cursor:"pointer", fontSize:12 }}
      >
        Sign out
      </button>
      </div>
      </div>
    </nav>
  );
}

function HeroRow({ score, credits, agentCount, onTopUp, scoreLive = false }) {
  const animatedScore = useAnimatedNumber(score, 1100);

  return (
    <div className="cba-hero-grid" style={{ display:"grid", gridTemplateColumns:"1.4fr 1fr 1fr", gap:14, marginBottom:22 }}>
      <Panel style={{ position:"relative", overflow:"hidden", padding:28 }}>
        <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:T.border }} />
        <Eyebrow>{scoreLive ? "Resilience Score · Pod Delta" : "Sample Resilience Score"}</Eyebrow>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:68, fontWeight:700, color:T.neon, lineHeight:1, letterSpacing:"-0.04em", animation:"countUp 0.5s ease" }}>
          {animatedScore}
        </div>
        <div style={{ display:"inline-flex", alignItems:"center", gap:4, background:"rgba(34,197,94,0.1)", border:"1px solid rgba(34,197,94,0.25)", color:T.safe, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, padding:"3px 9px", borderRadius:2, marginTop:10 }}>
          {scoreLive ? "Live value · trend unavailable" : "Sample change · +4 pts"}
        </div>
        <div style={{ marginTop:16, fontSize:12, color:T.muted }}>{scoreLive ? "Live score received from Pod Delta" : "Sample value · no score event received"}</div>
        <div style={{ marginTop:12, height:3, background:T.border, borderRadius:2, overflow:"hidden" }}>
          <div style={{ height:"100%", width:`${score}%`, background:T.neon, borderRadius:2, transition:"width 1.2s ease" }} />
        </div>
      </Panel>

      <Panel>
        <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:T.border }} />
        <Eyebrow>Sample Credit Balance</Eyebrow>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:44, fontWeight:700, lineHeight:1, marginBottom:4 }}>{credits}</div>
        <div style={{ fontSize:12, color:T.muted, marginBottom:16 }}>demo credits · wallet is separate</div>
        <div style={{ fontSize:11, color:T.muted, lineHeight:1.7 }}>
          Sample expiry: <strong style={{ color:T.warn }}>61 days</strong><br />
          Sample top-up: 3 days ago
        </div>
        <button
          onClick={onTopUp}
          className="cba-btn"
          style={{ width:"100%", marginTop:16, padding:9, background:"transparent", border:`1px solid rgba(0,229,255,0.3)`, color:T.neon, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, letterSpacing:"0.1em", textTransform:"uppercase", borderRadius:8, cursor:"pointer" }}
          onMouseEnter={e => e.currentTarget.style.background="rgba(0,229,255,0.08)"}
          onMouseLeave={e => e.currentTarget.style.background="transparent"}
        >＋ Purchase Credits</button>
      </Panel>

      <Panel>
        <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:T.border }} />
        <Eyebrow>Sample Engagements (30 days)</Eyebrow>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:38, fontWeight:700, lineHeight:1, marginBottom:4 }}>{agentCount}</div>
        <div style={{ fontSize:12, color:T.muted, marginBottom:16 }}>total executions</div>
        {[["Vuln Scan",6],["Malware",3],["Compliance",3]].map(([label,val]) => (
          <div key={label} style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:8 }}>
            <span style={{ color:T.muted }}>{label}</span>
            <span style={{ fontFamily:"'IBM Plex Mono',monospace", fontWeight:700 }}>{val}</span>
          </div>
        ))}
      </Panel>
    </div>
  );
}

  useEffect(() => {
    const style = document.createElement("style");
    style.textContent = globalCSS;
    document.head.appendChild(style);
    return () => document.head.removeChild(style);
  }, []);

  const [loggedIn, setLoggedIn]       = useState(false);
  const [leaderboard, setLeaderboard] = useState(INITIAL_LEADERBOARD);
  const [transactions, setTransactions] = useState([]);
  const [accessToken, setAccessToken] = useState("");
  const [demoIdentity, setDemoIdentity] = useState(false);
  const [topUpOpen, setTopUpOpen] = useState(false);
  const [topUpLoading, setTopUpLoading] = useState(false);
  const [demoReceipts, setDemoReceipts] = useState([]);
  const [demoEngagements, setDemoEngagements] = useState([]);
  const [currentReceipt, setCurrentReceipt] = useState(null);
  const [demoActionLoading, setDemoActionLoading] = useState(false);
  const [lastEngagement, setLastEngagement] = useState(null);
  const [connections, setConnections] = useState(null);
  const [connectionsLoading, setConnectionsLoading] = useState(false);
  const [apiErrors, setApiErrors] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [campaignError, setCampaignError] = useState("");
  const [recommendations, setRecommendations] = useState(null);
  const [recommendationError, setRecommendationError] = useState("");
  const [leaderboardConnected, setLeaderboardConnected] = useState(false);
  const [leaderboardSource, setLeaderboardSource] = useState("SEEDED DEMO DATA");
  const [walletData, setWalletData] = useState(null);
  const [walletError, setWalletError] = useState("");
  const [walletHistoryLive, setWalletHistoryLive] = useState(false);
  const [notifications, setNotifications] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [notificationError, setNotificationError] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [analyticsError, setAnalyticsError] = useState("");
  const [activeTab, setActiveTab]     = useState("Dashboard");
  const { toasts, add: toast }        = useToasts();

  function applyDemoState(state) {
    setWalletData(state.wallet);
    setWalletError("");
    setTransactions((state.transactions.entries || []).map(entry => ({
      type:entry.entry_type,
      desc:entry.reference_id,
      amount:Number(entry.amount),
      currency:entry.currency || "CR",
      time:entry.created_at ? new Date(entry.created_at).toLocaleString() : "RECENT",
    })));
    setDemoReceipts(state.receipts?.entries || []);
    setDemoEngagements(state.engagements || []);
    setLastEngagement(state.engagements?.[0] || null);
    setWalletHistoryLive(true);
    setNotifications(state.notifications);
    setPreferences(state.preferences);
    setNotificationError("");
    setAnalytics(state.analytics);
    setAnalyticsError("");
  }

  async function refreshConnections() {
    setConnectionsLoading(true);
    try {
      setConnections(await apiRequest("/api/v1/arena/connections", { token:accessToken }));
    } catch (error) {
      toast(`Connection check failed: ${error.message}`, "info");
    } finally {
      setConnectionsLoading(false);
    }
  }

  async function handleLogin(accountId, password) {
    const session = await apiRequest("/api/v1/auth/demo", {
      method:"POST",
      body:{ account_id:accountId, password },
    });
    setAccessToken(session.access_token);
    setDemoIdentity(session.mode === "development_demo");
    setLoggedIn(true);
    setActiveTab("Dashboard");
    toast("Demo account signed in. Payments and runs are simulated.", "success");
  }

  async function handleDemoTopUp(packageId, paymentMethod, customer, checkoutId) {
    setTopUpLoading(true);
    try {
      const result = await apiRequest("/api/v1/arena/demo/top-up", {
        token:accessToken,
        method:"POST",
        body:{
          package_id:packageId,
          payment_method:paymentMethod,
          checkout_id:checkoutId,
          customer_name:customer.name,
          customer_email:customer.email,
          billing_address:customer.billingAddress,
        },
      });
      applyDemoState(result.state);
      setCurrentReceipt(result.receipt);
      toast(result.payment.message, "success");
    } catch (error) {
      toast(`Demo top-up failed: ${error.message}`, "info");
    } finally {
      setTopUpLoading(false);
    }
  }

  async function handleDemoReset() {
    try {
      const state = await apiRequest("/api/v1/arena/demo/reset", {
        token:accessToken,
        method:"POST",
      });
      applyDemoState(state);
      setLastEngagement(null);
      setCurrentReceipt(null);
      toast("Demo wallet and activity reset to the starting state.", "success");
    } catch (error) {
      toast(`Could not reset demo account: ${error.message}`, "info");
    }
  }

  function handleLogout() {
    setLoggedIn(false);
    setAccessToken("");
    setDemoIdentity(false);
    setTopUpOpen(false);
    setLastEngagement(null);
    setConnections(null);
    setCampaigns([]);
    setCampaignError("");
    setRecommendations(null);
    setRecommendationError("");
    setLeaderboard(INITIAL_LEADERBOARD);
    setLeaderboardConnected(false);
    setLeaderboardSource("SEEDED DEMO DATA");
    setWalletData(null);
    setWalletError("");
    setWalletHistoryLive(false);
    setTransactions([]);
    setNotifications(null);
    setPreferences(null);
    setNotificationError("");
    setAnalytics(null);
    setAnalyticsError("");
    setApiErrors([]);
    setActiveTab("Dashboard");
  }

  useEffect(() => {
    if (!accessToken) return undefined;
    let active = true;
    setConnectionsLoading(true);
    setApiErrors([]);

    const load = async (path, onSuccess, label) => {
      try {
        const data = await apiRequest(path, { token:accessToken });
        if (active) onSuccess(data);
      } catch (error) {
        if (active) {
          if (error.status === 404 && (label === "analytics" || label === "resilience score")) {
            if (label === "analytics") setAnalyticsError("No analytics record exists for this tenant yet.");
            return;
          }
          setApiErrors(current => [...current, `${label}: ${error.message}`]);
          if (label === "campaigns") setCampaignError(error.message);
          if (label === "recommendations") setRecommendationError(error.message);
          if (label === "wallet" || label === "wallet history") setWalletError(error.message);
          if (label === "notifications" || label === "preferences") setNotificationError(error.message);
          if (label === "analytics") setAnalyticsError(error.message);
        }
      }
    };

    const requests = [
      load("/api/v1/arena/connections", setConnections, "connections"),
      load("/api/v1/arena/campaigns", data => {
        setCampaigns(Array.isArray(data) ? data : []);
        setCampaignError("");
      }, "campaigns"),
      load("/api/v1/arena/engagement/recommendations", data => {
        setRecommendations(data);
        setRecommendationError("");
      }, "recommendations"),
      load("/api/v1/arena/leaderboard", data => {
        const rows = Array.isArray(data) ? data : (data.entries || []);
        setLeaderboard(rows.map((row, index) => ({
          rank:row.rank || index + 1,
          name:row.username || row.tenant_id || "Tenant",
          score:Number(row.score ?? row.security_score ?? 0),
          delta:row.delta_score ?? row.delta ?? 0,
          isYou:row.username === "1",
        })));
        setLeaderboardConnected(true);
        setLeaderboardSource(data.label || "POD GAMMA API · SOURCE UNCLASSIFIED — TREAT AS DEMO");
      }, "leaderboard"),
    ];

    if (demoIdentity) {
      requests.push(
        load("/api/v1/arena/demo/state", applyDemoState, "demo account"),
      );
    } else {
      requests.push(
        load("/api/v1/arena/analytics/dashboard", data => {
          setAnalytics(data);
          setAnalyticsError("");
        }, "analytics"),
        load("/api/v1/arena/wallet/balance", data => {
          setWalletData(data);
          setWalletError("");
        }, "wallet"),
        load("/api/v1/arena/wallet/history", data => {
          const entries = data.entries || [];
          setWalletHistoryLive(true);
          setTransactions(entries.map(entry => ({
            type:entry.entry_type || entry.transaction_type || "debit",
            desc:entry.reference_id || entry.module_source || "Wallet entry",
            amount:Number(entry.amount),
            currency:entry.currency || "CR",
            time:entry.created_at ? new Date(entry.created_at).toLocaleString() : "RECENT",
          })));
        }, "wallet history"),
        load("/api/v1/arena/notifications", data => {
          setNotifications(data);
          setNotificationError("");
        }, "notifications"),
        load("/api/v1/arena/preferences", data => {
          setPreferences(data);
          setNotificationError("");
        }, "preferences"),
      );
    }

    Promise.all(requests).finally(() => {
      if (active) setConnectionsLoading(false);
    });

    return () => { active = false; };
  }, [accessToken, demoIdentity]);

  function handleAgentRun(agent) {
    if (!demoIdentity || demoActionLoading) return;
    setDemoActionLoading(true);
    apiRequest("/api/v1/arena/demo/engagements", {
      token:accessToken,
      method:"POST",
      body:{
        campaign_id:agent.id,
        campaign_title:agent.name,
        credit_cost:agent.cost,
      },
    }).then(result => {
      setLastEngagement(result.engagement);
      applyDemoState(result.state);
      toast(
        `${agent.name} simulation completed with ${result.engagement.finding_count} sample findings. No scan ran.`,
        "success",
      );
    }).catch(error => {
      toast(`Demo scan could not run: ${error.message}`, "info");
    }).finally(() => setDemoActionLoading(false));
  }

  const allServicesHealthy = Boolean(
    connections
    && connections.pod_delta.status === "healthy"
    && connections.upstreams.every(item => item.status === "healthy")
  );

  if (!loggedIn) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div style={{ minHeight:"100vh", background:T.bg }}>
      <ParticleField color={T.neon} density={80} />
      <Nav activeTab={activeTab} setActiveTab={setActiveTab} demoIdentity={demoIdentity} onLogout={handleLogout} />
      <div className="cba-container" style={{ padding:"28px 12px", maxWidth:"1700px", margin:"0 auto", position:"relative" }}>
        <svg
          className="cba-shield"
          viewBox="0 0 200 220"
          style={{
            position:"absolute", top:-60, right:-40,
            width:560, height:620,
            opacity:0.10, filter:"blur(6px)",
            pointerEvents:"none", zIndex:0,
          }}
        >
          <path
            d="M100 6 L182 34 V104 C182 154 148 190 100 214 C52 190 18 154 18 104 V34 Z"
            fill="none" stroke={T.neon} strokeWidth="3"
          />
          <path
            d="M100 6 L182 34 V104 C182 154 148 190 100 214 C52 190 18 154 18 104 V34 Z"
            fill={T.neon} opacity="0.06"
          />
          <path
            d="M64 108 L88 132 L138 78"
            fill="none" stroke={T.neon} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
        <div style={{ position:"relative", zIndex:1 }}>
        <div style={{ marginBottom:26, display:"flex", alignItems:"flex-end", justifyContent:"space-between" }}>
          <div>
            <Eyebrow>Module 4 — Arena</Eyebrow>
            <h1 style={{ fontFamily:T.fontDisplay, fontSize:36, fontWeight:700, letterSpacing:"0.01em", lineHeight:1.1 }}>
              {activeTab}
            </h1>
            <p style={{ color:T.muted, fontSize:14, marginTop:6 }}>
              {activeTab === "Dashboard" && "Your account overview, live service status, and connected Arena data."}
              {activeTab === "Campaigns" && "Browse campaign definitions supplied by Pod Beta."}
              {activeTab === "Leaderboard" && "Leaderboard entries are loaded from Pod Gamma when available."}
              {activeTab === "Benchmark" && "Review seeded synthetic cohort baselines from Pod Gamma."}
              {activeTab === "Wallet" && (demoIdentity ? "Try simulated top-ups, payment methods, and a working demo ledger." : "Read wallet balance and ledger history from the Wallet service.")}
              {activeTab === "Notifications" && (demoIdentity ? "Sample events generated by demo payments and scan runs." : "Tenant-scoped notifications and preferences from Pod Delta.")}
              {activeTab === "Analytics" && (demoIdentity ? "Sample account metrics that update after a simulated scan." : "Tenant-scoped dashboard metrics from Pod Delta.")}
              {activeTab === "Services" && "Check upstream health and diagnose integrations."}
            </p>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:6, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, color:allServicesHealthy ? T.safe : T.warn, letterSpacing:"0.08em" }}>
            <span style={{ width:6, height:6, borderRadius:"50%", background:allServicesHealthy ? T.safe : T.warn, boxShadow:`0 0 6px ${allServicesHealthy ? T.safe : T.warn}`, display:"inline-block" }} />
            {connections
              ? `${connections.upstreams.filter(item => item.status === "healthy").length + (connections.pod_delta.status === "healthy" ? 1 : 0)}/${connections.upstreams.length + 1} SERVICES ONLINE`
              : "CHECKING POD CONNECTIONS"}
          </div>
        </div>

        {activeTab === "Dashboard" && (
          <Reveal>
            <DashboardOverview
              connections={connections}
              campaigns={campaigns}
              leaderboard={leaderboard}
              leaderboardConnected={leaderboardConnected}
              demoIdentity={demoIdentity}
              walletData={walletData}
              analytics={analytics}
              onNavigate={setActiveTab}
            />
          </Reveal>
        )}

        {activeTab === "Campaigns" && (
          <>
            <Reveal><CampaignLibrary campaigns={campaigns} error={campaignError} /></Reveal>
            <Reveal delay={40}><RecommendationsPanel data={recommendations} error={recommendationError} /></Reveal>
            <Reveal delay={80}>
              <div style={{ marginTop:18 }}>
                <SectionHeader title="Simulated Security Runs" action="NO REAL TARGETS ACCESSED" />
              </div>
              {lastEngagement && (
                <Panel style={{ marginBottom:14 }}>
                  <SectionHeader title={`Run complete · ${lastEngagement.campaign_title}`} action={`${lastEngagement.finding_count} SAMPLE FINDINGS`} />
                  <p style={{ color:T.warning, fontSize:12, marginBottom:12 }}>{lastEngagement.notice}</p>
                  <button type="button" onClick={() => downloadDemoReport(lastEngagement)} className="cba-btn" style={{ marginBottom:12, padding:"8px 12px", background:"transparent", color:T.neon, border:`1px solid ${T.neon}`, borderRadius:8, cursor:"pointer" }}>Download this report</button>
                  <div style={{ display:"grid", gap:8 }}>
                    {lastEngagement.results.map(item => (
                      <div key={item.id} style={{ display:"flex", justifyContent:"space-between", gap:12, padding:"9px 12px", border:`1px solid ${T.border}`, borderRadius:8 }}>
                        <span>{item.title}</span>
                        <strong style={{ color:item.severity === "high" ? T.danger : item.severity === "medium" ? T.warning : T.neon, textTransform:"uppercase" }}>{item.severity} · simulated</strong>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
              {demoIdentity && demoEngagements.length > 0 && (
                <Panel style={{ marginBottom:14 }}>
                  <SectionHeader title="Simulation report history" action={`${demoEngagements.length} DOWNLOADABLE`} />
                  <p style={{ color:T.muted, fontSize:11, marginBottom:12 }}>These sample reports are generated by Pod Delta's demo simulator. Pod Beta has not executed these runs.</p>
                  <div style={{ display:"grid", gap:9 }}>
                    {demoEngagements.map(engagement => (
                      <div key={engagement.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", gap:12, flexWrap:"wrap", padding:12, border:`1px solid ${T.border}`, borderRadius:8 }}>
                        <div>
                          <strong style={{ display:"block", fontSize:12 }}>{engagement.campaign_title}</strong>
                          <span style={{ color:T.muted, fontSize:11 }}>{new Date(engagement.completed_at).toLocaleString()} · {engagement.finding_count} sample findings · {engagement.credit_cost} CR</span>
                        </div>
                        <div style={{ display:"flex", gap:8 }}>
                          <button type="button" onClick={() => downloadDemoReport(engagement)} className="cba-btn" style={{ padding:"7px 10px", background:"transparent", color:T.neon, border:`1px solid ${T.neon}`, borderRadius:7, cursor:"pointer" }}>Download HTML</button>
                          <button type="button" onClick={() => downloadDemoReportJson(engagement)} className="cba-btn" style={{ padding:"7px 10px", background:"transparent", color:T.muted, border:`1px solid ${T.border}`, borderRadius:7, cursor:"pointer" }}>Download JSON</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
              <div className="cba-agents-grid" style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
                {AGENTS.map(a => (
                  <AgentCard key={a.id} agent={a} onRun={handleAgentRun} />
                ))}
              </div>
            </Reveal>
          </>
        )}

        {activeTab === "Leaderboard" && (
          <Reveal>
            <p style={{ color:T.muted, fontSize:11, marginBottom:8 }}>{leaderboardConnected ? leaderboardSource : "SEEDED DEMO DATA · POD GAMMA UNAVAILABLE"}</p>
            <LeaderboardPanel entries={leaderboard} />
          </Reveal>
        )}

        {activeTab === "Benchmark" && (
          <Reveal><BenchmarkPanel token={accessToken} /></Reveal>
        )}

        {activeTab === "Wallet" && (
          <Reveal>
            <Panel style={{ marginBottom:16 }}>
              <SectionHeader
                title={demoIdentity ? "Demo Wallet" : "Wallet Service"}
                action={demoIdentity ? "SIMULATED LEDGER" : walletData ? "LIVE API" : "NOT CONNECTED"}
              />
              {walletData
                ? <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:12 }}>
                    <p>Available balance: <strong>{walletData.available_balance} {walletData.currency}</strong></p>
                    {demoIdentity && (
                      <div style={{ display:"flex", gap:8 }}>
                        <button className="cba-btn" onClick={() => setTopUpOpen(true)} style={{ padding:"9px 14px", background:T.neon, color:"#001318", border:0, borderRadius:8, fontWeight:700, cursor:"pointer" }}>＋ Demo top-up</button>
                        <button className="cba-btn" onClick={handleDemoReset} style={{ padding:"9px 14px", background:"transparent", color:T.muted, border:`1px solid ${T.border}`, borderRadius:8, cursor:"pointer" }}>Reset demo</button>
                      </div>
                    )}
                  </div>
                : <p style={{ color:demoIdentity ? T.muted : T.warn }}>
                    {walletError || "Wallet response not available."}
                  </p>}
            </Panel>
            {walletHistoryLive
              ? <TransactionLog transactions={transactions} />
              : <p style={{ color:T.muted, fontSize:12 }}>
                  {demoIdentity
                    ? "The simulated ledger shows demo top-ups and scan-credit debits."
                    : "Wallet history has not been loaded for this account."}
                </p>}
            {demoIdentity && demoReceipts.length > 0 && (
              <Panel style={{ marginTop:14 }}>
                <SectionHeader title="Payment receipts" action="SIMULATED PROOF" />
                <div style={{ display:"grid", gap:8 }}>
                  {demoReceipts.map(item => (
                    <div key={item.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", gap:12, padding:"10px 12px", border:`1px solid ${T.border}`, borderRadius:8 }}>
                      <div>
                        <strong style={{ display:"block", fontSize:12 }}>{item.receipt_number} · {item.line_items[0]?.description}</strong>
                        <span style={{ color:T.muted, fontSize:11 }}>{item.credits_added.toLocaleString()} CR · {new Date(item.issued_at).toLocaleString()}</span>
                      </div>
                      <button type="button" onClick={() => { setCurrentReceipt(item); setTopUpOpen(true); }} className="cba-btn" style={{ padding:"7px 10px", border:`1px solid ${T.border}`, background:"transparent", color:T.neon, borderRadius:7, cursor:"pointer", whiteSpace:"nowrap" }}>View receipt</button>
                    </div>
                  ))}
                </div>
              </Panel>
            )}
          </Reveal>
        )}

        {activeTab === "Notifications" && (
          <Reveal><NotificationsPanel notifications={notifications} preferences={preferences} error={notificationError} demoMode={demoIdentity} /></Reveal>
        )}

        {activeTab === "Analytics" && (
          <Reveal><AnalyticsPanel data={analytics} error={analyticsError} /></Reveal>
        )}

        {activeTab === "Services" && (
          <Reveal>
            <ConnectionsPanel connections={connections} loading={connectionsLoading} refresh={refreshConnections} />
            {apiErrors.length > 0 && (
              <Panel style={{ marginTop:14 }}>
                <SectionHeader title="Integration Details" />
                {apiErrors.map((error, index) => <p key={index} style={{ color:T.warn, marginTop:6 }}>{error}</p>)}
              </Panel>
            )}
          </Reveal>
        )}
        </div>
      </div>

      <TopUpModal
        open={topUpOpen}
        onClose={() => { setTopUpOpen(false); setCurrentReceipt(null); }}
        onPurchase={handleDemoTopUp}
        purchasing={topUpLoading}
        receipt={currentReceipt}
      />
      <ToastStack toasts={toasts} />
    </div>
  );
}

export default CyBreachArena;