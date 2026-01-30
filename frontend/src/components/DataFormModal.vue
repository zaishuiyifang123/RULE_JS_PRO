<template>
  <div v-if="visible" class="modal-backdrop" @click.self="emitClose">
    <div class="modal-card">
      <header class="modal-head">
        <h3>{{ title }}</h3>
        <button class="icon-btn" type="button" @click="emitClose">×</button>
      </header>
      <div class="modal-body">
        <p v-if="error" class="error-text">{{ error }}</p>
        <form class="modal-form" @submit.prevent="emitSubmit">
          <div v-for="field in fields" :key="field.key" class="field">
            <label>
              {{ field.label }}
              <span v-if="field.required" class="field-required">*</span>
            </label>
            <textarea
              v-if="field.type === 'textarea'"
              :value="modelValue[field.key] ?? ''"
              :placeholder="field.placeholder || ''"
              :readonly="field.readonly"
              @input="updateField(field.key, ($event.target as HTMLTextAreaElement).value)"
            />
            <input
              v-else
              :type="field.type"
              :value="modelValue[field.key] ?? ''"
              :placeholder="field.placeholder || ''"
              :readonly="field.readonly"
              @input="updateField(field.key, ($event.target as HTMLInputElement).value)"
            />
          </div>
          <div class="modal-actions">
            <button class="btn ghost" type="button" @click="emitClose">取消</button>
            <button class="btn primary" type="submit" :disabled="loading">
              {{ loading ? '提交中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type FieldDef = {
  key: string;
  label: string;
  type: "text" | "number" | "date" | "textarea";
  required?: boolean;
  placeholder?: string;
  readonly?: boolean;
};

type Props = {
  visible: boolean;
  title: string;
  fields: FieldDef[];
  modelValue: Record<string, any>;
  loading: boolean;
  error: string;
};

const props = defineProps<Props>();
const emit = defineEmits<{
  (event: "update:modelValue", value: Record<string, any>): void;
  (event: "submit"): void;
  (event: "close"): void;
}>();

const updateField = (key: string, value: string) => {
  emit("update:modelValue", { ...props.modelValue, [key]: value });
};

const emitSubmit = () => {
  emit("submit");
};

const emitClose = () => {
  emit("close");
};
</script>
