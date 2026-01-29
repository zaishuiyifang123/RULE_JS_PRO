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
        <span class="nav-item is-active">数据管理</span>
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

const logout = () => {
  auth.clear();
  router.replace("/login");
};
</script>
