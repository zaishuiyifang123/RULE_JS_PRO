<template>
  <div class="login-shell">
    <section class="login">
      <h2>用户登录</h2>
      <form class="login-form" @submit.prevent="submit">
        <div class="login_box">
          <input
            v-model.trim="username"
            type="text"
            name="username"
            required
            placeholder=" "
            autocomplete="username"
            :class="{ 'is-invalid': !!error }"
            :aria-invalid="Boolean(error)"
          />
          <label>用户名</label>
        </div>
        <div class="login_box">
          <input
            v-model.trim="password"
            type="password"
            name="password"
            required
            placeholder=" "
            autocomplete="current-password"
            :class="{ 'is-invalid': !!error }"
            :aria-invalid="Boolean(error)"
          />
          <label>密码</label>
        </div>
        <p v-if="error" class="error-text login-error">{{ error }}</p>
        <p v-if="loading" class="login-status">正在验证身份，请稍候...</p>
        <button class="login-submit" type="submit" :disabled="loading">
          <span class="login-submit-line line-1"></span>
          <span class="login-submit-line line-2"></span>
          <span class="login-submit-line line-3"></span>
          <span class="login-submit-line line-4"></span>
          <span class="login-submit-text">{{ loading ? "登录中..." : "登录" }}</span>
        </button>
      </form>
    </section>
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
