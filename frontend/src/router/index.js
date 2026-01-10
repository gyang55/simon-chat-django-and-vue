import { createRouter, createWebHistory } from "vue-router";
import Login from "../pages/Login.vue";
import Chat from "../pages/Chat.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/chat" },
    { path: "/login", component: Login },
    { path: "/chat", component: Chat },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("access_token");
  if (to.path !== "/login" && !token) return "/login";
});

export default router;
