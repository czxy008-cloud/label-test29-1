import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '首页', requiresAuth: true }
  },
  {
    path: '/surveys',
    name: 'SurveyList',
    component: () => import('@/views/SurveyList.vue'),
    meta: { title: '我的问卷', requiresAuth: true }
  },
  {
    path: '/surveys/create',
    name: 'SurveyCreate',
    component: () => import('@/views/SurveyCreate.vue'),
    meta: { title: '创建问卷', requiresAuth: true }
  },
  {
    path: '/surveys/:id',
    name: 'SurveyDetail',
    component: () => import('@/views/SurveyDetail.vue'),
    meta: { title: '问卷详情', requiresAuth: true }
  },
  {
    path: '/surveys/:id/statistics',
    name: 'SurveyStatistics',
    component: () => import('@/views/SurveyStatistics.vue'),
    meta: { title: '投票统计', requiresAuth: true }
  },
  {
    path: '/survey/:shareToken',
    name: 'SurveyVote',
    component: () => import('@/views/SurveyVote.vue'),
    meta: { title: '参与投票', requiresAuth: false }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/Admin.vue'),
    meta: { title: '管理员后台', requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面未找到', requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 在线投票调查系统`
  }

  // 检查是否需要认证
  if (to.meta.requiresAuth) {
    if (!userStore.isLoggedIn) {
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }

    // 检查是否需要管理员权限
    if (to.meta.requiresAdmin && !userStore.isAdmin) {
      // 不是管理员，重定向到首页
      next('/')
      return
    }
  }

  // 如果已登录用户访问登录或注册页，重定向到首页
  if ((to.path === '/login' || to.path === '/register') && userStore.isLoggedIn) {
    next('/dashboard')
    return
  }

  next()
})

export default router
