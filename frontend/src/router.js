import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import Library from './views/Library.vue'
import ShowDetail from './views/ShowDetail.vue'
import Dashboard from './views/Dashboard.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/library', name: 'library', component: Library },
  { path: '/dashboard', name: 'dashboard', component: Dashboard },
  { path: '/shows/:id', name: 'show-detail', component: ShowDetail },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// The Library's filters as last seen, so the nav's "Library" link returns to
// them instead of a bare /library (which would reset them). In memory only —
// a reload starts clean. Links with their own query (Home's "See all →") win.
export const lastLibraryQuery = ref({})

router.afterEach((to) => {
  if (to.name === 'library') lastLibraryQuery.value = to.query
})
