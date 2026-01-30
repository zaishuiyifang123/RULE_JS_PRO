<template>
  <div class="pagination-bar">
    <div class="pagination-controls">
      <button
        class="btn ghost"
        type="button"
        :disabled="page <= 1"
        @click="emitPageChange(page - 1)"
      >
        上一页
      </button>
      <button
        v-for="p in pages"
        :key="p"
        class="page-btn"
        :class="{ active: p === page }"
        type="button"
        @click="emitPageChange(p)"
      >
        {{ p }}
      </button>
      <button
        class="btn ghost"
        type="button"
        :disabled="page >= totalPages"
        @click="emitPageChange(page + 1)"
      >
        下一页
      </button>
    </div>
    <div class="page-size">
      <span>每页</span>
      <select :value="pageSize" @change="emitPageSizeChange($event)">
        <option v-for="size in pageSizes" :key="size" :value="size">
          {{ size }}
        </option>
      </select>
      <span>条</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

type Props = {
  page: number;
  pageSize: number;
  total: number;
  pageSizes?: number[];
};

const props = withDefaults(defineProps<Props>(), {
  pageSizes: () => [10, 20, 50, 100],
});

const emit = defineEmits<{
  (event: "page-change", value: number): void;
  (event: "page-size-change", value: number): void;
}>();

const totalPages = computed(() => {
  if (props.total <= 0) {
    return 1;
  }
  return Math.max(1, Math.ceil(props.total / props.pageSize));
});

const pages = computed(() => {
  const maxButtons = 5;
  const total = totalPages.value;
  let start = Math.max(1, props.page - Math.floor(maxButtons / 2));
  let end = Math.min(total, start + maxButtons - 1);
  start = Math.max(1, end - maxButtons + 1);
  const result: number[] = [];
  for (let i = start; i <= end; i += 1) {
    result.push(i);
  }
  return result;
});

const emitPageChange = (nextPage: number) => {
  if (nextPage < 1 || nextPage > totalPages.value) {
    return;
  }
  emit("page-change", nextPage);
};

const emitPageSizeChange = (event: Event) => {
  const value = Number((event.target as HTMLSelectElement).value);
  if (!Number.isNaN(value)) {
    emit("page-size-change", value);
  }
};
</script>
