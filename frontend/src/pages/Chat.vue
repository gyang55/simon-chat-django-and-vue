<template>
  <div class="app-shell">
    <aside class="sidebar">
      <!-- top -->
      <div class="sidebar-top">
        <div class="sidebar-header">
          <Aperture class="brand-icon" />
          <button class="new-chat-btn" @click="createChat">
            <span class="plus">＋</span>
            <span>New chat</span>
          </button>
        </div>

        <!-- chat list -->
        <div class="chat-list">
          <div
            v-for="c in chats"
            :key="c.id"
            class="chat-item"
            :class="{ active: selectedChat?.id === c.id }"
            @click="selectChat(c)"
          >
            <div class="chat-row">
              <div class="chat-text">
                <div class="chat-title">{{ c.title || "Untitled" }}</div>
                <div class="chat-meta">#{{ c.id }}</div>
              </div>

              <button
                class="icon-btn"
                type="button"
                title="Delete chat"
                @click.stop="deleteChat(c)"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- bottom -->
      <div class="sidebar-bottom">
        <button class="logout-btn" @click="logout">Logout</button>
      </div>
    </aside>

    <main class="main">
      <div class="main-header">
        <div class="title">
          <div class="title-h1">
            {{ selectedChat ? `Chat #${selectedChat.id}` : "Select a chat" }}
          </div>
        </div>
      </div>

      <div class="chat-panel" v-if="selectedChat">
        <div class="messages" ref="msgWrap">
          <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
            <div class="bubble">
              <div class="role">{{ m.role }}</div>
              <div class="content">{{ m.content }}</div>
            </div>
          </div>
        </div>

        <form class="composer" @submit.prevent="sendMessage">
          <div class="composer-inner">
            <input
              v-model="input"
              class="composer-input"
              placeholder="Message Simon Chat..."
            />
            <button class="btn btn-primary" :disabled="!input.trim()">
              Send
            </button>
          </div>
          <div class="composer-hint">
            Enter to send · Shift+Enter for newline
          </div>
        </form>

        <p v-if="error" class="error">{{ error }}</p>
      </div>

      <div v-else class="empty-state">
        <div class="empty-card">
          <div class="empty-title">Welcome 👋</div>
          <div class="empty-sub">
            Create a new chat or select one from the left.
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { api } from "../lib/api.js";
import { streamChat } from "../lib/stream.js";
import { Aperture } from "lucide-vue-next";

export default {
  components: {
    Aperture,
  },
  data() {
    return {
      chats: [],
      selectedChat: null,
      messages: [],
      input: "",
      error: "",
    };
  },
  async mounted() {
    await this.loadChats();
  },
  methods: {
    async loadChats() {
      this.error = "";
      try {
        const res = await api.get("/api/chats/");
        this.chats = res.data;
      } catch (e) {
        this.error = "Failed to load chats (are you logged in?)";
      }
    },
    async createChat() {
      this.error = "";
      try {
        const res = await api.post("/api/chats/", { title: "New chat" });
        this.chats.unshift(res.data);
        this.selectChat(res.data);
      } catch (e) {
        this.error = "Failed to create chat";
      }
    },
    async selectChat(chat) {
      this.selectedChat = chat;
      await this.loadMessages(chat.id);
    },
    async loadMessages(chatId) {
      this.error = "";
      try {
        const res = await api.get(`/api/chats/${chatId}/messages/`);
        this.messages = res.data;
      } catch (e) {
        this.error = "Failed to load messages";
      }
    },
    async sendMessage() {
      if (!this.selectedChat) return;

      const text = this.input.trim();
      if (!text) return;

      this.input = "";
      this.error = "";

      // 1) Add user message locally
      this.messages.push({
        id: Date.now(),
        role: "user",
        content: text,
      });

      // 2) Add ONE assistant placeholder
      this.messages.push({
        id: Date.now() + 1,
        role: "assistant",
        content: "",
      });

      const idx = this.messages.length - 1;

      const token = localStorage.getItem("access_token");
      const base = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

      try {
        await streamChat({
          url: `${base}/api/chats/${this.selectedChat.id}/stream/`,
          token,
          body: { content: text },

          onDelta: (delta) => {
            this.messages[idx].content += delta;
          },

          onDone: async () => {
            // OPTIONAL: only reload if backend already saved the messages
            // otherwise it will "erase" your local ones
            // const res = await api.get(`/api/chats/${this.selectedChat.id}/messages/`);
            // this.messages = res.data;
          },
        });
      } catch (e) {
        this.error = e.message || "Streaming failed";
      }
    },
    async deleteChat(chat) {
      if (!confirm(`Delete chat "${chat.title || "Untitled"}"?`)) return;

      this.error = "";
      try {
        await api.delete(`/api/chats/${chat.id}/`);
        this.chats = this.chats.filter((c) => c.id !== chat.id);

        if (this.selectedChat?.id === chat.id) {
          this.selectedChat = null;
          this.messages = [];
        }
      } catch (e) {
        this.error = "Failed to delete chat";
      }
    },

    logout() {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      this.$router.push("/login");
    },
  },
};
</script>
