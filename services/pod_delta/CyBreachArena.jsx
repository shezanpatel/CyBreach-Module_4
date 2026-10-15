import { useState, useEffect, useCallback } from "react";

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
    .cba-nav-tabs {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
    }
    .cba-nav-tabs::-webkit-scrollbar { display: none; }
    .cba-hero-grid { grid-template-columns: 1fr 1fr !important; }
    .cba-agents-grid { grid-template-columns: 1fr 1fr !important; }
    .cba-two-col { grid-template-columns: 1fr !important; }
    .cba-shield { display: none !important; }
  }
  @media (max-width: 640px) {
    .cba-hero-grid { grid-template-columns: 1fr !important; }
    .cba-agents-grid { grid-template-columns: 1fr !important; }
    .cba-container { padding: 20px 16px !important; }
    .cba-nav { padding: 12px 16px !important; }
    .cba-nav-inner { flex-direction: column; align-items: flex-start !important; gap: 12px; }
    .cba-nav-tabs { width: 100%; }
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

const TOPUP_PLANS = [
  { credits:50,  price:"₹149"  },
  { credits:100, price:"₹279"  },
  { credits:250, price:"₹599"  },
  { credits:500, price:"₹1,099"},
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

function RunButton({ onClick, disabled, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={disabled ? "" : "cba-btn"}
      style={{
        width:"100%", marginTop:12, padding:"9px 0",
        background:"transparent",
        border:`1px solid ${disabled ? "rgba(0,229,255,0.15)" : "rgba(0,229,255,0.35)"}`,
        color: disabled ? T.muted : T.neon,
        fontFamily:"'IBM Plex Mono',monospace", fontSize:11,
        letterSpacing:"0.1em", textTransform:"uppercase",
        borderRadius:8, cursor: disabled ? "not-allowed" : "pointer",
        transition:"background 0.2s, border-color 0.2s",
      }}
      onMouseEnter={e => { if (!disabled) e.target.style.background = "rgba(0,229,255,0.09)"; }}
      onMouseLeave={e => { e.target.style.background = "transparent"; }}
    >
      {loading ? "◉ Running..." : "▷ Run Agent"}
    </button>
  );
}

function AgentCard({ agent, credits, onRun }) {
  const [running, setRunning] = useState(false);
  const [hovered, setHovered] = useState(false);

  function handleRun() {
    if (credits < agent.cost) {
      onRun(agent, false);
      return;
    }
    setRunning(true);
    onRun(agent, true);
    setTimeout(() => setRunning(false), 4000);
  }

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
      background: T.surface3,
      border: `1px solid ${running ? "rgba(0,229,255,0.45)" : hovered ? T.neonDim : T.border}`,
      borderRadius:8, padding:20,
      boxShadow: running ? "0 0 20px rgba(0,229,255,0.1)" : hovered ? "0 10px 28px rgba(0,0,0,0.35)" : "none",
      transform: hovered && !running ? "translateY(-3px)" : "translateY(0)",
      transition:"border-color 0.25s, box-shadow 0.25s, transform 0.25s",
      display:"flex", flexDirection:"column",
      animation:"fadeIn 0.35s ease",
    }}>
      <div style={{ height:2, background: running ? T.neon : T.border, borderRadius:2, marginBottom:16, transition:"background 0.3s" }} />

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
          background: running ? "rgba(34,197,94,0.1)" : "rgba(0,229,255,0.07)",
          color: running ? T.safe : T.neon,
          border: `1px solid ${running ? "rgba(34,197,94,0.25)" : "rgba(0,229,255,0.2)"}`,
        }}>
          {running ? "RUNNING" : "READY"}
        </span>
      </div>

      {running && (
        <div style={{ marginTop:12 }}>
          <div style={{ height:2, background:T.border, borderRadius:2, overflow:"hidden" }}>
            <div style={{
              height:"100%", background:T.neon, borderRadius:2,
              boxShadow:`0 0 6px ${T.neon}`,
              animation:"scanBar 3.8s ease-in-out forwards",
            }} />
          </div>
          <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:9, color:T.neon, marginTop:5, letterSpacing:"0.06em" }}>
            ▷ SCANNING...
          </div>
        </div>
      )}

      <RunButton onClick={handleRun} disabled={running} loading={running} />
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

