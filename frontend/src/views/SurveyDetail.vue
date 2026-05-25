<template>
  <div class="survey-detail">
    <div class="page-header">
      <h2>问卷详情</h2>
    </div>

    <el-card v-loading="loading" v-if="survey">
      <template #header>
        <div class="card-header">
          <span>{{ survey.title }}</span>
          <div>
            <el-tag :type="survey.is_active ? 'success' : 'info'">
              {{ survey.is_active ? '进行中' : '已关闭' }}
            </el-tag>
            <el-button type="primary" size="small" @click="showShareLink" style="margin-left: 10px">
              <el-icon><Share /></el-icon> 分享
            </el-button>
            <el-button type="primary" size="small" @click="$router.push(`/surveys/${survey.id}/statistics`)" style="margin-left: 10px">
              <el-icon><DataAnalysis /></el-icon> 查看统计
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="survey.description" class="description">
        <p>{{ survey.description }}</p>
      </div>

      <div class="info-row">
        <span class="label">创建时间：</span>
        <span>{{ formatDate(survey.created_at) }}</span>
      </div>
      <div class="info-row">
        <span class="label">过期时间：</span>
        <span>{{ survey.expire_at ? formatDate(survey.expire_at) : '永不过期' }}</span>
      </div>

      <el-divider />

      <h3>问题列表</h3>
      <div v-for="(question, index) in survey.questions" :key="question.id" class="question-item">
        <div class="question-header">
          <span class="question-number">问题 {{ index + 1 }}</span>
          <el-tag size="small" :type="getQuestionTypeTag(question.question_type)">
            {{ getQuestionTypeName(question.question_type) }}
          </el-tag>
          <el-tag v-if="question.is_required" size="small" type="danger">必答</el-tag>
        </div>
        <p class="question-text">{{ question.question_text }}</p>
        <ul v-if="question.options && question.options.length > 0" class="options-list">
          <li v-for="(option, optIndex) in question.options" :key="option.id">
            {{ getOptionLabel(optIndex) }}. {{ option.option_text }}
          </li>
        </ul>
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
import { useRoute } from 'vue-router'
import { surveyApi } from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()

const survey = ref(null)
const loading = ref(false)
const shareDialogVisible = ref(false)
const shareUrl = ref('')

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

function getQuestionTypeTag(type) {
  const map = {
    single_choice: '',
    multiple_choice: 'warning',
    text_input: 'success'
  }
  return map[type] || ''
}

function getQuestionTypeName(type) {
  const map = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    text_input: '填空题'
  }
  return map[type] || type
}

function getOptionLabel(index) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
  return letters[index] || `${index + 1}`
}

async function loadSurvey() {
  loading.value = true
  try {
    const result = await surveyApi.getById(route.params.id)
    survey.value = result
  } catch (error) {
    console.error('加载问卷详情失败:', error)
  } finally {
    loading.value = false
  }
}

async function showShareLink() {
  try {
    const result = await surveyApi.getShareLink(survey.value.id)
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

onMounted(() => {
  loadSurvey()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.description {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.description p {
  margin: 0;
  color: #666;
}

.info-row {
  margin-bottom: 10px;
  color: #666;
}

.info-row .label {
  color: #999;
}

.question-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.question-number {
  font-weight: bold;
}

.question-text {
  font-size: 16px;
  color: #333;
  margin: 10px 0;
}

.options-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.options-list li {
  padding: 6px 0;
  color: #666;
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
