const { storeAPI } = require('../../utils/api.js')

/** 商店页 - 积分商店、签到、秒杀活动 */
Page({
  data: {
    books: [],
    filteredBooks: [],
    pointsBalance: {
      balance: 0,
      totalEarned: 0,
      totalSpent: 0
    },
    searchKeyword: '',
    activeCategory: 'all',
    categories: [
      { id: 'all', name: '全部' },
      { id: 'cet4', name: '四级' },
      { id: 'cet6', name: '六级' },
      { id: 'ielts', name: '雅思' },
      { id: 'toefl', name: '托福' },
      { id: 'business', name: '商务' },
      { id: 'daily', name: '日常' }
    ],
    sortBy: 'recommend',
    sortOptions: [
      { id: 'recommend', name: '推荐' },
      { id: 'hot', name: '热门' },
      { id: 'new', name: '新品' },
      { id: 'price', name: '价格' }
    ],
    showDetailModal: false,
    showOrderModal: false,
    showFlashSaleModal: false,
    selectedBook: null,
    orderBook: null,
    checkinInfo: {
      checkedIn: false,
      continuousDays: 0
    },
    loading: false,
    flashSaleList: [],
    flashSaleCountdown: {
      hours: '00',
      minutes: '00',
      seconds: '00'
    },
    currentFlashSale: null,
    countdownTimer: null
  },

  onLoad() {
    this.loadData()
  },

  onUnload() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
    }
  },

  onHide() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
    }
  },

  onShow() {
    if (this.data.flashSaleList.length > 0) {
      this.startCountdown()
    }
  },

  /** 加载商店首页数据（积分、书籍、秒杀） */
  async loadData() {
    await Promise.all([
      this.loadPointsBalance(),
      this.loadBooks(),
      this.loadFlashSaleList()
    ])
  },

  /** 更新秒杀活动状态（未开始/进行中/已结束/售罄） */
  updateFlashSaleStatus(flashSaleList) {
    return flashSaleList.map(item => {
      const status = this.getFlashSaleStatus(item)
      return { ...item, status: status }
    })
  },

  /** 加载秒杀活动列表 */
  async loadFlashSaleList() {
    try {
      const res = await storeAPI.getFlashSaleList()
      if (res.code === 200) {
        let flashSaleList = res.data || []
        flashSaleList = this.updateFlashSaleStatus(flashSaleList)
        this.setData({ flashSaleList })
        if (flashSaleList.length > 0) {
          this.startCountdown()
        }
      }
    } catch (err) {
      console.error('loadFlashSaleList error:', err)
      const mockFlashSaleList = [
        {
          id: 1,
          bookId: 1,
          bookName: '四级核心词汇',
          coverImage: '',
          originalPrice: 500,
          flashPrice: 199,
          stock: 50,
          soldCount: 32,
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
          status: 'ongoing',
          description: '精选四级高频词汇，助你轻松过级',
          wordCount: 2000,
          difficulty: 2
        },
        {
          id: 2,
          bookId: 2,
          bookName: '雅思高频词汇',
          coverImage: '',
          originalPrice: 800,
          flashPrice: 299,
          stock: 30,
          soldCount: 15,
          startTime: new Date(Date.now() + 1 * 60 * 60 * 1000).toISOString(),
          endTime: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(),
          status: 'upcoming',
          description: '雅思考试必备词汇精选',
          wordCount: 3000,
          difficulty: 3
        }
      ]
      this.setData({ flashSaleList: mockFlashSaleList })
      if (mockFlashSaleList.length > 0) {
        this.startCountdown()
      }
    }
  },

  /** 启动秒杀倒计时 */
  startCountdown() {
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
    }

    const timer = setInterval(() => {
      this.updateCountdown()
    }, 1000)

    this.setData({ countdownTimer: timer })
    this.updateCountdown()
  },

  /** 更新倒计时显示 */
  updateCountdown() {
    const { flashSaleList } = this.data
    if (!flashSaleList || flashSaleList.length === 0) return

    const now = Date.now()
    let nearestEnd = null
    let nearestItem = null

    flashSaleList.forEach(item => {
      const status = this.getFlashSaleStatus(item)
      if (status === 'ongoing') {
        const endTime = new Date(item.endTime).getTime()
        if (!nearestEnd || endTime < nearestEnd) {
          nearestEnd = endTime
          nearestItem = item
        }
      }
    })

    if (!nearestItem) {
      flashSaleList.forEach(item => {
        const status = this.getFlashSaleStatus(item)
        if (status === 'upcoming') {
          const startTime = new Date(item.startTime).getTime()
          if (!nearestEnd || startTime < nearestEnd) {
            nearestEnd = startTime
            nearestItem = item
          }
        }
      })
    }

    if (!nearestEnd) {
      this.setData({
        flashSaleCountdown: { hours: '00', minutes: '00', seconds: '00' }
      })
      return
    }

    const distance = nearestEnd - now

    if (distance <= 0) {
      this.loadFlashSaleList()
      return
    }

    const hours = Math.floor(distance / (1000 * 60 * 60))
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((distance % (1000 * 60)) / 1000)

    this.setData({
      flashSaleCountdown: {
        hours: hours.toString().padStart(2, '0'),
        minutes: minutes.toString().padStart(2, '0'),
        seconds: seconds.toString().padStart(2, '0')
      }
    })
  },

  /** 计算秒杀活动状态 */
  getFlashSaleStatus(item) {
    const now = Date.now()
    
    const startDate = new Date(item.startTime)
    const endDate = new Date(item.endTime)
    
    const startTime = startDate.getTime()
    const endTime = endDate.getTime()
    
    console.log('=== 秒杀状态计算 ===')
    console.log('当前时间:', new Date(now).toISOString())
    console.log('开始时间:', item.startTime, '/', startTime)
    console.log('结束时间:', item.endTime, '/', endTime)
    console.log('库存:', item.stock, ', 已售:', item.soldCount)

    if (isNaN(startTime) || isNaN(endTime)) {
      console.error('日期解析失败')
      return 'ongoing'
    }

    if (now < startTime) {
      console.log('状态: upcoming')
      return 'upcoming'
    }
    if (now > endTime) {
      console.log('状态: ended')
      return 'ended'
    }
    
    const remainingStock = Math.max(0, (item.stock || 0) - (item.soldCount || 0))
    console.log('剩余库存:', remainingStock)
    
    if ((item.stock || 0) <= 0 || remainingStock <= 0) {
      console.log('状态: soldout')
      return 'soldout'
    }
    console.log('状态: ongoing')
    return 'ongoing'
  },

  /** 查看秒杀商品详情 */
  showFlashSaleDetail(e) {
    const item = e.currentTarget.dataset.item
    const status = this.getFlashSaleStatus(item)
    this.setData({
      currentFlashSale: { ...item, currentStatus: status },
      showFlashSaleModal: true
    })
  },

  /** 关闭秒杀详情弹窗 */
  closeFlashSaleModal() {
    this.setData({ showFlashSaleModal: false })
  },

  /** 执行秒杀购买 */
  async purchaseFlashSale() {
    const { currentFlashSale, pointsBalance } = this.data

    if (!currentFlashSale) return

    if (currentFlashSale.currentStatus !== 'ongoing') {
      wx.showToast({ title: '秒杀活动未开始或已结束', icon: 'none' })
      return
    }

    if (currentFlashSale.stock <= currentFlashSale.soldCount) {
      wx.showToast({ title: '商品已售罄', icon: 'none' })
      return
    }

    if (pointsBalance.balance < currentFlashSale.flashPrice) {
      wx.showToast({ title: '积分不足', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: '抢购中...' })
      const res = await storeAPI.purchaseFlashSale(currentFlashSale.id)
      wx.hideLoading()

      if (res.code === 200) {
        wx.showModal({
          title: '抢购成功',
          content: `恭喜您以${currentFlashSale.flashPrice}积分抢购成功！`,
          showCancel: false,
          success: () => {
            this.closeFlashSaleModal()
            this.loadData()
          }
        })
      } else {
        wx.showToast({ title: res.message || '抢购失败', icon: 'none' })
      }
    } catch (err) {
      wx.hideLoading()
      console.error('purchaseFlashSale error:', err)
      if (err && err.message) {
        const errorMsg = err.message.replace('秒杀失败: ', '')
        wx.showToast({ title: errorMsg || '抢购失败', icon: 'none' })
      } else {
        wx.showToast({ title: '抢购失败，请重试', icon: 'none' })
      }
    }
  },

  /** 加载用户积分余额 */
  async loadPointsBalance() {
    try {
      const res = await storeAPI.getPointsBalance()
      if (res.code === 200) {
        this.setData({
          pointsBalance: res.data
        })
      }
    } catch (err) {
      console.error('loadPointsBalance error:', err)
    }
  },

  /** 加载商店单词书列表 */
  async loadBooks() {
    try {
      this.setData({ loading: true })
      const params = {
        category: this.data.activeCategory === 'all' ? '' : this.data.activeCategory,
        sortBy: this.data.sortBy
      }
      console.log('加载书籍参数:', params)
      const res = await storeAPI.getBooks(params)
      console.log('书籍响应:', res)
      console.log('响应码:', res?.code)
      console.log('响应数据:', res?.data)
      console.log('records:', res?.data?.records)
      
      if (res && res.code === 200) {
        const books = res.data?.records || res.data || []
        console.log('最终书籍列表:', books)
        this.setData({
          books: books,
          filteredBooks: this.filterBooks(books)
        })
      }
    } catch (err) {
      wx.showToast({ title: '加载失败', icon: 'none' })
      console.error('loadBooks error:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  /** 刷新商店所有数据 */
  async refreshAll() {
    try {
      wx.showLoading({ title: '刷新中...' })
      await Promise.all([
        this.loadBooks(),
        this.loadFlashSaleList()
      ])
      wx.hideLoading()
      wx.showToast({ title: '刷新成功', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '刷新失败', icon: 'none' })
      console.error('refreshAll error:', err)
    }
  },

  /** 过滤书籍列表（按搜索关键词） */
  filterBooks(books) {
    let result = books || []
    if (this.data.searchKeyword) {
      const keyword = this.data.searchKeyword.toLowerCase()
      result = result.filter(book => 
        book.bookName && book.bookName.toLowerCase().includes(keyword) ||
        book.description && book.description.toLowerCase().includes(keyword)
      )
    }
    return result
  },

  /** 执行每日签到 */
  async checkin() {
    try {
      wx.showLoading({ title: '签到中...' })
      const res = await storeAPI.checkin()
      wx.hideLoading()
      
      console.log('签到响应:', res)
      console.log('响应码:', res.code)
      console.log('响应消息:', res.message)
      
      if (res && res.code === 200) {
        const data = res.data || {}
        const { checkedIn, pointsEarned, continuousDays, bonusPoints } = data
        
        console.log('checkedIn:', checkedIn)
        
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
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '签到失败', icon: 'none' })
      console.error('checkin error:', err)
    }
  },

  onSearchInput(e) {
    const keyword = e.detail.value
    this.setData({ searchKeyword: keyword })
    // 实时过滤书籍
    const filteredBooks = this.filterBooks(this.data.books)
    this.setData({ filteredBooks })
  },

  /** 切换分类筛选 */
  switchCategory(e) {
    const categoryId = e.currentTarget.dataset.categoryId
    this.setData({ activeCategory: categoryId })
    this.loadBooks()
  },

  /** 切换排序方式 */
  switchSort(e) {
    const sortId = e.currentTarget.dataset.sortId
    this.setData({ sortBy: sortId })
    this.loadBooks()
  },

  /** 查看书籍详情弹窗 */
  showBookDetail(e) {
    const book = e.currentTarget.dataset.book
    this.setData({
      selectedBook: book,
      showDetailModal: true
    })
  },

  /** 关闭书籍详情弹窗 */
  closeDetailModal() {
    this.setData({ showDetailModal: false })
  },

  /** 打开购买确认弹窗 */
  buyBook(e) {
    const book = e.currentTarget.dataset.book
    this.setData({
      orderBook: book,
      showOrderModal: true,
      showDetailModal: false
    })
  },

  /** 跳转单词书预览页 */
  previewBook(e) {
    const book = e.currentTarget.dataset.book
    wx.navigateTo({
      url: `/pages/book-preview/book-preview?id=${book.id}&name=${encodeURIComponent(book.bookName)}`
    })
  },

  /** 关闭订单弹窗 */
  closeOrderModal() {
    this.setData({ showOrderModal: false })
  },

  /** 提交购买订单 */
  async submitOrder() {
    const { orderBook, pointsBalance } = this.data
    
    console.log('订单信息:', orderBook)
    console.log('当前积分:', pointsBalance.balance)
    console.log('书籍价格:', orderBook.price)
    
    if (pointsBalance.balance < orderBook.price) {
      wx.showToast({ title: '积分不足', icon: 'none' })
      return
    }
    
    try {
      wx.showLoading({ title: '购买中...' })
      
      console.log('发起购买请求, bookId:', orderBook.id)
      const res = await storeAPI.purchaseBook(orderBook.id)
      console.log('购买响应:', res)
      
      wx.hideLoading()
      
      if (res.code === 200) {
        wx.showModal({
          title: '购买成功',
          content: '单词书已添加到您的书架',
          showCancel: false,
          success: () => {
            this.closeOrderModal()
            this.loadData()
          }
        })
      } else {
        wx.showToast({ title: res.message || '购买失败', icon: 'none' })
      }
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '购买失败', icon: 'none' })
      console.error('purchaseBook error:', err)
    }
  },

  /** 阻止事件冒泡 */
  preventBubble() {}
})