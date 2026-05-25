import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.is_admin || false)
  const username = computed(() => userInfo.value?.username || '')

  // 动作
  async function login(loginData) {
    try {
      const result = await authApi.login(loginData)
      token.value = result.access_token
      localStorage.setItem('token', result.access_token)

      // 获取用户信息
      const user = await authApi.getMe()
      userInfo.value = user
      localStorage.setItem('user', JSON.stringify(user))

      return result
    } catch (error) {
      throw error
    }
  }

  async function register(registerData) {
    try {
      const result = await authApi.register(registerData)
      return result
    } catch (error) {
      throw error
    }
  }

  async function fetchUserInfo() {
    try {
      const user = await authApi.getMe()
      userInfo.value = user
      localStorage.setItem('user', JSON.stringify(user))
      return user
    } catch (error) {
      throw error
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return {
    // 状态
    token,
    userInfo,
    // 计算属性
    isLoggedIn,
    isAdmin,
    username,
    // 动作
    login,
    register,
    fetchUserInfo,
    logout
  }
})
