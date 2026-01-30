<template>
  <div v-if="visible" class="modal-backdrop" @click.self="emitClose">
    <div class="modal-card">
      <header class="modal-head">
        <h3>{{ title }}</h3>
        <button class="icon-btn" type="button" @click="emitClose">×</button>
      </header>
      <div class="modal-body">
        <p v-if="error" class="error-text">{{ error }}</p>
        <div v-if="loading" class="table-state">正在加载...</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>课程</th>
              <th>学期</th>
              <th>成绩</th>
              <th>等级</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <td>{{ item.course_name || "-" }}</td>
              <td>{{ item.term || "-" }}</td>
              <td>{{ item.score_value ?? "-" }}</td>
              <td>{{ item.score_level || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="modal-actions">
        <button class="btn ghost" type="button" @click="emitClose">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type ScoreRow = {
  id: number;
  course_name?: string;
  term?: string;
  score_value?: number | null;
  score_level?: string | null;
};

type Props = {
  visible: boolean;
  title: string;
  rows: ScoreRow[];
  loading: boolean;
  error: string;
};

defineProps<Props>();

const emit = defineEmits<{
  (event: "close"): void;
}>();

const emitClose = () => {
  emit("close");
};
</script>
