<template>
  <div style="max-width: 360px; margin: 60px auto; font-family: system-ui;">
    <h2>Login</h2>

    <form @submit.prevent="onLogin">
      <div style="margin: 12px 0;">
        <label>Username / Email</label>
        <input v-model="username" style="width:100%; padding:8px;" />
      </div>

      <div style="margin: 12px 0;">
        <label>Password</label>
        <input v-model="password" type="password" style="width:100%; padding:8px;" />
      </div>

      <button :disabled="loading" style="padding:8px 12px;">
        {{ loading ? "Logging in..." : "Login" }}
      </button>

      <p v-if="error" style="color: red; margin-top: 10px;">{{ error }}</p>
    </form>
  </div>
</template>

<script>
import { api } from "../lib/api";

export default {
  data() {
    return {
      username: "",
      password: "",
      loading: false,
      error: "",
    };
  },
  methods: {
    async onLogin() {
      this.error = "";
      this.loading = true;
      try {
        const res = await api.post("/api/auth/login/", {
          username: this.username,
          password: this.password,
        });

        localStorage.setItem("access_token", res.data.access);
        localStorage.setItem("refresh_token", res.data.refresh);

        this.$router.push("/chat");
      } catch (e) {
        this.error =
          e?.response?.data?.detail ||
          "Login failed. Check username/password.";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
