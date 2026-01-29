<template>
  <div class="login-shell">
    <section class="login-card">
      <div class="login-title">
        <h1>教务驾驶舱</h1>
        <p>管理员登录入口</p>
      </div>
      <form class="login-form" @submit.prevent="submit">
        <label class="field">
          <span>账号</span>
          <input
            v-model.trim="username"
            type="text"
            name="username"
            placeholder="请输入管理员账号"
            autocomplete="username"
          />
        </label>
        <label class="field">
          <span>密码</span>
          <input
            v-model.trim="password"
            type="password"
            name="password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </label>
        <p v-if="error" class="error-text">{{ error }}</p>
        <button class="btn primary" type="submit" :disabled="loading">
          {{ loading ? "登录中..." : "登录" }}
        </button>
      </form>
      <p class="login-footnote">登录后可访问数据管理与基础指标视图。</p>
    </section>
    <aside class="login-panel">
      <div class="panel-card">
        <p class="panel-title">今日概览</p>
        <p class="panel-number">20,000+</p>
        <p class="panel-sub">学生规模 · 全量数据可追溯</p>
      </div>
      <div class="panel-note">
        统一口径 · 风险预警 · 可解释查询
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import api from "../api/client";
import { useAuthStore } from "../stores/auth";

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const submit = async () => {
  error.value = "";
  if (!username.value || !password.value) {
    error.value = "请填写账号和密码";
    return;
  }
  loading.value = true;
  try {
    const res = await api.post("/auth/login", {
      username: username.value,
      password: password.value,
    });
    auth.setToken(res.data.access_token);
    const redirect = (route.query.redirect as string) || "/data";
    router.replace(redirect);
  } catch (err: any) {
    const message = err?.response?.data?.message;
    error.value = message || "登录失败，请检查账号或密码";
  } finally {
    loading.value = false;
  }
};
</script>
