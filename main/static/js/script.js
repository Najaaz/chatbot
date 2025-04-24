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

    /**
     * 
     * @param {string} choice 
     * @description: handle the selection of the user from the options provided by the bot.
     * This function sends the selected option to the backend and receives a response.
     **/
    async function handleSelection(choice) {
        appendMessage('user', choice);
        scrollToBottom();
        clearOptions();
        showTyping(true);

        try {
            const res = await fetch('set-choice/', {
                method: 'POST',
                headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: choice })
            });
            const data = await res.json();
            showTyping(false);
            appendMessage('bot', data.message, data.options);
            scrollToBottom();

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
  
    /**
     * 
     * @param {string} who 
     * @param {string|string[]} text 
     * @param {string[]} options 
     * @description: Appends a message (or messages) to the chat interface, and optionally displays selectable options.
     */
    function appendMessage(who, text, options) {

        // Check if the message is a string or a list of strings
        if (typeof text === 'string') {
            const msgEl = document.createElement('div');
            msgEl.classList.add('message', who);
            msgEl.innerHTML = `
                <div class="bubble px-4 py-2 ${who === 'user' ? 'text-end' : ''}">
                    ${text}
                </div>`;
            chatMsg.appendChild(msgEl);

        } else if (Array.isArray(text)) {
            text.forEach(t => {
                const msgEl = document.createElement('div');
                // for all messages except the last one, add a class of 'message'
                if (text.indexOf(t) !== text.length - 1) {
                    msgEl.classList.add('message', who, 'm-0');
                } else {
                    msgEl.classList.add('message', who);
                }

                msgEl.innerHTML = `
                    <div class="bubble px-4 py-2 ${who === 'user' ? 'text-end' : ''}">
                        ${t}
                    </div>`;
                chatMsg.appendChild(msgEl);
            });
        }

        // If options are provided, show them as clickable bubbles
        if (Array.isArray(options) && options.length) {
            showOptions(options);
        } else {
            disableInput(false);
            input.focus();
        }
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
  