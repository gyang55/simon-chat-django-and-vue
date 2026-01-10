<template>
  <div style="display: flex; height: 100vh; font-family: system-ui">
    <aside style="width: 280px; border-right: 1px solid #ddd; padding: 12px">
      <div
        style="
          display: flex;
          justify-content: space-between;
          align-items: center;
        "
      >
        <h3 style="margin: 0">Chats</h3>
        <button @click="createChat">+ New</button>
      </div>

      <div style="margin-top: 12px">
        <div
          v-for="c in chats"
          :key="c.id"
          @click="selectChat(c)"
          :style="{
            padding: '10px',
            cursor: 'pointer',
            borderRadius: '8px',
            background: selectedChat?.id === c.id ? '#f0f0f0' : 'transparent',
          }"
        >
          <div style="font-weight: 600">{{ c.title || "Untitled" }}</div>
          <div style="font-size: 12px; color: #666">#{{ c.id }}</div>
        </div>
      </div>

      <hr />
      <button @click="logout" style="width: 100%">Logout</button>
    </aside>

    <main style="flex: 1; padding: 16px">
      <h2 v-if="!selectedChat">Select a chat</h2>

      <div v-else>
        <h2 style="margin-top: 0">Chat #{{ selectedChat.id }}</h2>

        <div
          style="
            margin: 12px 0;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 12px;
            height: 60vh;
            overflow: auto;
          "
        >
          <div v-for="m in messages" :key="m.id" style="margin: 10px 0">
            <b>{{ m.role }}:</b> <span>{{ m.content }}</span>
          </div>
        </div>

        <form @submit.prevent="sendMessage" style="display: flex; gap: 8px">
          <input
            v-model="input"
            style="flex: 1; padding: 10px"
            placeholder="Type..."
          />
          <button :disabled="!input.trim()">Send</button>
        </form>
      </div>

      <p v-if="error" style="color: red">{{ error }}</p>
    </main>
  </div>
</template>

<script>
import { api } from "../lib/api.js";
import { streamChat } from "../lib/stream.js";
export default {
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

    logout() {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      this.$router.push("/login");
    },
  },
};
</script>
