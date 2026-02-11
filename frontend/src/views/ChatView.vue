<template>
  <AppLayout>
    <section class="page">
      <header class="page-header">
        <div>
          <h2>智能问答</h2>
          <p>选择历史会话继续对话，支持滚动加载更多记录</p>
        </div>
        <div class="header-actions">
          <button class="btn ghost chat-mobile-toggle" type="button" @click="toggleSessionPanel">
            会话列表
          </button>
        </div>
      </header>

      <div class="page-body-scroll">
        <section class="chat-shell">
          <aside class="card chat-sidebar" :class="{ 'is-open': showSessionPanel }">
            <div class="chat-sidebar-head">
              <p class="chat-sidebar-title">历史会话</p>
              <button class="btn ghost" type="button" @click="startNewSession" :disabled="sending">新会话</button>
            </div>
            <div ref="sessionListRef" class="chat-session-list" @scroll.passive="handleSessionScroll">
              <button
                v-for="session in sessions"
                :key="session.session_id"
                class="chat-session-item"
                :class="{ 'is-active': session.session_id === activeSessionId }"
                type="button"
                @click="openSession(session.session_id)"
              >
                <span class="chat-session-preview">{{ session.preview || "空会话" }}</span>
                <span class="chat-session-time">{{ formatSessionTime(session.last_active_at) }}</span>
              </button>
              <p v-if="sessionsLoading && !sessions.length" class="chat-side-tip">加载会话中...</p>
              <p v-else-if="!sessionsLoading && !sessions.length" class="chat-side-tip">暂无历史会话</p>
              <p v-if="sessionsLoadingMore" class="chat-side-tip">加载更多会话...</p>
              <p v-else-if="!sessionsHasMore && sessions.length" class="chat-side-tip">没有更多会话了</p>
              <p v-if="sessionError" class="error-text chat-side-error">{{ sessionError }}</p>
            </div>
          </aside>

          <section class="card chat-main">
            <div class="chat-main-head">
              <span class="chat-session">会话: {{ activeSessionId || "未选择" }}</span>
              <button class="btn ghost" type="button" @click="startNewSession" :disabled="sending">新会话</button>
            </div>

            <div v-if="!activeSessionId && !timeline.length" class="chat-empty">
              <p>请选择左侧会话，或点击“新会话”开始对话。</p>
            </div>

            <div
              v-else
              ref="messageListRef"
              class="chat-message-list"
              @scroll.passive="handleMessageScroll"
            >
              <p v-if="messagesLoadingMore" class="chat-load-tip">加载更早消息...</p>
              <p v-if="messagesLoading && !timeline.length" class="chat-load-tip">加载消息中...</p>
              <div
                v-for="item in timeline"
                :key="item.local_id"
                class="chat-msg-row"
                :class="item.role === 'user' ? 'is-user' : 'is-assistant'"
              >
                <div class="chat-msg-bubble">
                  <div v-if="item.role === 'assistant' && item.statusLines?.length" class="chat-msg-status-list">
                    <p
                      v-for="(statusLine, statusIndex) in item.statusLines"
                      :key="`status-${statusIndex}-${statusLine}`"
                      class="chat-msg-status"
                    >
                      {{ statusLine }}
                    </p>
                  </div>
                  <p v-if="item.content" class="chat-msg-content">{{ item.content }}</p>
                </div>
              </div>
              <p v-if="activeSessionId && !timeline.length && !messagesLoading" class="chat-load-tip">该会话暂无消息</p>
              <p v-if="!messagesHasOlder && timeline.length" class="chat-load-tip">已显示最近消息</p>
            </div>

            <section class="chat-composer">
              <label class="chat-label" for="chat-message">输入问题</label>
              <textarea
                id="chat-message"
                v-model="message"
                class="chat-textarea"
                placeholder="输入问题后发送，未选会话将自动创建新会话"
              />
              <div class="chat-actions">
                <button class="btn primary" type="button" @click="submitMessage" :disabled="sending || !message.trim()">
                  {{ sending ? "发送中..." : "发送" }}
                </button>
              </div>
              <p v-if="error" class="error-text">{{ error }}</p>
            </section>
          </section>
        </section>
      </div>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";

import AppLayout from "../layouts/AppLayout.vue";
import {
  getChatSessionMessages,
  getChatSessions,
  postChatStream,
  type ChatSessionItem,
  type ChatSessionMessageItem,
} from "../api/chat";

type TimelineMessage = {
  local_id: string;
  id?: number;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  statusLines?: string[];
};

