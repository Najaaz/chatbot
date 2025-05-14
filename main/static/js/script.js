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
        showOptions(['Guided Questions', 'Free Flow'], handleSelection);
        disableInput(true);
    }

    // ── enable / disable input box ──
    function disableInput(on) {
        input.value = '';
        input.disabled = on;
    }

    // ── show clickable bubbles ──
    function showOptions(arr, functionName) {
        optionsEl.innerHTML = '';
        arr.forEach(text => {
            const btn = document.createElement('div');
            btn.classList.add('option-bubble');
            btn.textContent = text;
            btn.addEventListener('click', () => functionName(text));
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
            console.log(data);
            showTyping(false);
            appendMessage('bot', data.response, data.options, data.results);
            scrollToBottom();

        } catch (err) {
            console.error(err);
            showTyping(false);
            appendMessage('bot', 'Sorry, something went wrong.');
            disableInput(false);
            scrollToBottom();
        }
    }

    async function feedbackHandler(message) {
        appendMessage('user', message);
        showTyping(true);
        scrollToBottom();
        clearOptions();

        try {
            const res = await fetch('chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: message })
            });
            const data = await res.json();
            console.log(data);
            showTyping(false);
            appendMessage('bot', data.response, data.options, data.results);
            scrollToBottom();

        } catch (err) {
            console.error(err);
            showTyping(false);
            appendMessage('bot', 'Sorry, we are unable to process your request at the moment.');
            disableInput(false);
            scrollToBottom();
        }

        if (["reset", "clear", "restart", "start over", "new", "new chat", "new conversation"].includes(message.toLowerCase())) {
            console.log('resetting conversation...');
            appendMessage('user', message);
            appendMessage('bot', "Sure! Starting a new conversation.");
            startConversation();
            return;
        }
    }

    // ── send message ──
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (message) {
            feedbackHandler(message);
        }
    });

  
    /**
     * 
     * @param {string} who 
     * @param {string|string[]} text 
     * @param {string[]} options 
     * @description: Appends a message (or messages) to the chat interface, and optionally displays selectable options.
     */
    function appendMessage(who, text, options, results) {

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

        // If results are provided, show them as clickable cards
        if (Array.isArray(results) && results.length > 0 && who === 'bot') {
            showResults(results);
        }

        // If options are provided, show them as clickable bubbles
        if (Array.isArray(options) && options.length > 0 && who === 'bot') {
            disableInput(true);
            showOptions(options, feedbackHandler);
        } else {
            disableInput(false);
            input.focus();
        }
    }

    function showResults(results) {
        const resultsEl = document.createElement('div');
        resultsEl.classList.add('d-flex', 'flex-nowrap', 'gap-3', 'overflow-auto', 'pb-1', 'mb-2');
        results.forEach(result => {
            const card = document.createElement('div');
            card.classList.add('card', 'product-card', 'shadow-sm');
            card.innerHTML = `
                <img src="${result.image}" class="card-img-top" alt="${result.name}">
                <div class="card-body p-2">
                    <h6 class="card-title mb-1 text-truncate">${result.name}</h6>
                    <p class="card-text text-danger fw-bold mb-1">Rs. ${Number(result.current_price).toLocaleString('en-IN')}</p>
                    <a href="${result.url}" target="_blank" class="btn btn-sm btn-pink w-100">View Product</a>
                </div>`;
            resultsEl.appendChild(card);
        });
        chatMsg.appendChild(resultsEl);
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



    // ── Privacy Consent Check ──
    const consentBanner = document.getElementById('privacy-consent');
    const acceptButton = document.getElementById('accept-privacy');

    // Hide chatbot toggle button until consent is given
    if (!localStorage.getItem('privacyAccepted')) {
        document.getElementById('chat-toggle-button').style.display = 'none';
        consentBanner.style.display = 'flex';
    } else {
        consentBanner.style.display = 'none';
    }

    // Accept consent
    acceptButton.addEventListener('click', () => {
        console.log(consentBanner);
        localStorage.setItem('privacyAccepted', 'true');
        consentBanner.style.display = 'none';
        document.getElementById('chat-toggle-button').style.display = 'flex';
    });

});
  