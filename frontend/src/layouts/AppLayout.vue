<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <div>
          <p class="brand-title">Edu Cockpit</p>
          <p class="brand-sub">教务驾驶舱</p>
        </div>
      </div>
      <nav class="app-nav">
        <RouterLink
          class="nav-item"
          :class="{ 'is-active': isActive('/cockpit') }"
          :aria-current="isActive('/cockpit') ? 'page' : undefined"
          to="/cockpit"
        >
          驾驶舱
        </RouterLink>
        <RouterLink
          class="nav-item"
          :class="{ 'is-active': isActive('/data') }"
          :aria-current="isActive('/data') ? 'page' : undefined"
          to="/data"
        >
          数据管理
        </RouterLink>
        <RouterLink
          class="nav-item"
          :class="{ 'is-active': isActive('/chat') }"
          :aria-current="isActive('/chat') ? 'page' : undefined"
          to="/chat"
        >
          智能问答
        </RouterLink>
      </nav>
      <button class="btn ghost" type="button" @click="logout">退出</button>
    </header>
    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const isActive = (path: string) => {
  return router.currentRoute.value.path.startsWith(path);
};

const logout = () => {
  auth.clear();
  router.replace("/login");
};
</script>
