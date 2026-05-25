<template>
  <div class="survey-statistics">
    <div class="page-header">
      <h2>投票统计 - {{ survey?.title || '加载中...' }}</h2>
    </div>

    <el-row :gutter="20" v-if="statistics">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ statistics.total_voters }}</div>
          <div class="stat-label">参与人数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ questionsCount }}</div>
          <div class="stat-label">问题数量</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="statistics && statistics.statistics" class="statistics-card">
      <template #header>
        <div class="card-header">
          <span>投票详情</span>
          <el-button type="primary" size="small" @click="exportCSV">
            <el-icon><Download /></el-icon> 导出CSV
          </el-button>
        </div>
      </template>

      <div v-for="(question, qIndex) in statistics.statistics.questions" :key="qIndex" class="question-stat">
        <el-divider />
        <h3>问题 {{ qIndex + 1 }}: {{ question.text }}</h3>
        <el-tag size="small" :type="getQuestionTypeTag(question.type)">
          {{ getQuestionTypeName(question.type) }}
        </el-tag>

        <!-- 选择题统计 - 使用图表展示 -->
        <div v-if="question.type !== 'text_input' && question.options">
          <div class="chart-container" :ref="el => setChartRef(el, qIndex)"></div>
        </div>

        <!-- 填空题统计 -->
        <div v-else-if="question.type === 'text_input'">
          <div class="fill-answers">
            <p>共收到 <strong>{{ question.total_answers || 0 }}</strong> 条回答</p>
            <el-table v-if="question.answers && question.answers.length > 0" :data="question.answers" style="width: 100%">
              <el-table-column prop="text" label="回答内容" show-overflow-tooltip />
              <el-table-column prop="voted_at" label="投票时间" width="180">
                <template #default="{ row }">
                  {{ formatDate(row.voted_at) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-card>

    <div v-if="!statistics" class="empty-state">
      <el-icon><DataAnalysis /></el-icon>
      <p>暂无统计数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { surveyApi, voteApi } from '@/api'
import * as echarts from 'echarts'

const route = useRoute()

const survey = ref(null)
const statistics = ref(null)
const questionsCount = ref(0)
const chartInstances = {}

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

function setChartRef(el, index) {
  if (el) {
    nextTick(() => {
      renderChart(el, index)
    })
  }
}

function renderChart(el, questionIndex) {
  if (!statistics.value || !statistics.value.statistics) return

  const question = statistics.value.statistics.questions[questionIndex]
  if (!question || !question.options) return

  // 销毁旧的图表实例
  if (chartInstances[questionIndex]) {
    chartInstances[questionIndex].dispose()
  }

  const chart = echarts.init(el)
  chartInstances[questionIndex] = chart

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const param = params[0]
        return `${param.name}<br/>票数: ${param.value}<br/>占比: ${question.options[param.dataIndex].percentage}%`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: question.options.map(o => o.text),
      axisLabel: {
        interval: 0,
        rotate: question.options.length > 5 ? 30 : 0,
        formatter: (value) => value.length > 15 ? value.substring(0, 15) + '...' : value
      }
    },
    yAxis: {
      type: 'value',
      name: '票数',
      minInterval: 1
    },
    series: [{
      type: 'bar',
      data: question.options.map(o => o.count),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409EFF' },
          { offset: 1, color: '#66B1FF' }
        ]),
        borderRadius: [4, 4, 0, 0]
      },
      label: {
        show: true,
        position: 'top',
        formatter: (params) => {
          const opt = question.options[params.dataIndex]
          return `${opt.count}票 (${opt.percentage}%)`
        }
      }
    }]
  }

  chart.setOption(option)
}

async function loadData() {
  try {
    // 加载问卷信息
    survey.value = await surveyApi.getById(route.params.id)
    questionsCount.value = survey.value.questions?.length || 0

    // 加载统计数据
    const result = await voteApi.getStatistics(route.params.id)
    statistics.value = result
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

async function exportCSV() {
  try {
    const blob = await voteApi.exportCSV(route.params.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `survey_${route.params.id}_votes.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('导出CSV失败:', error)
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  // 销毁所有图表实例
  Object.values(chartInstances).forEach(chart => chart.dispose())
})

function handleResize() {
  Object.values(chartInstances).forEach(chart => chart.resize())
}
</script>

<style scoped>
.stat-card {
  text-align: center;
  margin-bottom: 20px;
}

.stat-card .stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
}

.stat-card .stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 8px;
}

.statistics-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.question-stat {
  margin-bottom: 20px;
}

.question-stat h3 {
  margin: 10px 0;
  color: #333;
}

.chart-container {
  height: 300px;
  margin: 20px 0;
}

.fill-answers {
  margin-top: 16px;
}

.fill-answers p {
  color: #666;
  margin-bottom: 10px;
}
</style>
