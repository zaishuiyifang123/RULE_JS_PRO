import { defineStore } from "pinia";

const TOKEN_KEY = "edu_token";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || "",
  }),
  getters: {
    isAuthed: (state) => Boolean(state.token),
  },
  actions: {
    setToken(token: string) {
      this.token = token;
      localStorage.setItem(TOKEN_KEY, token);
    },
    clear() {
      this.token = "";
      localStorage.removeItem(TOKEN_KEY);
    },
  },
});
