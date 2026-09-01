/* ==========================================================================
   AI-HMS — Floating AI chatbot widget (v2)
   Adds: typing indicator, quick-reply suggestion chips, unread badge,
   avatars, and a more polished, attractive panel.
   Include this script + call initChatbot() on any logged-in page.
   ========================================================================== */
function initChatbot() {
  if (document.getElementById("chatbot-toggle")) return; // already initialized

  const toggle = document.createElement("button");
  toggle.id = "chatbot-toggle";
  toggle.innerHTML = '<i class="bi bi-chat-dots-fill"></i><span id="chatbot-badge" class="d-none">1</span>';
  document.body.appendChild(toggle);

  const panel = document.createElement("div");
  panel.id = "chatbot-panel";
  panel.innerHTML = `
    <div id="chatbot-header">
      <div class="d-flex align-items-center gap-2">
        <div id="chatbot-avatar"><i class="bi bi-robot"></i></div>
        <div>
          <div class="fw-bold">AI-HMS Assistant</div>
          <div id="chatbot-status"><span class="chatbot-dot"></span> Online</div>
        </div>
      </div>
      <button id="chatbot-close" aria-label="Close"><i class="bi bi-x-lg"></i></button>
    </div>
    <div id="chatbot-messages"></div>
    <div id="chatbot-quick-replies"></div>
    <form id="chatbot-form">
      <input type="text" id="chatbot-input" placeholder="Type your message..." autocomplete="off" />
      <button type="submit" aria-label="Send"><i class="bi bi-send-fill"></i></button>
    </form>`;
  document.body.appendChild(panel);

  const messages = panel.querySelector("#chatbot-messages");
  const quickRepliesBox = panel.querySelector("#chatbot-quick-replies");
  let hasOpened = false;

  addBotMessage(messages, "Hi! I'm the AI-HMS assistant \u{1F44B} Ask me about appointments, symptoms, prescriptions, lab reports, or billing.");
  loadStarterSuggestions();

  toggle.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) {
      document.getElementById("chatbot-badge").classList.add("d-none");
      if (!hasOpened) {
        hasOpened = true;
        setTimeout(() => panel.querySelector("#chatbot-input").focus(), 200);
      }
    }
  });
  panel.querySelector("#chatbot-close").addEventListener("click", () => panel.classList.remove("open"));

  async function loadStarterSuggestions() {
    try {
      const res = await API.chatbotSuggestions();
      renderQuickReplies(res.suggestions);
    } catch (err) {
      renderQuickReplies(["Book an appointment", "Check my symptoms", "View my bills"]);
    }
  }

  function renderQuickReplies(options) {
    if (!options || options.length === 0) {
      quickRepliesBox.innerHTML = "";
      return;
    }
    quickRepliesBox.innerHTML = options.map(opt =>
      `<button type="button" class="chatbot-chip">${opt}</button>`).join("");
    quickRepliesBox.querySelectorAll(".chatbot-chip").forEach(chip => {
      chip.addEventListener("click", () => sendMessage(chip.textContent));
    });
  }

  async function sendMessage(text) {
    text = text.trim();
    if (!text) return;
    addUserMessage(messages, text);
    quickRepliesBox.innerHTML = "";
    const typingEl = addTypingIndicator(messages);

    try {
      const res = await API.chatbot(text);
      typingEl.remove();
      addBotMessage(messages, res.reply);
      renderQuickReplies(res.quick_replies);
    } catch (err) {
      typingEl.remove();
      addBotMessage(messages, "Sorry, I couldn't process that right now. Please try again.");
    }

    if (!panel.classList.contains("open")) {
      document.getElementById("chatbot-badge").classList.remove("d-none");
    }
  }

  panel.querySelector("#chatbot-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = panel.querySelector("#chatbot-input");
    const text = input.value;
    input.value = "";
    sendMessage(text);
  });
}

function addBotMessage(container, text) {
  const wrap = document.createElement("div");
  wrap.className = "chat-row bot";
  wrap.innerHTML = `
    <div class="chat-avatar bot-avatar"><i class="bi bi-robot"></i></div>
    <div class="chat-msg bot">${escapeHtml(text)}</div>`;
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function addUserMessage(container, text) {
  const wrap = document.createElement("div");
  wrap.className = "chat-row user";
  wrap.innerHTML = `<div class="chat-msg user">${escapeHtml(text)}</div>`;
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function addTypingIndicator(container) {
  const wrap = document.createElement("div");
  wrap.className = "chat-row bot";
  wrap.innerHTML = `
    <div class="chat-avatar bot-avatar"><i class="bi bi-robot"></i></div>
    <div class="chat-msg bot typing-indicator"><span></span><span></span><span></span></div>`;
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
  return wrap;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
