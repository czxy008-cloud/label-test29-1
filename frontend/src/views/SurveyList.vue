<template>
  <div class="survey-list">
    <div class="page-header">
      <h2>我的问卷</h2>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>问卷列表</span>
          <div>
            <el-button type="primary" @click="$router.push('/surveys/create')">
              <el-icon><Plus /></el-icon> 创建问卷
            </el-button>
          </div>
        </div>
      </template>

      <el-table v-if="surveys.length > 0" :data="surveys" style="width: 100%">
        <el-table-column prop="title" label="问卷标题" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
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
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/surveys/${row.id}`)">详情</el-button>
            <el-button link type="primary" @click="$router.push(`/surveys/${row.id}/statistics`)">统计</el-button>
            <el-button link type="primary" @click="showShareLink(row)">分享</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="empty-state">
        <el-icon><Document /></el-icon>
        <p>暂无问卷</p>
        <el-button type="primary" @click="$router.push('/surveys/create')">创建问卷</el-button>
      </div>

      <div class="pagination" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadSurveys"
        />
      </div>
    </el-card>

    <!-- 分享链接对话框 -->
    <el-dialog v-model="shareDialogVisible" title="分享链接" width="500px">
      <div class="share-link">
        <code>{{ shareUrl }}</code>
        <el-button type="primary" @click="copyShareLink">
          <el-icon><CopyDocument /></el-icon> 复制
        </el-button>
      </div>
      <p class="share-tip">将此链接分享给他人，他们可以通过该链接参与投票</p>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { surveyApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const surveys = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const shareDialogVisible = ref(false)
const shareUrl = ref('')
const currentSurvey = ref(null)

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

async function loadSurveys() {
  try {
    const result = await surveyApi.list({
      skip: (currentPage.value - 1) * pageSize,
      limit: pageSize
    })
    surveys.value = result.surveys || []
    total.value = result.total || 0
  } catch (error) {
    console.error('加载问卷列表失败:', error)
  }
}

async function showShareLink(survey) {
  currentSurvey.value = survey
  try {
    const result = await surveyApi.getShareLink(survey.id)
    const baseUrl = window.location.origin
    shareUrl.value = `${baseUrl}/survey/${result.share_token}`
    shareDialogVisible.value = true
  } catch (error) {
    console.error('获取分享链接失败:', error)
  }
}

async function copyShareLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    ElMessage.success('链接已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function handleDelete(survey) {
  try {
    await ElMessageBox.confirm(
      `确定要删除问卷"${survey.title}"吗？此操作不可恢复。`,
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
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除问卷失败:', error)
    }
  }
}

onMounted(() => {
  loadSurveys()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.share-link {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
}

.share-link code {
  flex: 1;
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
  color: #409EFF;
  word-break: break-all;
  font-size: 14px;
}

.share-tip {
  color: #999;
  font-size: 13px;
  margin-top: 12px;
  text-align: center;
}
</style>
