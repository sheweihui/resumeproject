const { userAPI, vocabAPI, studyRecordAPI, storeAPI } = require('../../utils/api')

/** 个人中心页 */
Page({
  data: {
    userInfo: {
      id: null,
      username: '',
      nickname: '未登录',
      avatar: '',
      level: 'Lv.1 新手',
      createdDays: 0
    },
    stats: [
      { label: '今日学习', value: '0', unit: '词' },
      { label: '本周学习', value: '0', unit: '词' },
      { label: '累计学习', value: '0', unit: '词' },
      { label: '学习天数', value: '0', unit: '天' }
    ],
    progress: {
      mastered: 0,
      total: 0,
      percent: 0
    },
    pointsBalance: {
      balance: 0,
      totalEarned: 0,
      totalSpent: 0
    },
    checkinInfo: {
      checkedIn: false,
      continuousDays: 0
    },
    menuItems: [
      { icon: '📚', label: '学习计划', path: '/pages/plan/plan', badge: '' },
      { icon: '🏆', label: '成就中心', path: '/pages/achievement/achievement', badge: '' },
      { icon: '💾', label: '数据导出', path: '/pages/export/export', badge: '' },
      { icon: '⚙️', label: '设置', path: '/pages/settings/settings', badge: '' },
      { icon: '💬', label: '意见反馈', path: '/pages/feedback/feedback', badge: '' }
    ],
    isLoggedIn: false,
    isLoading: true
  },

  onLoad() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.setData({
        isLoggedIn: true,
        userInfo: {
          ...this.data.userInfo,
          ...userInfo
        }
      })
      this.loadUserData()
    } else {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.loadUserData()
    }
  },

  /** 加载用户数据 */
  loadUserData() {
    this.setData({ isLoading: true })
    Promise.all([
      this.loadStudyStats(),
      this.loadVocabularyProgress(),
      this.loadPointsBalance()
    ]).finally(() => {
      this.setData({ isLoading: false })
    })
  },

  /** 加载积分余额 */
  loadPointsBalance() {
    return storeAPI.getPointsBalance().then(res => {
      if (res && res.code === 200) {
        this.setData({
          pointsBalance: res.data
        })
      }
    }).catch(() => {})
  },

  /** 执行每日签到 */
  checkin() {
    wx.showLoading({ title: '签到中...' })
    storeAPI.checkin().then(res => {
      wx.hideLoading()
      console.log('签到响应:', res)
      
      if (res && res.code === 200) {
        const data = res.data || {}
        const { checkedIn, pointsEarned, continuousDays, bonusPoints } = data
        
        if (checkedIn) {
          let message = `签到成功！获得${pointsEarned}积分`
          if (bonusPoints > 0) {
            message += `，连续签到${continuousDays}天额外奖励${bonusPoints}积分`
          }
          wx.showToast({ title: message, icon: 'success', duration: 2000 })
          this.loadPointsBalance()
          this.setData({
            checkinInfo: {
              checkedIn: true,
              continuousDays: continuousDays
            }
          })
        } else {
          wx.showToast({ title: res.message || '今日已签到', icon: 'none', duration: 2000 })
        }
      } else {
        wx.showToast({ title: res?.message || '签到失败', icon: 'none' })
      }
    }).catch(err => {
      wx.hideLoading()
      wx.showToast({ title: '签到失败', icon: 'none' })
      console.error('checkin error:', err)
    })
  },

  /** 根据单词量计算用户等级 */
  calculateLevel(totalWords) {
    if (totalWords >= 1000) return 'Lv.5 词汇大师'
    if (totalWords >= 500) return 'Lv.4 单词达人'
    if (totalWords >= 200) return 'Lv.3 学习能手'
    if (totalWords >= 50) return 'Lv.2 进阶学习'
    return 'Lv.1 新手'
  },

  /** 加载学习统计数据 */
  loadStudyStats() {
    return studyRecordAPI.getStudyStats().then(res => {
      const level = this.calculateLevel(res.totalWords || 0)
      const userInfo = wx.getStorageSync('userInfo')
      const updatedUserInfo = {
        ...userInfo,
        level: level
      }
      
      this.setData({
        stats: [
          { label: '今日学习', value: res.todayWords || '0', unit: '词' },
          { label: '本周学习', value: res.weekWords || '0', unit: '词' },
          { label: '累计学习', value: res.totalWords || '0', unit: '词' },
          { label: '学习天数', value: res.studyDays || '0', unit: '天' }
        ],
        'userInfo.level': level
      })
      
      wx.setStorageSync('userInfo', updatedUserInfo)
    }).catch(() => {})
  },

  /** 加载词汇掌握进度 */
  loadVocabularyProgress() {
    const userInfo = wx.getStorageSync('userInfo')
    const userId = userInfo?.id || 1
    
    return vocabAPI.getVocabList(userId).then(res => {
      const list = res || []
      const mastered = list.filter(item => item.mastered === 1).length
      const total = list.length
      const percent = total > 0 ? Math.round((mastered / total) * 100) : 0
      this.setData({
        progress: { mastered, total, percent }
      })
    }).catch(() => {})
  },

  /** 跳转个人资料页 */
  goToProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' })
  },

  /** 跳转菜单功能页 */
  goToMenuItem(e) {
    const item = e.currentTarget.dataset.item
    if (item.path) {
      wx.navigateTo({ url: item.path })
    }
  },

  /** 退出登录（带确认弹窗） */
  async logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: async (res) => {
        if (res.confirm) {
          const token = wx.getStorageSync('token')
          try {
            await userAPI.logout(token)
          } catch (err) {
            console.log('logout api failed:', err)
          }
          
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          
          wx.showToast({ title: '退出成功', icon: 'success' })
          
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/login/login' })
          }, 1500)
        }
      }
    })
  },

  onPullDownRefresh() {
    if (this.data.isLoggedIn) {
      this.loadUserData().finally(() => {
        wx.stopPullDownRefresh()
      })
    } else {
      wx.stopPullDownRefresh()
    }
  }
})
