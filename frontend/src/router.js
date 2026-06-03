import { createRouter, createWebHistory } from 'vue-router'
import Library from './views/Library.vue'
import ShowDetail from './views/ShowDetail.vue'

const routes = [
  { path: '/', name: 'library', component: Library },
  { path: '/shows/:id', name: 'show-detail', component: ShowDetail },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
