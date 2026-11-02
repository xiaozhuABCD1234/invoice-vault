import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/api/types'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    roles?: Role[]
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: { name: 'dashboard' },
      },
      {
        path: 'uploads',
        name: 'uploads',
        component: () => import('@/views/uploads/UploadsView.vue'),
        meta: { title: '上传' },
      },
      {
        path: 'review',
        name: 'review',
        component: () => import('@/views/review/ReviewQueueView.vue'),
        meta: { title: '审核队列' },
      },
      {
        path: 'review/:jobId',
        name: 'review-detail',
        component: () => import('@/views/review/ReviewDetailView.vue'),
        meta: { title: '审核详情' },
      },
      {
        path: 'invoices',
        name: 'invoices',
        component: () => import('@/views/invoices/InvoicesView.vue'),
        meta: { title: '发票' },
      },
      {
        path: 'invoices/:id',
        name: 'invoice-detail',
        component: () => import('@/views/invoices/InvoiceDetailView.vue'),
        meta: { title: '发票详情' },
      },
      {
        path: 'payments',
        name: 'payments',
        component: () => import('@/views/payments/PaymentsView.vue'),
        meta: { title: '付款' },
      },
      {
        path: 'payments/:id',
        name: 'payment-detail',
        component: () => import('@/views/payments/PaymentDetailView.vue'),
        meta: { title: '付款详情' },
      },
      {
        path: 'reconciliation',
        name: 'reconciliation',
        component: () => import('@/views/reconciliation/ReconciliationView.vue'),
        meta: { title: '对账' },
      },
      {
        path: 'exports',
        name: 'exports',
        component: () => import('@/views/exports/ExportsView.vue'),
        meta: { title: '导出' },
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'admin/users',
        name: 'admin-users',
        component: () => import('@/views/admin/UsersView.vue'),
        meta: { title: '用户管理', roles: ['admin'] },
      },
      {
        path: 'admin/audit',
        name: 'admin-audit',
        component: () => import('@/views/admin/AuditView.vue'),
        meta: { title: '审计日志', roles: ['admin'] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.initialized) {
    await auth.restore()
  }

  if (to.name === 'login') {
    if (auth.isAuthenticated) {
      return { name: 'dashboard' }
    }
    return true
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  const requiredRoles = to.meta.roles
  if (requiredRoles && requiredRoles.length > 0) {
    const role = auth.user?.role
    if (!role || !requiredRoles.includes(role)) {
      return { name: 'dashboard' }
    }
  }

  return true
})

router.afterEach((to) => {
  if (typeof document === 'undefined') return
  document.title = to.meta.title
    ? `${to.meta.title} · 发票管理系统`
    : '发票管理系统'
})

export default router
