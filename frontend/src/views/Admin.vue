<template>
  <div class="admin-panel">
    <div class="page-header">
      <h2>管理员后台</h2>
    </div>

    <!-- 系统统计 -->
    <el-card class="stats-card">
      <template #header>
        <span>系统概览</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <el-icon :size="48" color="#409EFF"><User /></el-icon>
            <div class="stat-value">{{ systemStats.total_users || 0 }}</div>
            <div class="stat-label">总用户数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-icon :size="48" color="#67C23A"><Document /></el-icon>
            <div class="stat-value">{{ systemStats.total_surveys || 0 }}</div>
            <div class="stat-label">总问卷数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-icon :size="48" color="#E6A23C"><CircleCheck /></el-icon>
            <div class="stat-value">{{ systemStats.active_surveys || 0 }}</div>
            <div class="stat-label">进行中问卷</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <el-icon :size="48" color="#F56C6C"><DataLine /></el-icon>
            <div class="stat-value">{{ systemStats.total_votes || 0 }}</div>
            <div class="stat-label">总投票数</div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 用户管理 -->
    <el-card class="section-card">
      <template #header>
        <span>用户管理</span>
      </template>

      <el-table :data="users" v-loading="usersLoading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="is_admin" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'danger' : ''">
              {{ row.is_admin ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              :disabled="row.is_admin"
              @click="deleteUser(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 问卷管理 -->
    <el-card class="section-card">
      <template #header>
        <span>问卷管理</span>
      </template>

      <el-table :data="allSurveys" v-loading="surveysLoading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="问卷标题" />
        <el-table-column prop="creator_id" label="创建者ID" width="100" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '进行中' : '已关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/surveys/${row.id}/statistics`)">
              统计
            </el-button>
            <el-button link type="danger" @click="deleteSurvey(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi, surveyApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const systemStats = ref({})
const users = ref([])
const allSurveys = ref([])
const usersLoading = ref(false)
const surveysLoading = ref(false)

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

async function loadSystemStats() {
  try {
    systemStats.value = await adminApi.getSystemStats()
  } catch (error) {
    console.error('加载系统统计失败:', error)
  }
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const result = await adminApi.getUsers({ limit: 50 })
    users.value = Array.isArray(result) ? result : (result.users || [])
  } catch (error) {
    console.error('加载用户列表失败:', error)
  } finally {
    usersLoading.value = false
  }
}

async function loadSurveys() {
  surveysLoading.value = true
  try {
    const result = await adminApi.getAllSurveys({ limit: 50 })
    allSurveys.value = Array.isArray(result) ? result : (result.surveys || [])
  } catch (error) {
    console.error('加载问卷列表失败:', error)
  } finally {
    surveysLoading.value = false
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户"${user.username}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await adminApi.deleteUser(user.id)
    ElMessage.success('删除成功')
    loadUsers()
    loadSystemStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除用户失败:', error)
    }
  }
}

async function deleteSurvey(survey) {
  try {
    await ElMessageBox.confirm(
      `确定要删除问卷"${survey.title}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await surveyApi.delete(survey.id)
    ElMessage.success('删除成功')
    loadSurveys()
    loadSystemStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除问卷失败:', error)
    }
  }
}

onMounted(() => {
  loadSystemStats()
  loadUsers()
  loadSurveys()
})
</script>

<style scoped>
.stats-card {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card .stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
  margin: 10px 0;
}

.stat-card .stat-label {
  font-size: 14px;
  color: #999;
}

.section-card {
  margin-top: 20px;
}
</style>
