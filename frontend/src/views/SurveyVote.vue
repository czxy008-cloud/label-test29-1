<template>
  <div class="survey-vote">
    <el-card v-loading="loading" v-if="survey" class="vote-card">
      <template #header>
        <div class="card-header">
          <span class="survey-title">{{ survey.title }}</span>
          <el-tag
            v-if="draftSavedAt"
            size="small"
            type="info"
            class="draft-tag"
          >
            草稿已保存 · {{ formatTime(draftSavedAt) }}
          </el-tag>
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
            @change="onFormChange"
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
            @change="onFormChange"
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
            @input="onFormChange"
          />
        </div>

        <div class="submit-area">
          <el-button size="large" :loading="savingDraft" @click="saveDraft">
            保存草稿
          </el-button>
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
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { surveyApi, voteApi } from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()

const survey = ref(null)
const loading = ref(false)
const submitting = ref(false)
const savingDraft = ref(false)
const hasVoted = ref(false)
const voteForm = reactive({})
const draftSavedAt = ref(null)

const AUTO_SAVE_DELAY = 1500
let autoSaveTimer = null
let hasFormChanged = false
let isRestoringDraft = false

const DRAFT_LOCAL_KEY_PREFIX = 'survey_draft_'
const draftLocalKey = computed(() => `${DRAFT_LOCAL_KEY_PREFIX}${route.params.shareToken || ''}`)

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

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function initFormDefaults() {
  sortedQuestions.value.forEach(question => {
    if (voteForm[question.id] === undefined) {
      if (question.question_type === 'multiple_choice') {
        voteForm[question.id] = []
      } else {
        voteForm[question.id] = question.question_type === 'text_input' ? '' : null
      }
    }
  })
}

function applyDraftToForm(draft) {
  if (!draft || !Array.isArray(draft.votes)) return
  isRestoringDraft = true
  try {
    draft.votes.forEach(item => {
      if (item.question_type === 'multiple_choice') {
        voteForm[item.question_id] = Array.isArray(item.option_ids) ? [...item.option_ids] : []
      } else if (item.question_type === 'single_choice') {
        voteForm[item.question_id] = Array.isArray(item.option_ids) && item.option_ids[0]
          ? item.option_ids[0]
          : null
      } else {
        voteForm[item.question_id] = item.text_value != null ? item.text_value : ''
      }
    })
    if (draft.updated_at) {
      draftSavedAt.value = draft.updated_at
    }
  } finally {
    isRestoringDraft = false
  }
}

function readLocalDraft() {
  try {
    const raw = localStorage.getItem(draftLocalKey.value)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data || !data.votes) return null
    return data
  } catch (e) {
    return null
  }
}

function writeLocalDraft(draft) {
  try {
    localStorage.setItem(draftLocalKey.value, JSON.stringify(draft))
  } catch (e) {
    // ignore
  }
}

function clearLocalDraft() {
  try {
    localStorage.removeItem(draftLocalKey.value)
  } catch (e) {
    // ignore
  }
}

async function loadSurvey() {
  loading.value = true
  try {
    const result = await surveyApi.getByShareToken(route.params.shareToken)
    survey.value = result
    initFormDefaults()

    // 尝试从后端恢复草稿（登录用户或已建立会话的匿名用户）
    let serverDraft = null
    try {
      serverDraft = await voteApi.getDraft(result.id)
    } catch (e) {
      serverDraft = null
    }

    const localDraft = readLocalDraft()

    if (serverDraft && Array.isArray(serverDraft.votes) && serverDraft.votes.length > 0) {
      applyDraftToForm(serverDraft)
      writeLocalDraft(serverDraft)
    } else if (localDraft && localDraft.survey_id === result.id) {
      applyDraftToForm(localDraft)
    }

    hasFormChanged = false
  } catch (error) {
    console.error('加载问卷失败:', error)
    if (error.response?.status === 400) {
      hasVoted.value = true
    }
  } finally {
    loading.value = false
  }
}

function buildVotePayload() {
  const votes = sortedQuestions.value
    .filter(question => {
      const value = voteForm[question.id]
      if (question.question_type === 'text_input') {
        return value != null && value !== ''
      }
      if (question.question_type === 'single_choice') {
        return value != null
      }
      return Array.isArray(value) && value.length > 0
    })
    .map(question => {
      const voteItem = { question_id: question.id }
      if (question.question_type === 'text_input') {
        voteItem.text_value = voteForm[question.id] || ''
      } else if (question.question_type === 'single_choice') {
        voteItem.option_ids = voteForm[question.id] ? [voteForm[question.id]] : []
      } else {
        voteItem.option_ids = voteForm[question.id] || []
      }
      return voteItem
    })
  return votes
}

async function saveDraft({ silent = false } = {}) {
  if (!survey.value || hasVoted.value) return
  const votes = buildVotePayload()
  if (votes.length === 0) {
    if (!silent) ElMessage.info('暂无可保存的填写内容')
    return
  }

  const payload = { survey_id: survey.value.id, votes }

  // 先写入本地
  const localPayload = {
    survey_id: survey.value.id,
    updated_at: new Date().toISOString(),
    votes: votes.map(v => {
      const q = sortedQuestions.value.find(x => x.id === v.question_id)
      return {
        question_id: v.question_id,
        question_type: q ? q.question_type : 'text_input',
        option_ids: v.option_ids || null,
        text_value: v.text_value != null ? v.text_value : null,
      }
    }),
  }
  writeLocalDraft(localPayload)
  draftSavedAt.value = localPayload.updated_at

  savingDraft.value = true
  try {
    await voteApi.saveDraft(payload)
    if (!silent) ElMessage.success('草稿已保存')
  } catch (e) {
    if (!silent) {
      const msg = e?.response?.data?.detail || '保存草稿失败，已暂存到本地'
      ElMessage.warning(msg)
    }
  } finally {
    savingDraft.value = false
  }
}

function scheduleAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    if (hasFormChanged && survey.value && !hasVoted.value) {
      hasFormChanged = false
      saveDraft({ silent: true })
    }
  }, AUTO_SAVE_DELAY)
}

function onFormChange() {
  if (isRestoringDraft) return
  hasFormChanged = true
  scheduleAutoSave()
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
    clearLocalDraft()
    draftSavedAt.value = null
    ElMessage.success('投票成功！')
  } catch (error) {
    if (error.response?.status === 400) {
      hasVoted.value = true
      clearLocalDraft()
      draftSavedAt.value = null
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadSurvey()
})

onBeforeUnmount(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
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

.draft-tag {
  margin-left: 12px;
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
  display: flex;
  justify-content: center;
  gap: 12px;
}

.voted-message {
  text-align: center;
  padding: 40px 0;
}
</style>
