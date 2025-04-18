// script.js
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('chat-toggle-button');
    const chatWin   = document.getElementById('chat-window');
    const closeBtn  = document.getElementById('chat-close');
    const form      = document.getElementById('chat-form');
    const input     = document.getElementById('chat-input');
    const body      = document.getElementById('chat-body');
    const chatMsg   = document.getElementById('chat-messages');
    const typing    = document.getElementById('typing-indicator');
    const optionsEl = document.getElementById('chat-options');

    let firstOpened = false;
  
    // open
    toggleBtn.addEventListener('click', () => {
        chatWin.classList.add('show');
        toggleBtn.classList.add('hide');
        if (!firstOpened) {
            firstOpened = true;
            startConversation();
        }
    });
  
    // close
    closeBtn.addEventListener('click', () => {
        chatWin.classList.remove('show');
        toggleBtn.classList.remove('hide');
    });

    function startConversation() {
        appendMessage('bot', 'Hi there! How would you like the conversation to go?');
        scrollToBottom();
        showOptions(['Guided Questions', 'Free Flow']);
        disableInput(true);
    }

    // ── enable / disable input box ──
    function disableInput(on) {
        input.disabled = on;
    }

    // ── show clickable bubbles ──
    function showOptions(arr) {
        optionsEl.innerHTML = '';
        arr.forEach(text => {
        const btn = document.createElement('div');
        btn.classList.add('option-bubble');
        btn.textContent = text;
        btn.addEventListener('click', () => handleSelection(text));
        optionsEl.appendChild(btn);
        });
        optionsEl.style.display = 'flex';
    }

    function clearOptions() {
        optionsEl.style.display = 'none';
        optionsEl.innerHTML = '';
    }

    // OPTION 1: user picks a bubble 
    async function handleSelection(choice) {
        appendMessage('user', choice);
        scrollToBottom();
        clearOptions();

        // if free‑flow, show text input and bail
        if (choice === 'Free Flow') {
            disableInput(false);
            input.focus();
            return;
        }

        // guided path → send to backend
        showTyping(true);
        try {
            const res = await fetch('/', {
                method: 'POST',
                headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: choice })
            });
            const data = await res.json();
            showTyping(false);
            appendMessage('bot', data.reply);
            scrollToBottom();

            // if backend returns more options:
            if (Array.isArray(data.options) && data.options.length) {
                showOptions(data.options);
            } else {
                disableInput(false);
                input.focus();
            }

        } catch (err) {
            showTyping(false);
            appendMessage('bot', 'Sorry, something went wrong.');
            disableInput(false);
            scrollToBottom();
        }
    }
  
    // OPTION 2: (Free flow text) send message
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const msg = input.value.trim();
        if (!msg) return;
    
        appendMessage('user', msg);
        input.value = '';
        scrollToBottom();
        showTyping(true);
    
        try {
            const res = await fetch('/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            showTyping(false);
            appendMessage('bot', data.reply);
            scrollToBottom();

            if (Array.isArray(data.options) && data.options.length) {
                showOptions(data.options);
            } else {
                disableInput(false);
                input.focus();
            }
        } catch (err) {
            showTyping(false);
            appendMessage('bot', 'Sorry, something went wrong.');
            disableInput(false);
            scrollToBottom();
            console.error(err);
        }
    });
  
    function appendMessage(who, text) {
        const msgEl = document.createElement('div');
        msgEl.classList.add('message', who);
        msgEl.innerHTML = `
            <div class="bubble px-4 py-2 ${who === 'user' ? 'text-end' : ''}">
                ${text}
            </div>`;
        chatMsg.appendChild(msgEl);
    }
  
    function scrollToBottom() {
        body.scrollTop = body.scrollHeight;
    }
  
    function showTyping(on) {
        typing.classList.toggle('d-none', !on);
    }
  
    // helper to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            document.cookie.split(';').forEach(c => {
                const [key, val] = c.trim().split('=');
                if (key === name) { cookieValue = decodeURIComponent(val); }
            });
        }
        return cookieValue;
    }
});
  