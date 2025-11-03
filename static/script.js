// elements
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");
const newChatBtn = document.getElementById("newChatBtn");
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileNameDisplay");
const chatList = document.getElementById("chatList");
const themeToggle = document.getElementById("themeToggle");

let chats = {};
let currentChatId = null;

// show selected file name
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = `📎 ${fileInput.files[0].name}`;
  } else {
    fileNameDisplay.textContent = "";
  }
});

// append message
function appendMessage(sender, text, senderClass) {
  const message = document.createElement("div");
  message.classList.add("message", senderClass);

  // Clean markdown bullets and bold
  let cleanText = text
    .replace(/\*\*/g, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .trim();

  message.innerHTML = `<strong>${sender}:</strong> ${cleanText.replace(/\n/g, "<br>")}`;
  chatBox.appendChild(message);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// render chat list with dropdown
// render chat list with dropdown
function renderChatList() {
  chatList.innerHTML = "";
  Object.keys(chats).forEach((id) => {
    const chat = chats[id];
    const item = document.createElement("div");
    item.className = "chat-item";
    if (id === currentChatId) item.classList.add("active");

    item.innerHTML = `
      <span class="chat-title">${chat.title}</span>
      <div class="chat-menu">
        <span class="chat-ellipsis">...</span>
        <div class="chat-dropdown">
          <button class="small-rename" data-id="${id}">Rename</button>
          <button class="small-delete" data-id="${id}">Delete</button>
        </div>
      </div>
    `;

    const ellipsis = item.querySelector(".chat-ellipsis");
    const dropdown = item.querySelector(".chat-dropdown");

    // Toggle dropdown on ellipsis click
    ellipsis.addEventListener("click", (e) => {
      e.stopPropagation(); // prevent loading chat
      // close other dropdowns
      document.querySelectorAll(".chat-dropdown.show").forEach(d => {
        if (d !== dropdown) d.classList.remove("show");
      });
      dropdown.classList.toggle("show");
    });

    // Rename & Delete buttons
    dropdown.querySelector(".small-rename").addEventListener("click", (e) => {
      e.stopPropagation();
      renameChat(id);
      dropdown.classList.remove("show");
    });
    dropdown.querySelector(".small-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteChat(id);
      dropdown.classList.remove("show");
    });

    // Clicking the item itself loads the chat
    item.addEventListener("click", () => {
      currentChatId = id;
      loadChat(id);
    });

    chatList.appendChild(item);
  });
}

// Close dropdowns if you click anywhere else
document.addEventListener("click", () => {
  document.querySelectorAll(".chat-dropdown.show").forEach(d => d.classList.remove("show"));
});



// load chat
function loadChat(id) {
  currentChatId = id;
  chatBox.innerHTML = "";
  chats[id].messages.forEach((m) =>
    appendMessage(m.sender, m.text, m.sender === "You" ? "user" : "ai")
  );
  renderChatList();
}

// rename chat
function renameChat(id) {
  const newName = prompt("Rename chat:", chats[id].title);
  if (newName && newName.trim()) {
    chats[id].title = newName.trim();
    renderChatList();
  }
}

// delete chat
function deleteChat(id) {
  if (!confirm("Delete this chat?")) return;
  delete chats[id];
  if (currentChatId === id) {
    currentChatId = null;
    chatBox.innerHTML = "";
  }
  renderChatList();
}

// create new chat
async function createNewChat() {
  try {
    const res = await fetch("/new_chat", { method: "POST" });
    const data = await res.json();
    const id = data.chat_id || "chat_" + Math.random().toString(36).slice(2, 10);
    chats[id] = { title: data.title || `Chat ${Object.keys(chats).length + 1}`, messages: [] };
    currentChatId = id;
  } catch {
    const id = "chat_" + Math.random().toString(36).slice(2, 10);
    chats[id] = { title: `Chat ${Object.keys(chats).length + 1}`, messages: [] };
    currentChatId = id;
  }
  chatBox.innerHTML = "";
  userInput.value = "";
  fileInput.value = "";
  fileNameDisplay.textContent = "";
  renderChatList();
}

// new chat button
newChatBtn.addEventListener("click", createNewChat);

// send message
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = userInput.value.trim();
  const file = fileInput.files[0];
  if (!text && !file) return;

  let userMessageText = text;
  if (file) {
  const fileURL = URL.createObjectURL(file);
  const fileDisplay = `<a href="${fileURL}" target="_blank" style="text-decoration:none;color:#4da3ff;">📎 ${file.name}</a>`;
  userMessageText = text ? `${text}<br>${fileDisplay}` : fileDisplay;
}


  appendMessage("You", userMessageText, "user");

  let body, headers = {};
  if (file) {
    body = new FormData();
    body.append("message", text);
    body.append("chat_id", currentChatId || "");
    body.append("file", file);
  } else {
    body = JSON.stringify({ message: text, chat_id: currentChatId || "" });
    headers["Content-Type"] = "application/json";
  }

  userInput.value = "";
  fileInput.value = "";
  fileNameDisplay.textContent = "";

  try {
    const res = await fetch("/ask", { method: "POST", headers, body });
    if (!res.ok) return appendMessage("ASK AI", `Error: ${res.statusText}`, "ai");

    const data = await res.json();
    currentChatId = data.chat_id;

    if (!chats[currentChatId]) {
      chats[currentChatId] = { title: data.title || "Chat", messages: [] };
    }

    chats[currentChatId].messages.push({ sender: "You", text: userMessageText });
    chats[currentChatId].messages.push({ sender: "ASK AI", text: data.reply });

    appendMessage("ASK AI", data.reply, "ai");
    renderChatList();
  } catch (err) {
    appendMessage("ASK AI", "Request failed.", "ai");
    console.error(err);
  }
});

// theme toggle
themeToggle?.addEventListener("click", () => {
  const isDark = document.body.classList.toggle("dark-mode");
  themeToggle.textContent = isDark ? "🌞" : "🌙";
  localStorage.setItem("theme", isDark ? "dark" : "light");
});

// apply saved theme
(function applySavedTheme() {
  const saved = localStorage.getItem("theme");
  if (saved === "dark") {
    document.body.classList.add("dark-mode");
    if (themeToggle) themeToggle.textContent = "🌞";
  } else {
    if (themeToggle) themeToggle.textContent = "🌙";
  }
})();

// initialize first chat
createNewChat();
