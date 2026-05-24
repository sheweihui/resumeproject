const { userAPI } = require('../../utils/api')

/** 注册页面 */
Page({
  data: {
    username: '',
    password: '',
    confirmPassword: '',
    nickname: '',
    showPassword: false,
    showConfirmPassword: false,
    isLoading: false
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value })
  },

  togglePassword() {
    this.setData({ showPassword: !this.data.showPassword })
  },

  toggleConfirmPassword() {
    this.setData({ showConfirmPassword: !this.data.showConfirmPassword })
  },

  /** 执行注册 */
  async register() {
    const { username, password, confirmPassword, nickname } = this.data
    
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    
    if (username.length < 3 || username.length > 20) {
      wx.showToast({ title: '用户名长度为3-20个字符', icon: 'none' })
      return
    }
    
    if (!password.trim()) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }
    
    if (password.length < 6) {
      wx.showToast({ title: '密码至少6个字符', icon: 'none' })
      return
    }
    
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次输入的密码不一致', icon: 'none' })
      return
    }

    this.setData({ isLoading: true })

    try {
      const res = await userAPI.register({
        username: username.trim(),
        password: password.trim(),
        nickname: nickname.trim() || username.trim()
      })
      
      const userData = {
        id: res.id,
        username: res.username,
        nickname: res.nickname || res.username,
        avatar: res.avatar || '',
        createdAt: res.createdAt
      }
      
      wx.setStorageSync('userInfo', userData)
      
      wx.showToast({ title: '注册成功', icon: 'success' })
      
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 1500)
    } catch (err) {
      wx.showToast({ title: err.message || '注册失败', icon: 'none' })
    } finally {
      this.setData({ isLoading: false })
    }
  },

  /** 返回登录页 */
  goToLogin() {
    wx.navigateBack()
  }
})
