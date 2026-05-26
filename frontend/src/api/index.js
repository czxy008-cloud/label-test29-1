import request from './request'

// 用户认证相关API
export const authApi = {
  // 用户注册
  register: (data) => request.post('/auth/register', data),

  // 用户登录
  login: (data) => request.post('/auth/login', data),

  // 获取当前用户信息
  getMe: () => request.get('/auth/me')
}

// 问卷相关API
export const surveyApi = {
  // 创建问卷
  create: (data) => request.post('/surveys', data),

  // 获取问卷列表
  list: (params) => request.get('/surveys', { params }),

  // 获取问卷详情
  getById: (id) => request.get(`/surveys/${id}`),

  // 通过分享令牌获取问卷
  getByShareToken: (token) => request.get(`/surveys/share/${token}`),

  // 更新问卷
  update: (id, data) => request.put(`/surveys/${id}`, data),

  // 删除问卷
  delete: (id) => request.delete(`/surveys/${id}`),

  // 获取分享链接
  getShareLink: (id) => request.get(`/surveys/${id}/share`)
}

// 投票相关API
export const voteApi = {
  // 提交投票
  submit: (data) => request.post('/votes', data),

  // 保存草稿
  saveDraft: (data) => request.post('/votes/draft', data),

  // 获取草稿
  getDraft: (surveyId) => request.get(`/votes/draft/survey/${surveyId}`),

  // 删除草稿
  deleteDraft: (surveyId) => request.delete(`/votes/draft/survey/${surveyId}`),

  // 获取投票统计
  getStatistics: (surveyId) => request.get(`/votes/survey/${surveyId}/statistics`),

  // 导出CSV
  exportCSV: (surveyId) => {
    const token = localStorage.getItem('token')
    return fetch(`/api/votes/survey/${surveyId}/export`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }).then(response => response.blob())
  }
}

// 管理员相关API
export const adminApi = {
  // 获取用户列表
  getUsers: (params) => request.get('/admin/users', { params }),

  // 获取用户详情
  getUserDetail: (id) => request.get(`/admin/users/${id}`),

  // 删除用户
  deleteUser: (id) => request.delete(`/admin/users/${id}`),

  // 获取所有问卷
  getAllSurveys: (params) => request.get('/admin/surveys', { params }),

  // 获取系统统计
  getSystemStats: () => request.get('/admin/statistics/summary')
}
