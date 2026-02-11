// ──────────────────────────────────────────
// CardSenseAI – Chat Script
// ──────────────────────────────────────────

const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

let isProcessing = false;

// ─── Init ────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadInitialMessage();
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Handle chip clicks (Yes/No options)
    chatContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('chip')) {
            const text = e.target.textContent;
            userInput.value = text;
            sendMessage();
        }
    });
});

// ─── Load initial bot greeting ───────────
function loadInitialMessage() {
    // The server sends the initial message on page load via /reset or session
    fetch('/reset', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            chatContainer.innerHTML = '';
            appendMessage('assistant', data.response);
        })
        .catch(() => {
            appendMessage('assistant', '👋 Hi! I\'m your Smart Credit Card Advisor. What is your monthly take-home income?');
        });
}

// ─── Send Message ────────────────────────
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    userInput.value = '';

    // Append user message
    appendMessage('user', text);

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        if (data.response) {
            appendMessage('assistant', data.response);
        } else if (data.error) {
            appendMessage('assistant', '⚠️ Something went wrong. Please try again.');
        }
    } catch (err) {
        typingEl.remove();
        appendMessage('assistant', '⚠️ Connection error. Please check if the server is running.');
    }

    isProcessing = false;
    sendBtn.disabled = false;
    userInput.focus();
}

// ─── Append Message ──────────────────────
function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'assistant' ? '💳' : '👤';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (role === 'assistant') {
        // Render markdown
        contentDiv.innerHTML = marked.parse(content, {
            breaks: true,
            gfm: true
        });
    } else {
        contentDiv.textContent = content;
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);

    // Scroll to bottom
    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
}

// ─── Typing Indicator ────────────────────
function showTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.className = 'typing-indicator';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '💳';
    avatar.style.background = 'linear-gradient(135deg, rgba(240,180,41,0.15), rgba(240,180,41,0.08))';
    avatar.style.border = '1px solid rgba(240,180,41,0.2)';

    const dots = document.createElement('div');
    dots.className = 'typing-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';

    wrapper.appendChild(avatar);
    wrapper.appendChild(dots);
    chatContainer.appendChild(wrapper);

    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });

    return wrapper;
}

// ─── Reset Chat ──────────────────────────
async function resetChat() {
    try {
        const res = await fetch('/reset', { method: 'POST' });
        const data = await res.json();

        chatContainer.innerHTML = '';
        appendMessage('assistant', data.response);
        userInput.value = '';
        userInput.focus();
    } catch (err) {
        appendMessage('assistant', '⚠️ Could not reset. Please refresh the page.');
    }

    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
}

// ─── Mobile Sidebar Toggle ──────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
}
