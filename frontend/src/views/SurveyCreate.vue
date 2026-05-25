<template>
  <div class="survey-create">
    <div class="page-header">
      <h2>创建问卷</h2>
    </div>

    <!-- 步骤指示器 -->
    <el-steps :active="currentStep" finish-status="success" class="steps">
      <el-step title="基本信息" />
      <el-step title="添加问题" />
      <el-step title="完成" />
    </el-steps>

    <!-- 步骤1：基本信息 -->
    <el-card v-if="currentStep === 0" class="step-card">
      <el-form :model="surveyForm" :rules="rules" ref="surveyFormRef" label-width="100px">
        <el-form-item label="问卷标题" prop="title">
          <el-input v-model="surveyForm.title" placeholder="请输入问卷标题" maxlength="200" />
        </el-form-item>
        <el-form-item label="问卷描述">
          <el-input
            v-model="surveyForm.description"
            type="textarea"
            :rows="4"
            placeholder="请输入问卷描述（可选）"
          />
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="surveyForm.expire_at"
            type="datetime"
            placeholder="选择过期时间（可选，不选则永不过期）"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <div class="step-footer">
        <el-button type="primary" @click="nextStep">下一步</el-button>
      </div>
    </el-card>

    <!-- 步骤2：添加问题 -->
    <el-card v-if="currentStep === 1" class="step-card">
      <div class="questions-header">
        <span>问题列表（{{ questions.length }}）</span>
        <div>
          <el-dropdown @command="addQuestion">
            <el-button type="primary">
              <el-icon><Plus /></el-icon> 添加问题
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="single_choice">
                  <el-icon><CircleCheck /></el-icon> 单选题
                </el-dropdown-item>
                <el-dropdown-item command="multiple_choice">
                  <el-icon><CircleCheckFilled /></el-icon> 多选题
                </el-dropdown-item>
                <el-dropdown-item command="text_input">
                  <el-icon><Edit /></el-icon> 填空题
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <div v-if="questions.length === 0" class="empty-state">
        <el-icon><Edit /></el-icon>
        <p>还没有添加问题，请点击上方按钮添加</p>
      </div>

      <div v-else class="questions-list">
        <div
          v-for="(question, index) in questions"
          :key="index"
          class="question-item"
        >
          <div class="question-header">
            <span class="question-number">问题 {{ index + 1 }}</span>
            <div>
              <el-tag size="small" :type="getQuestionTypeTag(question.question_type)">
                {{ getQuestionTypeName(question.question_type) }}
              </el-tag>
              <el-button
                link
                type="primary"
                :icon="Top"
                :disabled="index === 0"
                @click="moveQuestion(index, -1)"
              />
              <el-button
                link
                type="primary"
                :icon="Bottom"
                :disabled="index === questions.length - 1"
                @click="moveQuestion(index, 1)"
              />
              <el-button link type="danger" :icon="Delete" @click="removeQuestion(index)" />
            </div>
          </div>

          <el-form label-width="80px">
            <el-form-item label="问题内容">
              <el-input
                v-model="question.question_text"
                placeholder="请输入问题内容"
                maxlength="500"
              />
            </el-form-item>
            <el-form-item label="必答">
              <el-switch v-model="question.is_required" />
            </el-form-item>

            <!-- 选项编辑（选择题） -->
            <template v-if="question.question_type !== 'text_input'">
              <el-form-item label="选项">
                <div class="options-list">
                  <div
                    v-for="(option, optIndex) in question.options"
                    :key="optIndex"
                    class="option-item"
                  >
                    <span class="option-label">{{ getOptionLabel(optIndex, question.question_type) }}</span>
                    <el-input
                      v-model="option.option_text"
                      placeholder="请输入选项内容"
                      maxlength="500"
                    />
                    <el-button
                      link
                      type="danger"
                      :icon="Delete"
                      :disabled="question.options.length <= 2"
                      @click="removeOption(question, optIndex)"
                    />
                  </div>
                  <el-button
                    type="primary"
                    plain
                    size="small"
                    :icon="Plus"
                    @click="addOption(question)"
                  >
                    添加选项
                  </el-button>
                </div>
              </el-form-item>
            </template>
          </el-form>
        </div>
      </div>

      <div class="step-footer">
        <el-button @click="prevStep">上一步</el-button>
        <el-button type="primary" :disabled="questions.length === 0" @click="submitSurvey">
          创建问卷
        </el-button>
      </div>
    </el-card>

    <!-- 步骤3：完成 -->
    <el-card v-if="currentStep === 2" class="step-card success-card">
      <el-result
        icon="success"
        title="问卷创建成功！"
        :sub-title="`您可以分享此链接让他人参与投票`"
      >
        <template #extra>
          <div class="share-link">
            <code>{{ shareUrl }}</code>
            <el-button type="primary" @click="copyShareLink">
              <el-icon><CopyDocument /></el-icon> 复制链接
            </el-button>
          </div>
          <el-button type="primary" @click="$router.push('/surveys')">
            返回列表
          </el-button>
          <el-button @click="$router.push(`/surveys/${newSurveyId}/statistics`)">
            查看统计
          </el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { surveyApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Top, Bottom, CircleCheck, CircleCheckFilled, Edit, CopyDocument } from '@element-plus/icons-vue'

