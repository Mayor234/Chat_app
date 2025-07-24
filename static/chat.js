const socket = io();

let myId = null;
let selectedUser = null;

const userIdDisplay = document.getElementById("user-id");
const usernameInput = document.getElementById("usernameInput");
const setUsernameBtn = document.getElementById("setUsernameBtn");
const userListDiv = document.getElementById("userList");
const chatHeader = document.getElementById("chatHeader");
const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// Assign unique ID
socket.on("assign_id", (id) => {
  myId = id;
  userIdDisplay.textContent = `Your ID: ${id}`;
});

// Set your username
setUsernameBtn.onclick = () => {
  const username = usernameInput.value.trim();
  if (username) {
    socket.emit("set_username", username);
    setUsernameBtn.disabled = true;
    usernameInput.disabled = true;
  }
};

// Show all users
socket.on("user_list", (users) => {
  userListDiv.innerHTML = "";

  users.forEach((user) => {
    if (user.id === myId) return;

    const userDiv = document.createElement("div");
    userDiv.className = "user-entry";
    userDiv.textContent = `${user.username} (${user.id})`;
    userDiv.dataset.userid = user.id;

    userDiv.onclick = () => {
      selectedUser = user;
      chatHeader.textContent = `Chatting with: ${user.username}`;
      chatBox.innerHTML = "";
      socket.emit("load_history", { with: user.id });

      // Clear unread indicators
      const entry = document.querySelector(`[data-userid="${user.id}"]`);
      if (entry) {
        entry.style.fontWeight = "normal";
        const dot = entry.querySelector(".unread-dot");
        if (dot) dot.remove();
      }
    };

    userListDiv.appendChild(userDiv);
  });
});

// Send a message
sendBtn.onclick = () => {
  const message = messageInput.value.trim();
  if (message && selectedUser) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    socket.emit("send_message", {
      to: selectedUser.id,
      message: message
    });

    appendMessage(`You: ${message}`, false, time, "sent");

    messageInput.value = "";
    messageInput.focus();
  }
};

// Receive a message
socket.on("receive_message", (data) => {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (selectedUser && data.from_id === selectedUser.id) {
    appendMessage(`${data.from}: ${data.message}`, true, time, "received");
  } else {
    alert(`📩 New message from ${data.from}`);

    const target = document.querySelector(`[data-userid="${data.from_id}"]`);
    if (target) {
      target.style.fontWeight = "bold";
      if (!target.querySelector(".unread-dot")) {
        const dot = document.createElement("span");
        dot.className = "unread-dot";
        target.appendChild(dot);
      }
    }
  }
});

// Load chat history
socket.on("chat_history", (messages) => {
  messages.forEach((msg) => {
    const type = msg.from_id === myId ? "sent" : "received";
    appendMessage(`${msg.from}: ${msg.message}`, msg.is_read, msg.timestamp, type);
  });
});

// Append message to chat
function appendMessage(text, isRead, time, type) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${type}`;

  const messageContent = document.createElement("div");
  messageContent.className = "message-text";

  const messageTextOnly = document.createElement("span");
  messageTextOnly.textContent = text;

  const timeSpan = document.createElement("span");
  timeSpan.className = "timestamp";
  timeSpan.textContent = ` ${time} ${type === "sent" ? (isRead ? "✔✔" : "✔") : ""}`;

  messageContent.appendChild(messageTextOnly);
  messageContent.appendChild(timeSpan);
  msgDiv.appendChild(messageContent);

  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}


// Send on Enter
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendBtn.click();
  }
});
