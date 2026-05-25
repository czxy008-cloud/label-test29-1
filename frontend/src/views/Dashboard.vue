<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>欢迎回来，{{ userStore.username }}！</h2>
      <p>以下是您的问卷概览</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="stat-card">
          <el-icon :size="48" color="#409EFF"><Document /></el-icon>
          <div class="stat-value">{{ surveyCount }}</div>
          <div class="stat-label">我的问卷</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <el-icon :size="48" color="#67C23A"><Check /></el-icon>
          <div class="stat-value">{{ activeCount }}</div>
          <div class="stat-label">进行中</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <el-icon :size="48" color="#E6A23C"><DataLine /></el-icon>
          <div class="stat-value">{{ totalVotes }}</div>
          <div class="stat-label">总投票数</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-surveys">
      <template #header>
        <div class="card-header">
          <span>最近创建的问卷</span>
          <el-button type="primary" size="small" @click="$router.push('/surveys/create')">
            <el-icon><Plus /></el-icon> 创建问卷
          </el-button>
        </div>
      </template>

      <el-table v-if="recentSurveys.length > 0" :data="recentSurveys" style="width: 100%">
        <el-table-column prop="title" label="问卷标题" />
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
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/surveys/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="$router.push(`/surveys/${row.id}/statistics`)">统计</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="empty-state">
        <el-icon><Document /></el-icon>
        <p>暂无问卷，点击上方按钮创建您的第一份问卷</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { surveyApi } from '@/api'

const userStore = useUserStore()

const surveyCount = ref(0)
const activeCount = ref(0)
const totalVotes = ref(0)
const recentSurveys = ref([])

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

async function loadData() {
  try {
    const result = await surveyApi.list({ limit: 5 })
    recentSurveys.value = result.surveys || []
    surveyCount.value = result.total || 0
    activeCount.value = recentSurveys.value.filter(s => s.is_active).length
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-card {
  text-align: center;
  margin-bottom: 20px;
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recent-surveys {
  margin-top: 20px;
}
</style>