const SESSION_PAGE_SIZE = 20;
const MESSAGE_PAGE_SIZE = 20;

const showSessionPanel = ref(false);
const sessionListRef = ref<HTMLElement | null>(null);
const messageListRef = ref<HTMLElement | null>(null);

const sessions = ref<ChatSessionItem[]>([]);
const sessionsLoading = ref(false);
const sessionsLoadingMore = ref(false);
const sessionsHasMore = ref(true);
const sessionOffset = ref(0);
const sessionError = ref("");

const activeSessionId = ref("");
const timeline = ref<TimelineMessage[]>([]);
const messagesLoading = ref(false);
const messagesLoadingMore = ref(false);
const messagesHasOlder = ref(false);
const messageStartOffset = ref(0);

const message = ref("");
const sending = ref(false);
const error = ref("");

let localMessageSeed = 0;
const buildLocalId = (prefix: string) => `${prefix}-${Date.now()}-${++localMessageSeed}`;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const getAssistantMessageByIndex = (assistantIndex: number): TimelineMessage | null => {
  const message = timeline.value[assistantIndex];
  if (!message || message.role !== "assistant") {
    return null;
  }
  return message;
};

const appendAssistantTyping = async (assistantIndex: number, text: string) => {
  const assistantMessage = getAssistantMessageByIndex(assistantIndex);
  if (!assistantMessage) return;
  assistantMessage.content = "";
  const stepSize = 2;
  for (let index = 0; index < text.length; index += stepSize) {
    const liveMessage = getAssistantMessageByIndex(assistantIndex);
    if (!liveMessage) return;
    liveMessage.content += text.slice(index, index + stepSize);
    if (index % 8 === 0) {
      await nextTick();
      scrollToMessageBottom();
    }
    await wait(16);
  }
  await nextTick();
  scrollToMessageBottom();
};

const appendAssistantStatus = async (assistantIndex: number, statusText: string) => {
  const assistantMessage = getAssistantMessageByIndex(assistantIndex);
  if (!assistantMessage) return;
  const text = statusText.trim();
  if (!text) return;
  if (!assistantMessage.statusLines) {
    assistantMessage.statusLines = [];
  }
  const lastStatus = assistantMessage.statusLines[assistantMessage.statusLines.length - 1];
  if (lastStatus === text) {
    return;
  }
  assistantMessage.statusLines.push(text);
  await nextTick();
  scrollToMessageBottom();
};

const formatSessionTime = (value: string): string => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
};

const scrollToMessageBottom = () => {
  const el = messageListRef.value;
  if (!el) return;
  el.scrollTop = el.scrollHeight;
};

const loadMoreSessions = async () => {
  if (!sessionsHasMore.value) return;
  if (sessionsLoading.value || sessionsLoadingMore.value) return;
  const isFirstPage = sessionOffset.value === 0;
  if (isFirstPage) {
    sessionsLoading.value = true;
  } else {
    sessionsLoadingMore.value = true;
  }
  try {
    const resp = await getChatSessions({
      offset: sessionOffset.value,
      limit: SESSION_PAGE_SIZE,
    });
    const existing = new Set(sessions.value.map((item) => item.session_id));
    const incoming: ChatSessionItem[] = [];
    for (const item of resp.data) {
      if (!existing.has(item.session_id)) {
        incoming.push(item);
      }
    }
    sessions.value = [...sessions.value, ...incoming];
    sessionOffset.value += resp.data.length;
    sessionsHasMore.value = sessionOffset.value < resp.meta.total;
  } catch (err: any) {
    sessionError.value = err?.message ?? err?.response?.data?.message ?? "Failed to load sessions";
  } finally {
    sessionsLoading.value = false;
    sessionsLoadingMore.value = false;
  }
};

const refreshSessions = async () => {
  sessions.value = [];
  sessionsHasMore.value = true;
  sessionOffset.value = 0;
  sessionError.value = "";
  await loadMoreSessions();
};

const mapMessages = (rows: ChatSessionMessageItem[]): TimelineMessage[] => {
  return rows.map((item) => ({
    local_id: item.id ? `msg-${item.id}` : buildLocalId("msg"),
    id: item.id,
    role: item.role === "assistant" ? "assistant" : "user",
    content: item.content,
    created_at: item.created_at,
  }));
};

