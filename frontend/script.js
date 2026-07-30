/**
 * AI Candidate Representative (Mithun KV) - Frontend Client with Debug Logging
 */

const API_BASE_URL = "http://127.0.0.1:5002";

let isStreaming = false;

// DOM Selectors
const candidateCard = document.getElementById("candidate-card");
const candName = document.getElementById("cand-name");
const candLocation = document.getElementById("cand-location");
const candGithub = document.getElementById("cand-github");
const candLinkedin = document.getElementById("cand-linkedin");
const candSkillsChips = document.getElementById("cand-skills-chips");

const jdInput = document.getElementById("jd-input");
const matchBtn = document.getElementById("match-btn");
const matchResultsCard = document.getElementById("match-results-card");
const matchPercentage = document.getElementById("match-percentage");
const matchBadge = document.getElementById("match-badge");
const matchStrengths = document.getElementById("match-strengths");
const matchMissing = document.getElementById("match-missing");

const chatMessages = document.getElementById("chat-messages");
const welcomeView = document.getElementById("welcome-view");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");

document.addEventListener("DOMContentLoaded", () => {
    console.log("[App Init] Initializing AI Representative frontend...");
    setupEventListeners();
    fetchCandidateProfile();
});

function setupEventListeners() {
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = `${userInput.scrollHeight}px`;
        sendBtn.disabled = !userInput.value.trim() || isStreaming;
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                chatForm.dispatchEvent(new Event("submit"));
            }
        }
    });

    chatForm.addEventListener("submit", handleChatSubmit);

    document.querySelectorAll(".prompt-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const prompt = chip.getAttribute("data-prompt");
            console.log(`[Prompt Chip Clicked] Preset query selected: "${prompt}"`);
            userInput.value = prompt;
            userInput.dispatchEvent(new Event("input"));
            chatForm.dispatchEvent(new Event("submit"));
        });
    });

    matchBtn.addEventListener("click", handleJdMatch);

    newChatBtn.addEventListener("click", () => {
        console.log("[Chat Reset] Clearing active conversation view.");
        chatMessages.innerHTML = "";
        chatMessages.appendChild(welcomeView);
        welcomeView.classList.remove("hidden");
    });
}