function TopUpModal({ open, onClose, onConfirm }) {
  const [selected, setSelected] = useState(0);

  if (!open) return null;

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position:"fixed", inset:0,
        background:"rgba(0,0,0,0.82)",
        backdropFilter:"blur(8px)",
        display:"flex", alignItems:"center", justifyContent:"center",
        zIndex:200,
      }}
    >
      <div style={{
        background:T.surface,
        border:"1px solid rgba(0,229,255,0.2)",
        borderRadius:8, padding:32, width:"min(440px, 92vw)",
        boxShadow:"0 0 60px rgba(0,0,0,0.8), 0 0 24px rgba(0,229,255,0.08)",
        position:"relative", animation:"fadeIn 0.25s ease",
      }}>
        <button
          onClick={onClose}
          style={{ position:"absolute", top:14, right:14, background:"none", border:"none", color:T.muted, fontSize:18, cursor:"pointer" }}
        >✕</button>

        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:18, fontWeight:700, color:T.neon, marginBottom:4 }}>
          ◈ Purchase Credits
        </div>
        <div style={{ fontSize:13, color:T.muted, marginBottom:22 }}>
          Credits are added within 1–2 hours after UPI confirmation.
        </div>

        <div className="cba-plan-grid" style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8, marginBottom:18 }}>
          {TOPUP_PLANS.map((plan, i) => (
            <div
              key={i}
              onClick={() => setSelected(i)}
              style={{
                border:`1px solid ${selected===i ? T.neon : T.border}`,
                background: selected===i ? "rgba(0,229,255,0.06)" : "transparent",
                borderRadius:8, padding:"14px 8px", textAlign:"center",
                cursor:"pointer", transition:"all 0.15s",
              }}
            >
              <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:20, fontWeight:700, color:T.neon }}>
                {plan.credits}
              </div>
              <div style={{ fontSize:10, color:T.muted, marginTop:3 }}>credits</div>
              <div style={{ fontSize:12, color:T.text, marginTop:6, fontWeight:600 }}>{plan.price}</div>
            </div>
          ))}
        </div>

        <div style={{ fontSize:11, color:T.muted, padding:"10px 12px", background:T.surface2, borderLeft:`2px solid ${T.neon}`, marginBottom:18, lineHeight:1.5 }}>
          ⓘ This simulates UPI payment. In production, clicking below opens your UPI app.
          Credits post automatically when the transaction confirms.
        </div>

        <button
          onClick={() => { onConfirm(TOPUP_PLANS[selected].credits); onClose(); }}
          className="cba-btn"
          style={{
            width:"100%", padding:13,
            background:T.neon, color:"#000",
            fontFamily:"'IBM Plex Mono',monospace", fontSize:12,
            fontWeight:700, letterSpacing:"0.1em", textTransform:"uppercase",
            border:"none", borderRadius:8, cursor:"pointer",
          }}
        >
          Confirm & Pay via UPI
        </button>
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
            {tx.type === "credit" ? "+" : "-"}{tx.amount} CR
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
                  ● VERIFIED
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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (!email || !password) return setError("Enter email and password.");
    setError("");
    onLogin(email);
  };

  const input = {
    width: "100%",
    padding: "13px 15px",
    marginTop: 8,
    background: "rgba(255,255,255,.03)",
    border: `1px solid ${T.border}`,
    borderRadius: 10,
    color: T.text,
    outline: "none",
    fontFamily: "'IBM Plex Sans',sans-serif",
    transition: ".3s"
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
          Enterprise Security Operations Platform
        </div>

        <form onSubmit={submit}>

          <Eyebrow>Email</Eyebrow>

          <input
            type="email"
            value={email}
            style={input}
            placeholder="you@company.com"
            onChange={(e) => setEmail(e.target.value)}
          />

          <div style={{ marginTop: 18 }}>
            <Eyebrow>Password</Eyebrow>

            <input
              type="password"
              value={password}
              style={input}
              placeholder="••••••••"
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

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

          <button
            className="cba-btn"
            style={{
              width: "100%",
              marginTop: 28,
              padding: 14,
              border: 0,
              borderRadius: 10,
              cursor: "pointer",
              background:
                "linear-gradient(90deg,#00e5ff,#00b7d4)",
              color: "#001318",
              fontWeight: 700,
              letterSpacing: ".15em",
              fontFamily: "'IBM Plex Mono',monospace",
              boxShadow: "0 0 25px rgba(0,229,255,.35)"
            }}
          >
            LOGIN
          </button>

        </form>

        <div
          style={{
            marginTop: 24,
            textAlign: "center",
            color: "#22c55e",
            fontSize: 11,
            fontFamily: "'IBM Plex Mono',monospace"
          }}
        >
          ● SECURE CONNECTION ESTABLISHED
        </div>

      </div>

    </div>
  );
}
function Nav({ credits, onTopUp, activeTab, setActiveTab }) {
  const tabs = ["Dashboard","Agents","Leaderboard","Reports","Transactions"];
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
      <div style={{ fontFamily:T.fontDisplay, fontSize:19, fontWeight:700, color:T.neon, letterSpacing:"0.04em", display:"flex", alignItems:"center", gap:8 }}>
        <span style={{ animation:"pulse 2s ease-in-out infinite", display:"inline-block" }}>◈</span>
        CYBREACH ARENA
      </div>

      <div className="cba-nav-tabs" style={{ display:"flex", gap:4 }}>
        {tabs.map(t => (
          <button
            key={t}
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
        <button
          onClick={onTopUp}
          className="cba-btn"
          style={{
            display:"flex", alignItems:"center", gap:8,
            background:T.surface2, border:`1px solid ${T.border}`,
            borderRadius:8, padding:"7px 14px",
            fontFamily:"'IBM Plex Mono',monospace", fontSize:12,
            color:T.text, cursor:"pointer",
            transition:"border-color 0.2s",
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor=T.neon}
          onMouseLeave={e => e.currentTarget.style.borderColor=T.border}
        >
          <span style={{ width:6, height:6, borderRadius:"50%", background:T.neon, boxShadow:`0 0 8px ${T.neon}`, display:"inline-block" }} />
          {credits} CR
          <span style={{ color:T.muted, fontSize:11 }}>＋ Top Up</span>
        </button>

        <div
  style={{
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "6px 10px",
    border: `1px solid ${T.border}`,
    borderRadius: 10,
    background: "rgba(255,255,255,0.03)",
    cursor: "pointer",
    transition: "all .2s ease",
  }}
>
  {/* Avatar */}
  <div
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
    RK
  </div>

  {/* User Details */}
  <div style={{ lineHeight: 1.2 }}>
    <div
      style={{
        color: T.text,
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      Kylie Moss
    </div>

    <div
      style={{
        color: T.muted,
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
      }}
    >
      UID: CBA-10241
    </div>
  </div>
</div>
      </div>
      </div>
    </nav>
  );
}

function HeroRow({ score, credits, agentCount, onTopUp }) {
  const animatedScore = useAnimatedNumber(score, 1100);

  return (
    <div className="cba-hero-grid" style={{ display:"grid", gridTemplateColumns:"1.4fr 1fr 1fr", gap:14, marginBottom:22 }}>
      <Panel style={{ position:"relative", overflow:"hidden", padding:28 }}>
        <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:T.border }} />
        <Eyebrow>Resilience Score</Eyebrow>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:68, fontWeight:700, color:T.neon, lineHeight:1, letterSpacing:"-0.04em", animation:"countUp 0.5s ease" }}>
          {animatedScore}
        </div>
        <div style={{ display:"inline-flex", alignItems:"center", gap:4, background:"rgba(34,197,94,0.1)", border:"1px solid rgba(34,197,94,0.25)", color:T.safe, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, padding:"3px 9px", borderRadius:2, marginTop:10 }}>
          ▲ +4 pts this week
        </div>
        <div style={{ marginTop:16, fontSize:12, color:T.muted }}>Top 23% in your industry</div>
        <div style={{ marginTop:12, height:3, background:T.border, borderRadius:2, overflow:"hidden" }}>
          <div style={{ height:"100%", width:`${score}%`, background:T.neon, borderRadius:2, transition:"width 1.2s ease" }} />
        </div>
      </Panel>

      <Panel>
        <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:T.border }} />
        <Eyebrow>Credit Balance</Eyebrow>
        <div style={{ fontFamily:"'IBM Plex Mono',monospace", fontSize:44, fontWeight:700, lineHeight:1, marginBottom:4 }}>{credits}</div>
        <div style={{ fontSize:12, color:T.muted, marginBottom:16 }}>credits available</div>
        <div style={{ fontSize:11, color:T.muted, lineHeight:1.7 }}>
          Expiry in <strong style={{ color:T.warn }}>61 days</strong><br />
          Last top-up: 3 days ago
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
        <Eyebrow>Agents Run (30 days)</Eyebrow>
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
  const [credits, setCredits]         = useState(245);
  const [score, setScore]             = useState(74);
  const [agentCount, setAgentCount]   = useState(12);
  const [badges, setBadges]           = useState(INITIAL_BADGES);
  const [activity, setActivity]       = useState(INITIAL_ACTIVITY);
  const [leaderboard, setLeaderboard] = useState(INITIAL_LEADERBOARD);
  const [transactions, setTransactions] = useState([
    { type:"credit", desc:"UPI top-up", amount:100, time:"2 HOURS AGO" },
    { type:"debit",  desc:"Vulnerability Scan run", amount:5, time:"2 DAYS AGO" },
    { type:"debit",  desc:"Compliance Audit run", amount:20, time:"4 DAYS AGO" },
  ]);
  const [modalOpen, setModalOpen]     = useState(false);
  const [activeTab, setActiveTab]     = useState("Dashboard");
  const { toasts, add: toast }        = useToasts();

  function handleAgentRun(agent, hasCredits) {
    if (!hasCredits) {
      toast(`⚠ Need ${agent.cost} CR to run ${agent.name}. Top up first.`, "info");
      setModalOpen(true);
      return;
    }

    setCredits(c => c - agent.cost);
    setAgentCount(c => c + 1);
    toast(`▷ ${agent.name} started — ${agent.cost} CR deducted`, "info");
    setTransactions(t => [{ type:"debit", desc:`${agent.name} run`, amount:agent.cost, time:"JUST NOW" }, ...t]);

    setTimeout(() => {
      setScore(s => Math.min(s + 2, 100));
      setLeaderboard(lb => lb.map(row => row.isYou ? { ...row, score: Math.min(row.score+2, 100), delta: row.delta+1 } : row));
      setActivity(a => [{ icon:"▷", type:"scan", text:`${agent.name} completed — results ready`, time:"JUST NOW" }, ...a]);

      if (agent.id === "threat") {
        setBadges(b => b.map(badge => badge.id==="hunter" ? { ...badge, unlocked:true } : badge));
        toast("✦ New badge earned: Threat Hunter (Platinum)!", "success");
      } else {
        toast(`✓ ${agent.name} complete — score updated`, "success");
      }
    }, 4000);
  }

  function handleTopUp(amount) {
    toast(`◈ UPI initiated — ${amount} CR arriving shortly...`, "info");
    setTimeout(() => {
      setCredits(c => c + amount);
      setTransactions(t => [{ type:"credit", desc:"UPI top-up", amount, time:"JUST NOW" }, ...t]);
      setActivity(a => [{ icon:"◈", type:"credit", text:`+${amount} credits added via UPI`, time:"JUST NOW" }, ...a]);
      toast(`✓ ${amount} credits added to your wallet`, "success");
    }, 2000);
  }

  if (!loggedIn) {
    return <LoginScreen onLogin={() => setLoggedIn(true)} />;
  }

  return (
    <div style={{ minHeight:"100vh", background:T.bg }}>
      <ParticleField color={T.neon} density={80} />
      <Nav credits={credits} onTopUp={() => setModalOpen(true)} activeTab={activeTab} setActiveTab={setActiveTab} />
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
              {activeTab === "Dashboard" && "Welcome back, Kylie . Your resilience score improved 4 points this week."}
              {activeTab === "Agents"    && "Run a security agent to improve your resilience score."}
              {activeTab === "Leaderboard" && "See how your organisation ranks globally."}
              {activeTab === "Reports"   && "Download and share your engagement reports."}
              {activeTab === "Transactions" && "Full history of every credit movement."}
            </p>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:6, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, color:T.safe, letterSpacing:"0.08em" }}>
            <span style={{ width:6, height:6, borderRadius:"50%", background:T.safe, boxShadow:`0 0 6px ${T.safe}`, display:"inline-block", animation:"blink 1.4s ease-in-out infinite" }} />
            ALL SYSTEMS LIVE
          </div>
        </div>

        {activeTab === "Dashboard" && (
          <>
            <Reveal><HeroRow score={score} credits={credits} agentCount={agentCount} onTopUp={() => setModalOpen(true)} /></Reveal>
            <Reveal delay={80}>
              <div style={{ marginBottom:22 }}>
                <SectionHeader title="Security Agents" action="View all" onAction={() => setActiveTab("Agents")} />
                <div className="cba-agents-grid" style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
                  {AGENTS.map(a => (
                    <AgentCard key={a.id} agent={a} credits={credits} onRun={handleAgentRun} />
                  ))}
                </div>
              </div>
            </Reveal>
            <Reveal delay={120}><BadgesPanel badges={badges} /></Reveal>
            <Reveal delay={160}>
              <div className="cba-two-col" style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14, marginTop:22 }}>
                <LeaderboardPanel entries={leaderboard} />
                <ActivityFeed items={activity} />
              </div>
            </Reveal>
          </>
        )}

        {activeTab === "Agents" && (
          <>
            <Reveal><HeroRow score={score} credits={credits} agentCount={agentCount} onTopUp={() => setModalOpen(true)} /></Reveal>
            <Reveal delay={80}>
              <div className="cba-agents-grid" style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
                {AGENTS.map(a => (
                  <AgentCard key={a.id} agent={a} credits={credits} onRun={handleAgentRun} />
                ))}
              </div>
            </Reveal>
          </>
        )}

        {activeTab === "Leaderboard" && (
          <Reveal><LeaderboardPanel entries={leaderboard} /></Reveal>
        )}

        {activeTab === "Transactions" && (
          <Reveal><TransactionLog transactions={transactions} /></Reveal>
        )}

        {activeTab === "Reports" && (
          <Reveal>
            <Panel>
              <SectionHeader title="Monthly Reports" />
              {["June 2026","May 2026","April 2026"].map((month, i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"14px 0", borderBottom: i<2 ? `1px solid ${T.border}` : "none" }}>
                  <div>
                    <div style={{ fontSize:13, fontWeight:600 }}>{month} — Security Report</div>
                    <div style={{ fontSize:11, color:T.muted, marginTop:3 }}>Agents run, credits consumed, score trend, badge progress</div>
                  </div>
                  <button className="cba-btn" style={{ padding:"7px 16px", background:"transparent", border:`1px solid rgba(0,229,255,0.3)`, color:T.neon, fontFamily:"'IBM Plex Mono',monospace", fontSize:11, borderRadius:8, cursor:"pointer", letterSpacing:"0.08em" }}
                    onMouseEnter={e => e.currentTarget.style.background="rgba(0,229,255,0.08)"}
                    onMouseLeave={e => e.currentTarget.style.background="transparent"}
                  >↓ PDF</button>
                </div>
              ))}
            </Panel>
          </Reveal>
        )}
        </div>
      </div>

      <TopUpModal open={modalOpen} onClose={() => setModalOpen(false)} onConfirm={handleTopUp} />
      <ToastStack toasts={toasts} />
    </div>
  );
}

export default CyBreachArena;