<template>
  <div class="about-page">
    <section class="about-hero">
      <div>
        <div class="eyebrow">关于系统</div>
        <h1>实验智评</h1>
        <p>面向高校课程实验报告的智能评阅系统</p>
      </div>
      <div class="about-version">
        <div class="version-label">当前版本</div>
        <div class="version-value">V2 本地版</div>
      </div>
    </section>

    <el-row :gutter="18">
      <el-col :xs="24" :lg="14">
        <el-card class="page-card about-card">
          <template #header>
            <div class="toolbar header-tight">
              <div>
                <strong>版权与作者信息</strong>
                <div class="muted">用于标识系统来源、作者归属和开源协议。</div>
              </div>
            </div>
          </template>

          <div class="info-list">
            <div class="info-row">
              <span>系统名称</span>
              <strong>实验智评：面向高校课程实验报告的智能评阅系统</strong>
            </div>
            <div class="info-row">
              <span>维护团队</span>
              <strong>包头师范学院-人工智能科研虚拟教研室、计算机网络课程教学团队</strong>
            </div>
            <div class="info-row">
              <span>应用场景支持</span>
              <strong>计算机网络课程教学团队</strong>
            </div>
            <div class="info-row">
              <span>版权声明</span>
              <strong>Copyright (c) 2026 包头师范学院-人工智能科研虚拟教研室、计算机网络课程教学团队</strong>
            </div>
            <div class="info-row">
              <span>开源协议</span>
              <strong>MIT License</strong>
            </div>
            <div class="info-row">
              <span>项目地址</span>
              <a href="https://github.com/hrqz007/AIReportGrader" target="_blank" rel="noopener noreferrer">
                https://github.com/hrqz007/AIReportGrader
              </a>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="page-card about-card">
          <template #header>
            <div class="toolbar header-tight">
              <div>
                <strong>使用边界</strong>
                <div class="muted">系统定位为教师本地辅助评阅工具。</div>
              </div>
            </div>
          </template>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="AI 初评结果仅作为建议分，最终成绩以教师确认分为准。"
          />
          <el-alert
            class="about-alert"
            type="warning"
            :closable="false"
            show-icon
            title="请勿在公开仓库、截图或演示材料中泄露 API Key、学生名单和真实实验报告。"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card about-card">
      <template #header>
        <div class="toolbar header-tight">
          <div>
            <strong>MIT License 摘要</strong>
            <div class="muted">完整协议内容以项目根目录 LICENSE 文件为准。</div>
          </div>
        </div>
      </template>

      <el-row :gutter="14">
        <el-col :xs="24" :sm="12" :lg="6" v-for="item in licensePoints" :key="item.title">
          <div class="license-point">
            <div class="license-title">{{ item.title }}</div>
            <div class="license-desc">{{ item.desc }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
const licensePoints = [
  { title: '允许使用', desc: '可在教学、科研和本地管理场景中使用本系统。' },
  { title: '允许修改', desc: '可根据课程、学校或团队需要进行二次开发。' },
  { title: '允许分发', desc: '可在保留协议和版权声明的前提下分发副本。' },
  { title: '免责声明', desc: '软件按现状提供，作者不承担使用风险和结果责任。' }
]
</script>

<style scoped>
.about-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.about-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 22px;
  padding: 28px 30px;
  border: 1px solid var(--border);
  border-left: 7px solid var(--primary);
  border-radius: 18px;
  background:
    radial-gradient(circle at 86% 18%, rgba(14, 165, 233, 0.16), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #ecfbff 100%);
  box-shadow: var(--card-shadow);
}

.about-hero h1 {
  margin: 8px 0 6px;
  color: #082f49;
  font-size: 42px;
  line-height: 1.05;
}

.about-hero p {
  margin: 0;
  color: #315d75;
  font-size: 18px;
}

.eyebrow {
  color: var(--primary);
  font-weight: 850;
}

.about-version {
  min-width: 150px;
  padding: 16px 18px;
  border-radius: 16px;
  background: #e0f7ff;
  border: 1px solid #a7dff2;
  text-align: center;
}

.version-label {
  color: var(--text-muted);
  font-size: 13px;
}

.version-value {
  margin-top: 8px;
  color: #075985;
  font-size: 22px;
  font-weight: 900;
}

.about-card {
  height: 100%;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f5fbff;
  border: 1px solid #d9edf6;
}

.info-row span {
  color: var(--text-muted);
  font-weight: 750;
}

.info-row strong,
.info-row a {
  color: #0f3650;
  word-break: break-word;
}

.about-alert {
  margin-top: 14px;
}

.license-point {
  min-height: 116px;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid #cfe3ee;
  background: linear-gradient(180deg, #ffffff 0%, #f1fbff 100%);
}

.license-title {
  color: #075985;
  font-size: 18px;
  font-weight: 900;
}

.license-desc {
  margin-top: 10px;
  color: var(--text-muted);
  line-height: 1.65;
}

@media (max-width: 780px) {
  .about-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .about-hero h1 {
    font-size: 34px;
  }

  .info-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}
</style>