const loadSessionMessages = async (sessionId: string) => {
  messagesLoading.value = true;
  messagesLoadingMore.value = false;
  messagesHasOlder.value = false;
  messageStartOffset.value = 0;
  timeline.value = [];
  error.value = "";
  try {
    const probe = await getChatSessionMessages(sessionId, { offset: 0, limit: 1 });
    const total = probe.meta.total;
    if (total <= 0) {
      messagesHasOlder.value = false;
      return;
    }
    const startOffset = Math.max(total - MESSAGE_PAGE_SIZE, 0);
    const page = await getChatSessionMessages(sessionId, {
      offset: startOffset,
      limit: MESSAGE_PAGE_SIZE,
    });
    timeline.value = mapMessages(page.data);
    messageStartOffset.value = startOffset;
    messagesHasOlder.value = startOffset > 0;
    await nextTick();
    scrollToMessageBottom();
  } catch (err: any) {
    error.value = err?.message ?? err?.response?.data?.message ?? "Failed to load messages";
  } finally {
    messagesLoading.value = false;
  }
};

const loadOlderMessages = async () => {
  if (!activeSessionId.value) return;
  if (!messagesHasOlder.value || messagesLoading.value || messagesLoadingMore.value) return;
  const nextOffset = Math.max(messageStartOffset.value - MESSAGE_PAGE_SIZE, 0);
  const nextLimit = messageStartOffset.value - nextOffset;
  if (nextLimit <= 0) {
    messagesHasOlder.value = false;
    return;
  }
  const container = messageListRef.value;
  const prevHeight = container?.scrollHeight ?? 0;
  const prevTop = container?.scrollTop ?? 0;
  messagesLoadingMore.value = true;
  try {
    const resp = await getChatSessionMessages(activeSessionId.value, {
      offset: nextOffset,
      limit: nextLimit,
    });
    const olderRows = mapMessages(resp.data);
    timeline.value = [...olderRows, ...timeline.value];
    messageStartOffset.value = nextOffset;
    messagesHasOlder.value = nextOffset > 0;
    await nextTick();
    if (container) {
      container.scrollTop = container.scrollHeight - prevHeight + prevTop;
    }
  } catch (err: any) {
    error.value = err?.message ?? err?.response?.data?.message ?? "Failed to load older messages";
  } finally {
    messagesLoadingMore.value = false;
  }
};

const openSession = async (sessionId: string) => {
  if (!sessionId) return;
  activeSessionId.value = sessionId;
  await loadSessionMessages(sessionId);
  if (window.innerWidth <= 960) {
    showSessionPanel.value = false;
  }
};

const startNewSession = () => {
  activeSessionId.value = "";
  timeline.value = [];
  message.value = "";
  error.value = "";
  messagesLoading.value = false;
  messagesLoadingMore.value = false;
  messagesHasOlder.value = false;
  messageStartOffset.value = 0;
  if (window.innerWidth <= 960) {
    showSessionPanel.value = false;
  }
};

const submitMessage = async () => {
  const text = message.value.trim();
  if (!text) return;
  sending.value = true;
  error.value = "";
  timeline.value.push({ local_id: buildLocalId("tmp-user"), role: "user", content: text });
  const assistantMessage: TimelineMessage = {
    local_id: buildLocalId("tmp-assistant"),
    role: "assistant",
    content: "",
    statusLines: [],
  };
  const assistantIndex = timeline.value.length;
  timeline.value.push(assistantMessage);
  message.value = "";
  await nextTick();
  scrollToMessageBottom();
  try {
    const resp = await postChatStream(
      {
        session_id: activeSessionId.value || undefined,
        message: text,
      },
      {
        onEvent: (_event, data) => {
          if (data.message) {
            void appendAssistantStatus(assistantIndex, data.message);
          }
        },
      }
    );
    activeSessionId.value = resp.data.session_id;
    await appendAssistantTyping(assistantIndex, resp.data.summary || "");
    await refreshSessions();
    await nextTick();
    scrollToMessageBottom();
  } catch (err: any) {
    error.value = err?.message ?? err?.response?.data?.message ?? "Request failed";
    void appendAssistantStatus(assistantIndex, error.value || "请求失败");
  } finally {
    sending.value = false;
  }
};

const handleSessionScroll = () => {
  const el = sessionListRef.value;
  if (!el || sessionsLoading.value || sessionsLoadingMore.value || !sessionsHasMore.value) return;
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
    void loadMoreSessions();
  }
};

const handleMessageScroll = () => {
  const el = messageListRef.value;
  if (!el || messagesLoading.value || messagesLoadingMore.value || !messagesHasOlder.value) return;
  if (el.scrollTop <= 40) {
    void loadOlderMessages();
  }
};

const toggleSessionPanel = () => {
  showSessionPanel.value = !showSessionPanel.value;
};

onMounted(() => {
  void refreshSessions();
});
</script>
