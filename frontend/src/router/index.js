import { createRouter, createWebHistory } from 'vue-router'

const AIConfigView = () => import('@/views/AIConfigView.vue')
const AboutView = () => import('@/views/AboutView.vue')
const AIScoringView = () => import('@/views/AIScoringView.vue')
const ArchiveView = () => import('@/views/ArchiveView.vue')
const ClassesView = () => import('@/views/ClassesView.vue')
const CoursesView = () => import('@/views/CoursesView.vue')
const DashboardView = () => import('@/views/DashboardView.vue')
const ExperimentsView = () => import('@/views/ExperimentsView.vue')
const ExportAnalysisView = () => import('@/views/ExportAnalysisView.vue')
const GradingTasksView = () => import('@/views/GradingTasksView.vue')
const ReportParsingView = () => import('@/views/ReportParsingView.vue')
const ReportUploadView = () => import('@/views/ReportUploadView.vue')
const ReviewView = () => import('@/views/ReviewView.vue')
const RubricsView = () => import('@/views/RubricsView.vue')
const StudentsView = () => import('@/views/StudentsView.vue')
const SystemDataView = () => import('@/views/SystemDataView.vue')

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      component: DashboardView,
      meta: { title: '工作台', description: '查看系统运行状态、推荐流程和关键入口' }
    },
    {
      path: '/courses',
      component: CoursesView,
      meta: { title: '课程管理', description: '维护课程基础信息，作为实验任务、评分标准和批改任务的上层组织' }
    },
    {
      path: '/classes',
      component: ClassesView,
      meta: { title: '教学班管理', description: '维护教学班基础信息，并按需要关联到不同课程' }
    },
    {
      path: '/students',
      component: StudentsView,
      meta: { title: '学生名单', description: '维护班级基础名单和课程名单副本，适配重修、补选和退课场景' }
    },
    {
      path: '/archives',
      component: ArchiveView,
      meta: { title: '学期归档', description: '按学期、课程和教学班归档批改任务，避免历史任务干扰当前教学流程' }
    },
    {
      path: '/experiments',
      component: ExperimentsView,
      meta: { title: '实验任务', description: '为课程维护实验目标、实验要求、关键截图和检查重点' }
    },
    {
      path: '/rubrics',
      component: RubricsView,
      meta: { title: '评分标准', description: '为实验任务配置分项评分标准、满分权重和重点复核标记' }
    },
    {
      path: '/grading-tasks',
      component: GradingTasksView,
      meta: { title: '批改任务创建', description: '创建由课程、教学班和实验任务共同确定的批改任务' }
    },
    {
      path: '/report-upload',
      component: ReportUploadView,
      meta: { title: '报告上传', description: '选择批改任务，批量上传 Word 实验报告并自动匹配学生' }
    },
    {
      path: '/report-parsing',
      component: ReportParsingView,
      meta: { title: '解析与脱敏', description: '解析报告正文和表格，提取图片并生成用于 AI 初评的脱敏文本' }
    },
    {
      path: '/ai-config',
      component: AIConfigView,
      meta: { title: 'AI 配置', description: '配置本地保存的大模型 API 参数，供 AI 初评调用' }
    },
    {
      path: '/ai-scoring',
      component: AIScoringView,
      meta: { title: 'AI 初评', description: '基于评分标准和脱敏报告生成 AI 分项建议分' }
    },
    {
      path: '/review',
      component: ReviewView,
      meta: { title: '教师复核', description: '逐份查看原始报告和 AI 建议，确认最终教师分' }
    },
    {
      path: '/export-analysis',
      component: ExportAnalysisView,
      meta: { title: '成绩导出与班级分析', description: '预览教师确认成绩，生成 Excel 文件并查看班级统计分析' }
    },
    {
      path: '/system-data',
      component: SystemDataView,
      meta: { title: '系统数据管理', description: '备份、恢复和清理本地数据库、上传文件与导出文件' }
    },
    {
      path: '/about',
      component: AboutView,
      meta: { title: '关于实验智评', description: '查看系统版本、作者团队、开源协议和使用边界说明' }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} - 实验智评` : '实验智评'
})

export default router
