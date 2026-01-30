import { createRouter, createWebHistory } from "vue-router";

import LoginView from "../views/LoginView.vue";
import CockpitView from "../views/CockpitView.vue";
import DataView from "../views/DataView.vue";

const routes = [
  { path: "/", redirect: "/cockpit" },
  {
    path: "/login",
    name: "login",
    component: LoginView,
    meta: { public: true },
  },
  {
    path: "/cockpit",
    name: "cockpit",
    component: CockpitView,
    meta: { requiresAuth: true },
  },
  {
    path: "/data",
    name: "data",
    component: DataView,
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  const token = localStorage.getItem("edu_token");
  if (to.meta.requiresAuth && !token) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.name === "login" && token) {
    return { name: "data" };
  }
  return true;
});

export default router;
