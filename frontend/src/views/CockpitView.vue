<template>
  <AppLayout>
    <section class="page">
      <header class="page-header">
        <div>
          <h2>驾驶舱总览</h2>
          <p>学期与组织维度联动的关键指标与风险视图</p>
        </div>
        <div class="header-actions">
          <button class="btn ghost" type="button" @click="fetchOverview" :disabled="loading">
            {{ loading ? "加载中..." : "刷新" }}
          </button>
          <button class="btn primary" type="button" @click="exportRisk" :disabled="loading">
            导出风险清单
          </button>
        </div>
      </header>

      <section class="card filter-panel">
        <div class="filter-grid">
          <div class="filter-field">
            <label>学期</label>
            <select v-model="filters.term">
              <option value="">全部</option>
              <option v-for="term in filterOptions.terms" :key="term" :value="term">
                {{ term }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>学院</label>
            <select v-model="filters.college_id">
              <option value="">全部</option>
              <option v-for="item in filterOptions.colleges" :key="item.value" :value="String(item.value)">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>专业</label>
            <select v-model="filters.major_id">
              <option value="">全部</option>
              <option v-for="item in filterOptions.majors" :key="item.value" :value="String(item.value)">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>年级</label>
            <select v-model="filters.grade_year">
              <option value="">全部</option>
              <option v-for="item in filterOptions.grades" :key="item" :value="String(item)">
                {{ item }}
              </option>
            </select>
          </div>
          <div class="filter-actions">
            <button class="btn ghost" type="button" @click="applyFilters" :disabled="loading">
              应用筛选
            </button>
            <button class="btn ghost" type="button" @click="resetFilters" :disabled="loading">
              重置
            </button>
          </div>
        </div>
      </section>

      <section class="cockpit-grid">
        <div class="card metric-card" v-for="card in cards" :key="card.code">
          <p class="metric-label">{{ card.name }}</p>
          <p class="metric-value">{{ formatValue(card) }}</p>
          <span class="metric-tag">{{ card.code }}</span>
        </div>
      </section>

      <section class="cockpit-row">
        <div class="card trend-card">
          <div class="card-head">
            <div>
              <p class="table-title">趋势对比</p>
              <p class="table-sub">近 7 天出勤率 / 挂科率 / 平均成绩</p>
            </div>
          </div>
          <div v-if="loading" class="table-state">正在加载趋势...</div>
          <div v-else class="trend-chart">
            <svg viewBox="0 0 320 140" role="img" aria-label="trend">
              <polyline :points="trendLine(attendance)" fill="none" stroke="#1f7a8c" stroke-width="3" />
              <polyline :points="trendLine(failRate)" fill="none" stroke="#e07a5f" stroke-width="3" />
              <polyline :points="trendLine(avgScore)" fill="none" stroke="#324cdd" stroke-width="3" />
            </svg>
            <div class="trend-legend">
              <span><i class="legend-dot teal"></i>出勤率</span>
              <span><i class="legend-dot coral"></i>挂科率</span>
              <span><i class="legend-dot blue"></i>平均成绩</span>
            </div>
            <div class="trend-axis">
              <span v-for="item in trends" :key="item.date">{{ item.date.slice(5) }}</span>
            </div>
          </div>
        </div>

        <div class="card dist-card">
          <div class="card-head">
            <div>
              <p class="table-title">结构分布</p>
              <p class="table-sub">学院规模与成绩段分布</p>
            </div>
            <button class="btn ghost" type="button" @click="goToData('college')">查看学院</button>
          </div>
          <div class="dist-grid">
            <div>
              <p class="dist-title">学院规模</p>
              <div class="dist-list">
                <div v-for="item in distributions.college_students" :key="item.name" class="dist-item">
                  <span class="dist-name">{{ item.name }}</span>
                  <div class="dist-bar">
                    <span :style="{ width: calcBar(item.value, collegeMax) }"></span>
                  </div>
                  <span class="dist-value">{{ formatNumber(item.value) }}</span>
                </div>
              </div>
            </div>
            <div>
              <p class="dist-title">成绩段</p>
              <div class="dist-list">
                <div v-for="item in distributions.score_band" :key="item.name" class="dist-item">
                  <span class="dist-name">{{ item.name }}</span>
                  <div class="dist-bar">
                    <span :style="{ width: calcBar(item.value, scoreMax) }"></span>
                  </div>
                  <span class="dist-value">{{ formatNumber(item.value) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="cockpit-row">
        <div class="card rank-card">
          <div class="card-head">
            <div>
              <p class="table-title">风险榜单</p>
              <p class="table-sub">挂科率与缺勤率 Top</p>
            </div>
            <button class="btn ghost" type="button" @click="goToData('course')">查看课程</button>
          </div>
          <div class="rank-grid">
            <div>
              <p class="dist-title">课程挂科率</p>
              <ol class="rank-list">
                <li v-for="item in rankings.course_fail_rate" :key="item.name">
                  <span>{{ item.name }}</span>
                  <strong>{{ toPercent(item.value) }}</strong>
                </li>
              </ol>
            </div>
            <div>
              <p class="dist-title">班级缺勤率</p>
              <ol class="rank-list">
                <li v-for="item in rankings.class_absent_rate" :key="item.name">
                  <span>{{ item.name }}</span>
                  <strong>{{ toPercent(item.value) }}</strong>
                </li>
              </ol>
            </div>
          </div>
        </div>

        <div class="card alert-card">
          <div class="card-head">
            <div>
              <p class="table-title">高风险学生</p>
              <p class="table-sub">挂科累积提醒</p>
            </div>
            <button class="btn ghost" type="button" @click="goToData('student')">查看学生</button>
          </div>
          <div v-if="loading" class="table-state">正在加载风险清单...</div>
          <div v-else-if="risks.length === 0" class="table-state">暂无风险</div>
          <ul v-else class="alert-list">
            <li v-for="item in risks" :key="item.title" class="alert-item">
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
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import api from "../api/client";
import AppLayout from "../layouts/AppLayout.vue";

type OptionItem = { value: number | string; label: string };
type FilterOptions = { terms: string[]; colleges: OptionItem[]; majors: OptionItem[]; grades: number[] };
type CardItem = { code: string; name: string; value: number; unit?: string | null };
type TrendItem = { date: string; attendance_rate: number; fail_rate: number; avg_score?: number | null };
type DistributionItem = { name: string; value: number };
type RankingItem = { name: string; value: number };
type RiskItem = { level: string; title: string; message: string };

const router = useRouter();
const cards = ref<CardItem[]>([]);
const trends = ref<TrendItem[]>([]);
const risks = ref<RiskItem[]>([]);
const distributions = ref<{ college_students: DistributionItem[]; score_band: DistributionItem[] }>({
  college_students: [],
  score_band: [],
});
const rankings = ref<{ course_fail_rate: RankingItem[]; class_absent_rate: RankingItem[] }>({
  course_fail_rate: [],
  class_absent_rate: [],
});
const filterOptions = ref<FilterOptions>({ terms: [], colleges: [], majors: [], grades: [] });
const loading = ref(false);
const error = ref("");

const filters = reactive({
  term: "",
  college_id: "",
  major_id: "",
  grade_year: "",
});

const attendance = computed(() => trends.value.map((item) => item.attendance_rate));
const failRate = computed(() => trends.value.map((item) => item.fail_rate));
const avgScore = computed(() => trends.value.map((item) => item.avg_score ?? 0));

const collegeMax = computed(() => Math.max(...distributions.value.college_students.map((i) => i.value), 1));
const scoreMax = computed(() => Math.max(...distributions.value.score_band.map((i) => i.value), 1));

const formatNumber = (value: number) => {
  if (Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("zh-CN").format(value);
};

const toPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

const formatValue = (card: CardItem) => {
  if (card.unit === "ratio") {
    return toPercent(card.value);
  }
  return formatNumber(card.value);
};

const calcBar = (value: number, max: number) => {
  if (!max) {
    return "0%";
  }
  return `${Math.min(100, (value / max) * 100)}%`;
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

const buildParams = () => {
  const params: Record<string, any> = {};
  if (filters.term) {
    params.term = filters.term;
  }
  if (filters.college_id) {
    params.college_id = Number(filters.college_id);
  }
  if (filters.major_id) {
    params.major_id = Number(filters.major_id);
  }
  if (filters.grade_year) {
    params.grade_year = Number(filters.grade_year);
  }
  return params;
};

const fetchOverview = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.get("/cockpit/overview", { params: buildParams() });
    const data = res.data.data || {};
    cards.value = data.cards || [];
    trends.value = data.trends || [];
    risks.value = data.risks || [];
    distributions.value = data.distributions || { college_students: [], score_band: [] };
    rankings.value = data.rankings || { course_fail_rate: [], class_absent_rate: [] };
    filterOptions.value = data.filters || { terms: [], colleges: [], majors: [], grades: [] };
  } catch (err: any) {
    error.value = err?.response?.data?.message || "驾驶舱加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
};

const applyFilters = () => {
  fetchOverview();
};

const resetFilters = () => {
  filters.term = "";
  filters.college_id = "";
  filters.major_id = "";
  filters.grade_year = "";
  fetchOverview();
};

const goToData = (table: string) => {
  const query: Record<string, any> = { table };
  if (filters.college_id) {
    query.college_id = filters.college_id;
  }
  if (filters.major_id) {
    query.major_id = filters.major_id;
  }
  if (filters.grade_year) {
    query.enroll_year = filters.grade_year;
  }
  router.push({ name: "data", query });
};

const exportRisk = async () => {
  try {
    const res = await api.get("/cockpit/risk/export", {
      params: buildParams(),
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "risk_list.csv";
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (err: any) {
    error.value = err?.response?.data?.message || "导出失败";
  }
};

onMounted(fetchOverview);
</script>