// ---------------------------------------------------------------------------
// Auto-Fetch Profile on Startup
// ---------------------------------------------------------------------------
async function fetchCandidateProfile() {
    console.log(`[HTTP GET] Fetching profile from ${API_BASE_URL}/profile...`);
    try {
        const response = await fetch(`${API_BASE_URL}/profile`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const profile = await response.json();
        console.log("[HTTP GET Success] Loaded profile data:", profile);

        renderCandidateProfile(profile);

        userInput.disabled = false;
        userInput.placeholder = "Ask anything about Mithun's projects or skills...";
    } catch (err) {
        console.error("[HTTP GET Error] Failed to fetch profile:", err);
    }
}

function renderCandidateProfile(profile) {
    if (!profile) return;

    candidateCard.classList.remove("hidden");
    candName.textContent = profile.name || "Mithun KV";
    candLocation.innerHTML = `<i data-lucide="map-pin"></i> ${profile.location || "Bengaluru, India"}`;

    if (profile.github) {
        candGithub.href = profile.github;
        candGithub.style.display = "inline-flex";
    }
    if (profile.linkedin) {
        candLinkedin.href = profile.linkedin;
        candLinkedin.style.display = "inline-flex";
    }

    candSkillsChips.innerHTML = "";
    const allSkills = [...(profile.technical_skills || []), ...(profile.additional_skills || [])];
    allSkills.slice(0, 8).forEach((skill) => {
        const chip = document.createElement("span");
        chip.className = "skill-chip";
        chip.textContent = skill;
        candSkillsChips.appendChild(chip);
    });

    if (window.lucide) window.lucide.createIcons();
    console.log("[UI Update] Rendered candidate card with skills chips.");
}

// ---------------------------------------------------------------------------
// Chat Streaming via SSE
// ---------------------------------------------------------------------------
async function handleChatSubmit(e) {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query || isStreaming) return;

    console.log(`[Chat Submit] User prompt: "${query}"`);
    welcomeView.classList.add("hidden");
    appendMessage(query, "user");

    userInput.value = "";
    userInput.style.height = "auto";
    sendBtn.disabled = true;

    const assistantBubble = createAssistantMessageContainer();
    isStreaming = true;

    try {
        console.log(`[HTTP POST] Initiating chat stream at ${API_BASE_URL}/chat...`);
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: query }),
        });

        if (!response.ok) throw new Error(`Server returned HTTP status ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let assistantReply = "";
        let chunksReceived = 0;

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                console.log(`[Stream Complete] Finished receiving stream after ${chunksReceived} chunks.`);
                break;
            }

            chunksReceived++;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.replace("data: ", "").trim();
                    if (!jsonStr) continue;

                    try {
                        const payload = JSON.parse(jsonStr);
                        if (payload.token) {
                            assistantReply += payload.token;
                            renderAssistantReply(assistantBubble, assistantReply);
                            scrollToBottom();
                        } else if (payload.done) {
                            console.log("[Stream Done Event] Payload signals stream completion.");
                            isStreaming = false;
                        } else if (payload.error) {
                            console.error("[Stream Error Event]:", payload.error);
                            throw new Error(payload.error);
                        }
                    } catch (err) {
                        // Handle partial boundaries silently
                    }
                }
            }
        }
    } catch (err) {
        console.error("[Chat Error]:", err);
        renderAssistantReply(assistantBubble, "I don't have enough information to answer that.");
    } finally {
        isStreaming = false;
        assistantBubble.classList.remove("typing-cursor");
        sendBtn.disabled = !userInput.value.trim();
        scrollToBottom();
    }
}

function appendMessage(text, role) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = role === "user" ? '<i data-lucide="user"></i>' : '<i data-lucide="bot"></i>';

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (role === "assistant") {
        renderAssistantReply(bubble, text);
    } else {
        bubble.textContent = text;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);

    if (window.lucide) window.lucide.createIcons();
    scrollToBottom();
}

function createAssistantMessageContainer() {
    const row = document.createElement("div");
    row.className = "message-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = '<i data-lucide="bot"></i>';

    const bubble = document.createElement("div");
    bubble.className = "bubble typing-cursor";

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);

    if (window.lucide) window.lucide.createIcons();
    scrollToBottom();

    return bubble;
}

function renderAssistantReply(container, text) {
    container.innerHTML = "";
    container.appendChild(formatAssistantReply(text));
}

function formatAssistantReply(text) {
    const wrapper = document.createElement("div");
    wrapper.className = "assistant-content";

    const normalizedText = normalizeAssistantText(text);
    const lines = normalizedText.split("\n").map((line) => line.trim()).filter(Boolean);
    let activeList = null;

    lines.forEach((line) => {
        const numberedMatch = line.match(/^(\d+)\.\s+(.*)$/);
        const bulletMatch = line.match(/^[-•]\s+(.*)$/);

        if (numberedMatch || bulletMatch) {
            const listType = numberedMatch ? "ol" : "ul";
            if (!activeList || activeList.tagName.toLowerCase() !== listType) {
                activeList = document.createElement(listType);
                wrapper.appendChild(activeList);
            }

            const li = document.createElement("li");
            appendInlineFormattedText(li, numberedMatch ? numberedMatch[2] : bulletMatch[1]);
            activeList.appendChild(li);
            return;
        }

        activeList = null;
        const paragraph = document.createElement("p");
        appendInlineFormattedText(paragraph, line);
        wrapper.appendChild(paragraph);
    });

    if (!wrapper.children.length) {
        const paragraph = document.createElement("p");
        paragraph.textContent = text;
        wrapper.appendChild(paragraph);
    }

    return wrapper;
}

function normalizeAssistantText(text) {
    return text
        .replace(/\r/g, "")
        .replace(/\s+(\d+\.\s+\*\*)/g, "\n$1")
        .replace(/\s+(\d+\.\s+)/g, "\n$1")
        .replace(/\s+([-•]\s+)/g, "\n$1")
        .replace(/:\s+(?=\d+\.\s)/g, ":\n")
        .replace(/:\s+(?=[-•]\s+)/g, ":\n")
        .trim();
}

function appendInlineFormattedText(parent, text) {
    const segments = text.split(/(\*\*[^*]+\*\*)/g);

    segments.forEach((segment) => {
        if (!segment) return;

        if (segment.startsWith("**") && segment.endsWith("**")) {
            const strong = document.createElement("strong");
            appendLinkedText(strong, segment.slice(2, -2));
            parent.appendChild(strong);
        } else {
            appendLinkedText(parent, segment);
        }
    });
}

function appendLinkedText(parent, text) {
    const linkRegex = /(\[[^\]]+\]\(https?:\/\/[^)]+\)|https?:\/\/[^\s<]+)/g;
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            parent.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
        }

        const rawLink = match[0];
        const markdownMatch = rawLink.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);
        const cleanedLink = markdownMatch ? null : cleanTrailingPunctuation(rawLink);
        const linkText = markdownMatch ? markdownMatch[1] : cleanedLink.text;
        const href = markdownMatch ? markdownMatch[2] : cleanedLink.href;

        const link = document.createElement("a");
        link.href = href;
        link.textContent = linkText;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        parent.appendChild(link);

        if (cleanedLink?.trailing) {
            parent.appendChild(document.createTextNode(cleanedLink.trailing));
        }

        lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < text.length) {
        parent.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
}

function cleanTrailingPunctuation(url) {
    const trailingMatch = url.match(/[).,;:!?]+$/);
    const trailing = trailingMatch ? trailingMatch[0] : "";
    const href = trailing ? url.slice(0, -trailing.length) : url;

    return {
        href,
        text: href,
        trailing,
    };
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ---------------------------------------------------------------------------
// Job Description Fit Analysis
// ---------------------------------------------------------------------------
async function handleJdMatch() {
    const jdText = jdInput.value.trim();
    if (!jdText) {
        alert("Please paste a Job Description.");
        return;
    }

    console.log(`[JD Match] Initiating evaluation for JD (${jdText.length} characters)...`);
    matchBtn.disabled = true;
    matchBtn.textContent = "Evaluating Fit...";

    try {
        const response = await fetch(`${API_BASE_URL}/match`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jd_text: jdText }),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Match failed");

        console.log("[JD Match Success] Result:", data);
        renderMatchResults(data);
    } catch (err) {
        console.error("[JD Match Error]:", err);
        alert(`Error: ${err.message}`);
    } finally {
        matchBtn.disabled = false;
        matchBtn.innerHTML = '<i data-lucide="git-compare"></i> Compare Fit';
        if (window.lucide) window.lucide.createIcons();
    }
}

function renderMatchResults(data) {
    matchResultsCard.classList.remove("hidden");
    matchPercentage.textContent = `${data.match_percentage || 0}%`;
    matchBadge.textContent = data.hiring_recommendation || "Evaluated";

    matchStrengths.innerHTML = "";
    (data.strengths || []).forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        matchStrengths.appendChild(li);
    });

    matchMissing.innerHTML = "";
    (data.missing_skills || []).forEach((m) => {
        const li = document.createElement("li");
        li.textContent = m;
        matchMissing.appendChild(li);
    });
}