const router = useRouter()

const currentStep = ref(0)
const surveyFormRef = ref(null)
const newSurveyId = ref(null)
const shareUrl = ref('')

const surveyForm = reactive({
  title: '',
  description: '',
  expire_at: null
})

const questions = ref([])

const rules = {
  title: [
    { required: true, message: '请输入问卷标题', trigger: 'blur' },
    { min: 1, max_length: 200, message: '标题长度在1-200个字符', trigger: 'blur' }
  ]
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

function getOptionLabel(index, type) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
  return letters[index] || `${index + 1}.`
}

function addQuestion(type) {
  const newQuestion = {
    question_text: '',
    question_type: type,
    is_required: true,
    sort_order: questions.value.length,
    options: type !== 'text_input' ? [
      { option_text: '', sort_order: 0 },
      { option_text: '', sort_order: 1 }
    ] : []
  }
  questions.value.push(newQuestion)
}

function removeQuestion(index) {
  questions.value.splice(index, 1)
  // 更新排序
  questions.value.forEach((q, i) => {
    q.sort_order = i
  })
}

function moveQuestion(index, direction) {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= questions.value.length) return

  const temp = questions.value[index]
  questions.value[index] = questions.value[newIndex]
  questions.value[newIndex] = temp

  // 更新排序
  questions.value.forEach((q, i) => {
    q.sort_order = i
  })
}

function addOption(question) {
  question.options.push({
    option_text: '',
    sort_order: question.options.length
  })
}

function removeOption(question, index) {
  if (question.options.length <= 2) return
  question.options.splice(index, 1)
  // 更新排序
  question.options.forEach((opt, i) => {
    opt.sort_order = i
  })
}

function nextStep() {
  if (surveyFormRef.value) {
    surveyFormRef.value.validate((valid) => {
      if (valid) {
        currentStep.value = 1
      }
    })
  }
}

function prevStep() {
  currentStep.value = 0
}

async function submitSurvey() {
  // 验证问题
  for (let i = 0; i < questions.value.length; i++) {
    const q = questions.value[i]
    if (!q.question_text.trim()) {
      ElMessage.error(`请填写问题 ${i + 1} 的内容`)
      return
    }
    if (q.question_type !== 'text_input') {
      for (let j = 0; j < q.options.length; j++) {
        if (!q.options[j].option_text.trim()) {
          ElMessage.error(`请填写问题 ${i + 1} 的所有选项内容`)
          return
        }
      }
    }
  }

  try {
    const result = await surveyApi.create({
      ...surveyForm,
      questions: questions.value
    })

    newSurveyId.value = result.id
    const baseUrl = window.location.origin
    shareUrl.value = `${baseUrl}/survey/${result.share_token}`
    currentStep.value = 2
  } catch (error) {
    console.error('创建问卷失败:', error)
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
</script>

<style scoped>
.steps {
  margin-bottom: 30px;
  max-width: 600px;
}

.step-card {
  max-width: 800px;
  margin: 0 auto;
}

.step-footer {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.questions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.question-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  background: #fafafa;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.question-number {
  font-weight: bold;
  font-size: 16px;
}

.options-list {
  width: 100%;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.option-label {
  font-weight: bold;
  color: #409EFF;
  min-width: 30px;
}

.option-item .el-input {
  flex: 1;
}

.success-card {
  max-width: 600px;
}

.share-link {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  margin: 20px 0;
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
</style>
