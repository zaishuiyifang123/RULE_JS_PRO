<template>
  <AppLayout>
    <section class="page">
      <header class="page-header">
        <div>
          <h2>驾驶舱总览</h2>
          <p>核心指标与趋势速览</p>
        </div>
        <button class="btn ghost" type="button" @click="fetchOverview" :disabled="loading">
          {{ loading ? "加载中..." : "刷新" }}
        </button>
      </header>

      <section class="cockpit-grid">
        <div class="card metric-card" v-for="card in cards" :key="card.code">
          <p class="metric-label">{{ card.name }}</p>
          <p class="metric-value">{{ formatNumber(card.value) }}</p>
          <span class="metric-tag">{{ card.code }}</span>
        </div>
      </section>

      <section class="cockpit-row">
        <div class="card trend-card">
          <div class="card-head">
            <div>
              <p class="table-title">趋势折线</p>
              <p class="table-sub">近 7 天缺勤率 / 挂科率</p>
            </div>
          </div>
          <div v-if="loading" class="table-state">正在加载趋势...</div>
          <div v-else class="trend-chart">
            <svg viewBox="0 0 320 140" role="img" aria-label="trend">
              <polyline :points="trendLine(attendance)" fill="none" stroke="#1f7a8c" stroke-width="3" />
              <polyline :points="trendLine(failRate)" fill="none" stroke="#e07a5f" stroke-width="3" />
            </svg>
            <div class="trend-legend">
              <span><i class="legend-dot teal"></i>缺勤率</span>
              <span><i class="legend-dot coral"></i>挂科率</span>
            </div>
            <div class="trend-axis">
              <span v-for="item in trends" :key="item.date">{{ item.date.slice(5) }}</span>
            </div>
          </div>
        </div>

        <div class="card alert-card">
          <div class="card-head">
            <div>
              <p class="table-title">预警列表</p>
              <p class="table-sub">规则触发的异常提示</p>
            </div>
          </div>
          <div v-if="loading" class="table-state">正在加载预警...</div>
          <div v-else-if="alerts.length === 0" class="table-state">暂无预警</div>
          <ul v-else class="alert-list">
            <li v-for="item in alerts" :key="item.title" class="alert-item">
              <span class="alert-level">{{ item.level }}</span>
              <div>
                <p>{{ item.title }}</p>
                <small>{{ item.message }}</small>
              </div>
            </li>
          </ul>
        </div>
      </section>

      <p v-if="error" class="error-text">{{ error }}</p>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import api from "../api/client";
import AppLayout from "../layouts/AppLayout.vue";

type CardItem = { code: string; name: string; value: number };
type TrendItem = { date: string; attendance_rate: number; fail_rate: number };
type AlertItem = { level: string; title: string; message: string };

const cards = ref<CardItem[]>([]);
const trends = ref<TrendItem[]>([]);
const alerts = ref<AlertItem[]>([]);
const loading = ref(false);
const error = ref("");

const attendance = computed(() => trends.value.map((item) => item.attendance_rate));
const failRate = computed(() => trends.value.map((item) => item.fail_rate));

const formatNumber = (value: number) => {
  if (Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("zh-CN").format(value);
};

const trendLine = (values: number[]) => {
  if (!values.length) {
    return "";
  }
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1 || 1)) * 300 + 10;
      const y = 120 - ((value - min) / range) * 90;
      return `${x},${y}`;
    })
    .join(" ");
};

const fetchOverview = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.get("/cockpit/overview");
    cards.value = res.data.data.cards || [];
    trends.value = res.data.data.trends || [];
    alerts.value = res.data.data.alerts || [];
  } catch (err: any) {
    error.value = err?.response?.data?.message || "驾驶舱加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
};

onMounted(fetchOverview);
</script>
