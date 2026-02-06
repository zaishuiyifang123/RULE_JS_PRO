<template>
  <AppLayout>
    <section class="page">
      <header class="page-header">
        <div>
          <h2>智能问答</h2>
          <p>TASK010 意图识别节点（最近4条user消息）</p>
        </div>
        <div class="header-actions">
          <span class="chat-session">会话: {{ sessionId || "未创建" }}</span>
          <button class="btn ghost" type="button" @click="resetSession" :disabled="loading">
            新会话
          </button>
        </div>
      </header>

      <section class="card chat-input-card">
        <label class="chat-label" for="chat-message">输入问题</label>
        <textarea
          id="chat-message"
          v-model="message"
          class="chat-textarea"
          placeholder="例如：帮我查一下2025-2026-1高等数学A的平均分"
        />
        <div class="chat-actions">
          <button class="btn primary" type="button" @click="submitMessage" :disabled="loading || !message.trim()">
            {{ loading ? "识别中..." : "执行意图识别" }}
          </button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
      </section>

      <section class="card chat-result-card" v-if="result">
        <div class="chat-kv-grid">
          <div class="chat-kv">
            <span class="chat-kv-label">intent</span>
            <span class="chat-kv-value">{{ result.intent }}</span>
          </div>
          <div class="chat-kv">
            <span class="chat-kv-label">is_followup</span>
            <span class="chat-kv-value">{{ result.is_followup ? "true" : "false" }}</span>
          </div>
          <div class="chat-kv">
            <span class="chat-kv-label">confidence</span>
            <span class="chat-kv-value">{{ formatPercent(result.confidence) }}</span>
          </div>
          <div class="chat-kv">
            <span class="chat-kv-label">threshold</span>
            <span class="chat-kv-value">{{ formatPercent(result.threshold) }}</span>
          </div>
        </div>

        <div class="chat-block">
          <p class="chat-block-title">merged_query</p>
          <p class="chat-block-content">{{ result.merged_query }}</p>
        </div>
        <div class="chat-block">
          <p class="chat-block-title">rewritten_query</p>
          <p class="chat-block-content">{{ result.rewritten_query }}</p>
        </div>
      </section>

      <section class="card chat-history-card" v-if="timeline.length">
        <div class="table-meta">
          <div>
            <p class="table-title">本地对话记录</p>
            <p class="table-sub">用于给后端传递最近4条user消息</p>
          </div>
        </div>
        <ul class="chat-history-list">
          <li v-for="(item, index) in timeline" :key="`chat-row-${index}`" class="chat-history-item">
            <span class="chat-role" :class="item.role === 'user' ? 'is-user' : 'is-assistant'">
              {{ item.role }}
            </span>
            <span class="chat-content">{{ item.content }}</span>
          </li>
        </ul>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from "vue";

import AppLayout from "../layouts/AppLayout.vue";
import { postChatIntent, type ChatIntentData, type HistoryMessage } from "../api/chat";

const loading = ref(false);
const error = ref("");
const message = ref("");
const sessionId = ref("");
const result = ref<ChatIntentData | null>(null);
const timeline = ref<HistoryMessage[]>([]);

const submitMessage = async () => {
  const text = message.value.trim();
  if (!text) return;
  loading.value = true;
  error.value = "";
  try {
    const userHistory = timeline.value.filter((item) => item.role === "user").slice(-4);
    const resp = await postChatIntent({
      session_id: sessionId.value || undefined,
      message: text,
      history: userHistory,
    });
    result.value = resp.data;
    sessionId.value = resp.data.session_id;
    timeline.value.push({ role: "user", content: text });
    timeline.value.push({ role: "assistant", content: resp.data.rewritten_query });
    message.value = "";
  } catch (err: any) {
    error.value = err?.response?.data?.message ?? "请求失败";
  } finally {
    loading.value = false;
  }
};

const resetSession = () => {
  sessionId.value = "";
  message.value = "";
  result.value = null;
  error.value = "";
  timeline.value = [];
};

const formatPercent = (value: number): string => `${(value * 100).toFixed(1)}%`;
</script>

