(function () {
  const chatArea = document.getElementById("chat-area");
  const composer = document.getElementById("composer");
  const input = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const modeBanner = document.getElementById("mode-banner");
  const themeToggle = document.getElementById("theme-toggle");

  const pageData = JSON.parse(document.getElementById("page-data").textContent);
  if (!pageData.geminiLive) {
    modeBanner.style.display = "block";
  }

  // ---------- Theme toggle ----------
  const root = document.documentElement;
  themeToggle.addEventListener("click", () => {
    const isDark = root.getAttribute("data-theme") === "dark";
    root.setAttribute("data-theme", isDark ? "light" : "dark");
    themeToggle.textContent = isDark ? "🌙" : "☀️";
  });

  // ---------- Helpers ----------
  function nowLabel() {
    const d = new Date();
    let h = d.getHours();
    const m = d.getMinutes().toString().padStart(2, "0");
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return `${h}:${m} ${ampm}`;
  }

  function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  function addOutgoingBubble(text) {
    const el = document.createElement("div");
    el.className = "bubble bubble-out";
    el.textContent = text;
    const time = document.createElement("span");
    time.className = "bubble-time";
    time.innerHTML = `${nowLabel()} <span class="ticks" data-ticks>✓</span>`;
    el.appendChild(time);
    chatArea.appendChild(el);
    scrollToBottom();
    return el;
  }

  function upgradeTicks(bubbleEl, state) {
    const ticksEl = bubbleEl.querySelector("[data-ticks]");
    if (!ticksEl) return;
    if (state === "delivered") ticksEl.textContent = "✓✓";
    if (state === "read") {
      ticksEl.textContent = "✓✓";
      ticksEl.classList.add("read");
    }
  }

  function addTypingIndicator() {
    const el = document.createElement("div");
    el.className = "typing-bubble";
    el.innerHTML = "<span></span><span></span><span></span>";
    chatArea.appendChild(el);
    scrollToBottom();
    return el;
  }

  function addBotBubble(text) {
    const el = document.createElement("div");
    el.className = "bubble bubble-in";
    el.textContent = text;
    const time = document.createElement("span");
    time.className = "bubble-time";
    time.textContent = nowLabel();
    el.appendChild(time);
    chatArea.appendChild(el);
    scrollToBottom();
    return el;
  }

  function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function runAgentSteps() {
    const steps = [
      "🔒 Checking for personal info to protect…",
      "📚 Comparing against known scam patterns…",
      "🧠 Running risk analysis…",
    ];
    for (const step of steps) {
      const typing = addTypingIndicator();
      await wait(550 + Math.random() * 350);
      typing.remove();
      addBotBubble(step);
      await wait(120);
    }
    const finalTyping = addTypingIndicator();
    return finalTyping;
  }

  // ---------- Report rendering ----------
  function levelGradient(color) {
    return `linear-gradient(135deg, ${color}, ${color}CC)`;
  }

  function renderReport(data) {
    const card = document.createElement("div");
    card.className = "report-card";

    const head = document.createElement("div");
    head.className = "report-head";
    head.style.background = levelGradient(data.color);
    head.innerHTML = `
      <div class="verdict-emoji">${data.emoji}</div>
      <div>
        <div class="verdict-label">${data.label} · ${data.risk_level} RISK</div>
        <div class="verdict-sub">Scam Shield analysis</div>
      </div>
    `;
    card.appendChild(head);

    const body = document.createElement("div");
    body.className = "report-body";

    body.innerHTML += `
      <div class="confidence-row">
        <span>Confidence</span>
        <div class="confidence-track">
          <div class="confidence-fill" style="width:${data.confidence}%; background:${data.color}"></div>
        </div>
        <span>${data.confidence}%</span>
      </div>
    `;

    body.innerHTML += `
      <div class="report-section">
        <h4>WHY</h4>
        <div class="reasoning-text">${escapeHtml(data.reasoning)}</div>
      </div>
    `;

    if (data.risk_factors && data.risk_factors.length) {
      body.innerHTML += `
        <div class="report-section">
          <h4>RISK FACTORS</h4>
          <div class="chip-row">
            ${data.risk_factors.map((f) => `<span class="chip">${escapeHtml(f)}</span>`).join("")}
          </div>
        </div>
      `;
    }

    if (data.matched_patterns && data.matched_patterns.length) {
      body.innerHTML += `
        <div class="report-section">
          <h4>MATCHES KNOWN SCAM PATTERNS</h4>
          <div class="chip-row">
            ${data.matched_patterns
              .map((p) => `<span class="chip pattern">${escapeHtml(p.category)} · ${Math.round(p.similarity * 100)}%</span>`)
              .join("")}
          </div>
        </div>
      `;
    }

    if (data.privacy && data.privacy.pii_detected && data.privacy.pii_detected.length) {
      body.innerHTML += `
        <div class="report-section">
          <h4>PERSONAL INFO FOUND & REDACTED</h4>
          <div class="chip-row">
            ${data.privacy.pii_detected
              .map((t) => `<span class="chip">${escapeHtml(t.replace(/_/g, " "))}</span>`)
              .join("")}
          </div>
        </div>
      `;
    }

    body.innerHTML += `
      <div class="report-section">
        <h4>WHAT TO DO</h4>
        <ul class="action-list">
          ${data.recommended_actions.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}
        </ul>
      </div>
    `;

    body.innerHTML += `
      <div class="source-note">
        Analysis by ${data.analysis_source === "gemini" ? "Gemini AI + local rules" : "local rule-based engine (offline mode)"} ·
        redacted before analysis
      </div>
    `;

    card.appendChild(body);
    chatArea.appendChild(card);
    scrollToBottom();
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function addErrorBubble(msg) {
    const el = document.createElement("div");
    el.className = "error-bubble";
    el.textContent = msg;
    chatArea.appendChild(el);
    scrollToBottom();
  }

  // ---------- Autosize textarea ----------
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
  });

  // ---------- Submit handler ----------
  composer.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    sendBtn.disabled = true;
    const outgoing = addOutgoingBubble(text);
    input.value = "";
    input.style.height = "auto";

    await wait(200);
    upgradeTicks(outgoing, "delivered");

    // Fetch first so we know whether this is small talk (plain reply) or an
    // actual message to analyze (full pipeline animation), before deciding
    // what to show while we wait.
    let typing = addTypingIndicator();
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      upgradeTicks(outgoing, "read");

      if (!res.ok) {
        typing.remove();
        addErrorBubble(data.error || "Something went wrong. Please try again.");
      } else if (data.chat_reply) {
        // Small talk: no scam-pipeline steps, just a normal chat reply.
        await wait(400 + Math.random() * 300);
        typing.remove();
        addBotBubble(data.chat_reply);
      } else {
        // Real analysis: play the step-by-step pipeline animation, then the
        // friendly one-line summary, then the full report card.
        typing.remove();
        const finalTyping = await runAgentSteps();
        await wait(250);
        finalTyping.remove();
        if (data.chat_summary) addBotBubble(data.chat_summary);
        renderReport(data);
      }
    } catch (err) {
      typing.remove();
      addErrorBubble("Couldn't reach the analysis service. Is the server running?");
    } finally {
      sendBtn.disabled = false;
    }
  });
})();
