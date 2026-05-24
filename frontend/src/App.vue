<template>
  <el-container class="app-shell">
    <el-aside width="264px" class="app-sidebar">
      <div class="brand">
        <div class="brand-mark">实</div>
        <div>
          <div class="brand-title">实验智评</div>
          <div class="brand-subtitle">课程实验报告智能评阅系统</div>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="sidebar-menu">
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>工作台</span>
        </el-menu-item>

        <el-sub-menu index="base">
          <template #title>
            <el-icon><Collection /></el-icon>
            <span>基础数据</span>
          </template>
          <el-menu-item index="/courses">课程管理</el-menu-item>
          <el-menu-item index="/classes">教学班管理</el-menu-item>
          <el-menu-item index="/students">学生名单</el-menu-item>
          <el-menu-item index="/archives">学期归档</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="experiment">
          <template #title>
            <el-icon><Memo /></el-icon>
            <span>实验与评分</span>
          </template>
          <el-menu-item index="/experiments">实验任务</el-menu-item>
          <el-menu-item index="/rubrics">评分标准</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="workflow">
          <template #title>
            <el-icon><Operation /></el-icon>
            <span>批改流程</span>
          </template>
          <el-menu-item index="/grading-tasks">批改任务创建</el-menu-item>
          <el-menu-item index="/report-upload">报告上传</el-menu-item>
          <el-menu-item index="/report-parsing">解析与脱敏</el-menu-item>
          <el-menu-item index="/ai-scoring">AI 初评</el-menu-item>
          <el-menu-item index="/review">教师复核</el-menu-item>
          <el-menu-item index="/export-analysis">成绩导出与分析</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="settings">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </template>
          <el-menu-item index="/ai-config">AI 配置</el-menu-item>
          <el-menu-item index="/system-data">系统数据管理</el-menu-item>
          <el-menu-item index="/about">关于实验智评</el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-footer">
        <div class="runtime-dot"></div>
        <span>本地单机运行</span>
      </div>
    </el-aside>

    <el-container class="content-shell">
      <el-header class="app-header">
        <div class="header-title-block">
          <div class="header-title">{{ $route.meta.title || '实验智评' }}</div>
          <div class="header-subtitle">
            {{ $route.meta.description || '面向高校课程实验报告的智能评阅系统' }}
          </div>
        </div>
        <div class="header-actions">
          <el-tag effect="plain" type="success">V2 本地版</el-tag>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>

      <el-alert
        v-if="globalApiError"
        class="global-api-error"
        type="error"
        show-icon
        closable
        :title="globalApiError"
        @close="globalApiError = ''"
      />
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { Collection, DataBoard, Memo, Operation, Setting } from '@element-plus/icons-vue'

const globalApiError = ref('')
let globalApiErrorTimer = null

function handleApiError(event) {
  globalApiError.value = event.detail?.message || '请求失败'
  if (globalApiErrorTimer) window.clearTimeout(globalApiErrorTimer)
  globalApiErrorTimer = window.setTimeout(() => {
    globalApiError.value = ''
  }, 10000)
}

onMounted(() => {
  window.addEventListener('app-api-error', handleApiError)
})

onUnmounted(() => {
  window.removeEventListener('app-api-error', handleApiError)
  if (globalApiErrorTimer) window.clearTimeout(globalApiErrorTimer)
})
</script>
