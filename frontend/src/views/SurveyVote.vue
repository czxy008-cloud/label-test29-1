<template>
  <div class="survey-vote">
    <el-card v-loading="loading" v-if="survey" class="vote-card">
      <template #header>
        <div class="card-header">
          <span class="survey-title">{{ survey.title }}</span>
        </div>
      </template>

      <div v-if="survey.description" class="description">
        <p>{{ survey.description }}</p>
      </div>

      <el-form v-if="!hasVoted" :model="voteForm" @submit.prevent="submitVote">
        <div
          v-for="(question, qIndex) in sortedQuestions"
          :key="question.id"
          class="question-item"
        >
          <div class="question-header">
            <span class="question-number">
              {{ qIndex + 1 }}. {{ question.question_text }}
              <el-tag v-if="question.is_required" size="small" type="danger" style="margin-left: 8px">必答</el-tag>
            </span>
          </div>

          <!-- 单选题 -->
          <el-radio-group
            v-if="question.question_type === 'single_choice'"
            v-model="voteForm[question.id]"
          >
            <div
              v-for="option in sortedOptions(question)"
              :key="option.id"
              class="option-item"
            >
              <el-radio :value="option.id">
                {{ getOptionLabel(question.options.indexOf(option)) }}. {{ option.option_text }}
              </el-radio>
            </div>
          </el-radio-group>

          <!-- 多选题 -->
          <el-checkbox-group
            v-else-if="question.question_type === 'multiple_choice'"
            v-model="voteForm[question.id]"
          >
            <div
              v-for="option in sortedOptions(question)"
              :key="option.id"
              class="option-item"
            >
              <el-checkbox :value="option.id">
                {{ getOptionLabel(question.options.indexOf(option)) }}. {{ option.option_text }}
              </el-checkbox>
            </div>
          </el-checkbox-group>

          <!-- 填空题 -->
          <el-input
            v-else-if="question.question_type === 'text_input'"
            v-model="voteForm[question.id]"
            type="textarea"
            :rows="3"
            placeholder="请输入您的回答"
          />
        </div>

        <div class="submit-area">
          <el-button type="primary" size="large" :loading="submitting" @click="submitVote">
            提交投票
          </el-button>
        </div>
      </el-form>

      <div v-else class="voted-message">
        <el-result
          icon="success"
          title="感谢您的参与！"
          sub-title="您已成功提交投票"
        />
      </div>
    </el-card>

    <div v-if="!loading && !survey" class="empty-state">
      <el-icon><Warning /></el-icon>
      <p>问卷不存在或已关闭</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { surveyApi, voteApi } from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()

const survey = ref(null)
const loading = ref(false)
const submitting = ref(false)
const hasVoted = ref(false)
const voteForm = reactive({})

const sortedQuestions = computed(() => {
  if (!survey.value || !survey.value.questions) return []
  return [...survey.value.questions].sort((a, b) => a.sort_order - b.sort_order)
})

function sortedOptions(question) {
  if (!question.options) return []
  return [...question.options].sort((a, b) => a.sort_order - b.sort_order)
}

function getOptionLabel(index) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
  return letters[index] || `${index + 1}`
}

async function loadSurvey() {
  loading.value = true
  try {
    const result = await surveyApi.getByShareToken(route.params.shareToken)
    survey.value = result

    // 初始化表单
    sortedQuestions.value.forEach(question => {
      if (question.question_type === 'multiple_choice') {
        voteForm[question.id] = []
      } else {
        voteForm[question.id] = question.question_type === 'text_input' ? '' : null
      }
    })
  } catch (error) {
    console.error('加载问卷失败:', error)
    if (error.response?.status === 400) {
      // 问卷已关闭或过期
      hasVoted.value = true
    }
  } finally {
    loading.value = false
  }
}

async function submitVote() {
  // 验证必答题
  for (const question of sortedQuestions.value) {
    if (question.is_required) {
      const value = voteForm[question.id]
      if (question.question_type === 'text_input') {
        if (!value || !value.trim()) {
          ElMessage.error(`请回答问题"${question.question_text}"`)
          return
        }
      } else {
        if (!value || (Array.isArray(value) && value.length === 0)) {
          ElMessage.error(`请回答问题"${question.question_text}"`)
          return
        }
      }
    }
  }

  // 构建投票数据
  const votes = sortedQuestions.value.map(question => {
    const voteItem = {
      question_id: question.id
    }

    if (question.question_type === 'text_input') {
      voteItem.text_value = voteForm[question.id] || ''
    } else if (question.question_type === 'single_choice') {
      voteItem.option_ids = voteForm[question.id] ? [voteForm[question.id]] : []
    } else {
      voteItem.option_ids = voteForm[question.id] || []
    }

    return voteItem
  })

  submitting.value = true
  try {
    await voteApi.submit({
      survey_id: survey.value.id,
      votes
    })
    hasVoted.value = true
    ElMessage.success('投票成功！')
  } catch (error) {
    if (error.response?.status === 400) {
      hasVoted.value = true
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadSurvey()
})
</script>

<style scoped>
.survey-vote {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.vote-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.survey-title {
  font-size: 20px;
  font-weight: bold;
  color: #333;
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

.question-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.question-header {
  margin-bottom: 16px;
}

.question-number {
  font-size: 16px;
  color: #333;
}

.option-item {
  padding: 8px 0;
}

.submit-area {
  text-align: center;
  margin-top: 30px;
}

.voted-message {
  text-align: center;
  padding: 40px 0;
}
</style>
