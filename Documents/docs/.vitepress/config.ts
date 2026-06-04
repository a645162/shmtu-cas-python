import { defineConfig } from 'vitepress'

function resolveBase() {
  const repo = process.env.GITHUB_REPOSITORY?.split('/')[1]
  if (!process.env.GITHUB_ACTIONS || !repo) {
    return '/'
  }
  return repo.endsWith('.github.io') ? '/' : `/${repo}/`
}

export default defineConfig({
  base: resolveBase(),
  lang: 'zh-CN',
  title: 'shmtu-cas-python 库参考',
  description: '上海海事大学 CAS / 一卡通 / 热水查询 Python 客户端库',
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: '概览', link: '/' },
      { text: '快速开始', link: '/getting-started' },
      { text: 'API 索引', link: '/api-overview' },
      { text: '典型用例', link: '/examples/index' },
    ],
    sidebar: [
      {
        text: '概览',
        items: [
          { text: '文档首页', link: '/' },
          { text: '快速开始', link: '/getting-started' },
          { text: '跨语言对照', link: '/cross-language' },
        ],
      },
      {
        text: 'shmtu_cas.datatype',
        items: [
          { text: 'BillType', link: '/datatype/bill-type' },
          { text: 'BillItem', link: '/datatype/bill-item' },
          { text: 'BillItemStatus', link: '/datatype/bill-item-status' },
        ],
      },
      {
        text: 'shmtu_cas.auth',
        items: [
          { text: 'CasAuth', link: '/auth/cas-auth' },
          { text: 'CookieManager', link: '/auth/cookie-manager' },
          { text: 'EpayAuth', link: '/auth/epay-auth' },
          { text: 'WechatAuth', link: '/auth/wechat-auth' },
        ],
      },
      {
        text: 'shmtu_cas.session',
        items: [
          { text: 'LoginProbe / Challenge / Result', link: '/session/login-states' },
          { text: 'SessionProbe & Exceptions', link: '/session/exceptions' },
        ],
      },
      {
        text: 'shmtu_cas.captcha',
        items: [
          { text: 'CaptchaResolver 协议', link: '/captcha/resolver' },
          { text: '4 种内置 Resolver', link: '/captcha/built-in' },
          { text: 'TCP / HTTP OCR 客户端', link: '/captcha/ocr-clients' },
        ],
      },
      {
        text: 'shmtu_cas.parser',
        items: [
          { text: '账单 HTML 解析', link: '/parser/bill' },
          { text: '热水 HTML 解析', link: '/parser/hot-water' },
          { text: 'CSV 导出', link: '/parser/csv-export' },
        ],
      },
      {
        text: 'shmtu_cas.classifier',
        items: [
          { text: 'BillClassifier', link: '/classifier/bill-classifier' },
          { text: 'PositionTranslator', link: '/classifier/position-translator' },
        ],
      },
      {
        text: 'shmtu_cas.sync',
        items: [
          { text: '状态机与进度', link: '/sync/state-machine' },
          { text: 'SyncRangePreset / SyncOptions', link: '/sync/options' },
          { text: 'BillStore 接口', link: '/sync/bill-store' },
          { text: '同步入口函数', link: '/sync/entry-points' },
        ],
      },
      {
        text: 'shmtu_cas.cli',
        items: [{ text: '命令行入口', link: '/cli/index' }],
      },
      {
        text: '典型用例',
        items: [
          { text: '用例索引', link: '/examples/index' },
          { text: '手动验证码 + 拉账单 + 导出', link: '/examples/manual-captcha' },
          { text: 'HTTP OCR 自动登录', link: '/examples/http-ocr' },
          { text: '增量同步（单账号）', link: '/examples/incremental' },
          { text: '多账号并行同步', link: '/examples/parallel' },
          { text: '本地 ONNX 自定义 Resolver', link: '/examples/local-onnx' },
          { text: '账单分类 + 位置翻译', link: '/examples/classifier' },
        ],
      },
      {
        text: '附录',
        items: [
          { text: 'API 索引', link: '/api-overview' },
          { text: '异步设计要点', link: '/async-design' },
          { text: '测试与覆盖率', link: '/testing' },
          { text: '项目结构', link: '/project-structure' },
        ],
      },
    ],
    outline: [2, 3],
    search: {
      provider: 'local',
    },
    footer: {
      message: 'shmtu-cas-python Library Docs',
      copyright: 'Copyright © shmtu-cas-python',
    },
  },
})
