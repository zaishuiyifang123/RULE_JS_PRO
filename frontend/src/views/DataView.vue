<template>
  <AppLayout>
    <section class="page">
      <header class="page-header">
        <div>
          <h2>数据管理</h2>
          <p>基础数据浏览与快速检索入口</p>
        </div>
        <button class="btn ghost" type="button" @click="fetchData" :disabled="loading">
          {{ loading ? "加载中..." : "刷新" }}
        </button>
      </header>

      <section class="card">
        <div class="table-meta">
          <div>
            <p class="table-title">学生列表</p>
            <p class="table-sub">最新数据快照（示例）</p>
          </div>
          <span class="meta-count">共 {{ meta.total }} 条</span>
        </div>

        <div v-if="loading" class="table-state">正在加载数据...</div>
        <div v-else-if="error" class="table-state error-text">{{ error }}</div>
        <div v-else-if="rows.length === 0" class="table-state">暂无数据</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>学号</th>
              <th>姓名</th>
              <th>性别</th>
              <th>入学年份</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <td>{{ item.student_no }}</td>
              <td>{{ item.real_name }}</td>
              <td>{{ item.gender || "-" }}</td>
              <td>{{ item.enroll_year || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import api from "../api/client";
import AppLayout from "../layouts/AppLayout.vue";

type MetaInfo = {
  total: number;
};

const rows = ref<any[]>([]);
const meta = ref<MetaInfo>({ total: 0 });
const loading = ref(false);
const error = ref("");

const fetchData = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.get("/student/list", {
      params: { offset: 0, limit: 8 },
    });
    rows.value = res.data.data || [];
    meta.value = res.data.meta || { total: rows.value.length };
  } catch (err: any) {
    error.value = err?.response?.data?.message || "数据加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
};

onMounted(fetchData);
</script>
