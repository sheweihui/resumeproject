const { userAPI } = require('./utils/api')

App({
  onLaunch() {
    this.autoLogin()
  },

  async autoLogin() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')

    if (token && userInfo?.id) {
      try {
        await userAPI.validateToken(token)
        console.log('自动登录成功')
      } catch (err) {
        console.log('token 已过期，需要重新登录')
        wx.removeStorageSync('token')
        wx.removeStorageSync('userInfo')
      }
    }
  },

  globalData: {
    userInfo: null
  }
})
