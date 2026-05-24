const { studyRecordAPI, vocabAPI, userAPI } = require('../../utils/api')

/** 首页 - 学习概览 */
Page({
  data: {
    greeting: '',
    today: '',
    todayWords: 0,
    totalWords: 0,
    streak: 7,
    progress: 0,
    targetWords: 50,
    quickActions: [
      { icon: '📚', label: '创建单词书', color: '#5eb97d', action: 'createBook' },
    ],
    recentWords: [],
    tips: '每天坚持学习20分钟，效果更好哦！',
    isLoading: true,
    showModal: false,
    bookForm: {
      name: '',
      description: ''
    }
  },

  onLoad() {
    this.setToday()
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.setGreeting()
      this.loadData()
    } else {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.loadData()
    }
  },

  /** 根据当前时间设置问候语 */
  setGreeting() {
    const hour = new Date().getHours()
    let greeting = '早上好'
    if (hour >= 12 && hour < 18) {
      greeting = '下午好'
    } else if (hour >= 18) {
      greeting = '晚上好'
    }
    const userInfo = wx.getStorageSync('userInfo')
    const nickname = userInfo?.nickname || '学习者'
    this.setData({ greeting: `${greeting}，${nickname}` })
  },

  /** 设置当前日期显示 */
  setToday() {
    const now = new Date()
    const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    const month = now.getMonth() + 1
    const day = now.getDate()
    const weekDay = weekDays[now.getDay()]
    this.setData({
      today: `${month}月${day}日 ${weekDay}`
    })
  },

  /** 加载首页数据 */
  loadData() {
    this.setData({ isLoading: true })
    Promise.all([
      this.loadStudyStats(),
      this.loadRecentWords()
    ]).finally(() => {
      this.setData({ isLoading: false })
    })
  },

  /** 加载学习统计数据 */
  loadStudyStats() {
    return studyRecordAPI.getStudyStats().then(res => {
      const todayWords = res.todayWords || 0
      const targetWords = res.targetWords || 50
      const progress = Math.min(Math.round((todayWords / targetWords) * 100), 100)
      this.setData({
        todayWords,
        totalWords: res.totalWords || 0,
        streak: res.studyDays || 0,
        targetWords,
        progress
      })
    }).catch(() => {
      this.setData({
        todayWords: 0,
        totalWords: 0,
        streak: 0,
        progress: 0
      })
    })
  },

  /** 加载最近学习的单词 */
  loadRecentWords() {
    const userInfo = wx.getStorageSync('userInfo')
    const userId = userInfo?.id || 1
    
    return vocabAPI.getVocabList(userId).then(res => {
      const recent = (res || []).slice(0, 3).map(item => ({
        id: item.vocabId,
        word: item.word.wordText,
        meaning: item.word.definition,
        mastered: item.mastered
      }))
      this.setData({
        recentWords: recent
      })
    }).catch(() => {
      this.setData({ recentWords: [] })
    })
  },

  /** 处理快捷操作点击 */
  goToAction(e) {
    const action = e.currentTarget.dataset.action
    
    if (action === 'createBook') {
      this.createBook()
    }
  },

  /** 显示创建单词书弹窗 */
  createBook() {
    console.log('createBook called')
    this.setData({
      showModal: true,
      bookForm: {
        name: '',
        description: ''
      }
    })
    console.log('showModal set to true')
  },

  /** 关闭弹窗 */
  closeModal() {
    this.setData({
      showModal: false
    })
  },

  /** 阻止事件冒泡 */
  preventBubble() {
    // 阻止事件冒泡
  },

  onNameInput(e) {
    this.setData({
      'bookForm.name': e.detail.value
    })
  },

  onDescInput(e) {
    this.setData({
      'bookForm.description': e.detail.value
    })
  },

  /** 提交创建单词书 */
  async submitCreate() {
    const { name, description } = this.data.bookForm
    
    console.log('submitCreate called:', { name, description })
    
    if (!name.trim()) {
      wx.showToast({ title: '请输入名称', icon: 'none' })
      return
    }

    try {
      const userInfo = wx.getStorageSync('userInfo')
      const userId = userInfo?.id || 1
      console.log('Calling createBook:', { userId, name: name.trim(), description: description.trim() })
      const result = await vocabAPI.createBook(userId, name.trim(), description.trim())
      console.log('createBook result:', result)
      wx.showToast({ title: '创建成功', icon: 'success' })
      this.closeModal()
    } catch (err) {
      console.error('createBook error:', err)
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  },

  /** 跳转单词详情页 */
  goToWordDetail(e) {
    const word = e.currentTarget.dataset.word
    wx.navigateTo({
      url: `/pages/word-detail/word-detail?id=${word.id}`
    })
  },

  /** 查看全部单词 */
  viewAllWords() {
    wx.switchTab({
      url: '/pages/book/book'
    })
  },

  onPullDownRefresh() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.loadData().finally(() => {
        wx.stopPullDownRefresh()
      })
    } else {
      wx.stopPullDownRefresh()
    }
  }
})
