const { vocabAPI, wordAPI } = require('../../utils/api')

/** 单词书列表页 */
Page({
  data: {
    books: [],
    isLoading: true,
    showAddModal: false,
    showCreateBookModal: false,
    showEditBookModal: false,
    selectedBookId: null,
    aiFilled: false,
    newBookName: '',
    newBookDesc: '',
    editBookId: null,
    editBookName: '',
    editBookDesc: '',
    wordForm: {
      wordText: '',
      phonetic: '',
      partOfSpeech: '',
      definition: '',
      exampleSentence: '',
      exampleTranslation: ''
    }
  },

  onLoad() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      // 测试数据
      const testBooks = [
        { id: 9, userId: 1, bookName: '英语四级核心词汇', description: '大学英语', coverImage: '', wordCount: 50, isPublic: 0, createdAt: '2026-05-09T22:01:24', updatedAt: '2026-05-10T18:06:45' },
        { id: 8, userId: 1, bookName: '六级', description: '六级单词备考书', coverImage: '', wordCount: 50, isPublic: 0, createdAt: '2026-05-09T21:55:59', updatedAt: '2026-05-09T22:14:20' },
        { id: 7, userId: 1, bookName: 'snake', description: '第五本单词书', coverImage: '', wordCount: 100, isPublic: 0, createdAt: '2026-05-09T18:24:06', updatedAt: '2026-05-09T22:14:20' }
      ]
      this.setData({ books: testBooks })
      console.log('测试数据已设置:', this.data.books)
      
      // 然后加载真实数据
      this.loadBooks()
    } else {
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.loadBooks()
    }
  },

  /** 加载用户单词书列表 */
  loadBooks() {
    this.setData({ isLoading: true })
    const userInfo = wx.getStorageSync('userInfo')
    const userId = userInfo?.id || 1
    console.log('userId:', userId)
    console.log('token:', wx.getStorageSync('token'))

    vocabAPI.getBookList(userId).then(res => {
      console.log('getBookList result:', res)
      console.log('res.code:', res?.code)
      console.log('res.data:', res?.data)
      const books = res && res.code === 200 ? res.data : []
      console.log('books array:', books)
      console.log('books length:', books.length)
      this.setData({
        books: books
      }, () => {
        // 数据设置完成后的回调
        console.log('数据设置完成，当前books:', this.data.books)
        console.log('当前books长度:', this.data.books.length)
      })
    }).catch(err => {
      console.error('loadBooks error:', err)
      this.setData({ books: [] })
    }).finally(() => {
      this.setData({ isLoading: false })
    })
  },

  /** 跳转单词书详情页 */
  goToBookDetail(e) {
    const book = e.currentTarget.dataset.book
    wx.navigateTo({
      url: `/pages/book-detail/book-detail?id=${book.id}&name=${encodeURIComponent(book.bookName)}`
    })
  },

  /** 格式化日期为 M/d 显示 */
  formatDate(dateStr) {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}/${day}`
  },

  onPullDownRefresh() {
    this.loadBooks().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  /** 显示添加单词弹窗 */
  showAddWordModal() {
    if (this.data.books.length === 0) {
      wx.showToast({
        title: '请先创建单词书',
        icon: 'none'
      })
      return
    }
    this.setData({
      showAddModal: true,
      selectedBookId: null,
      aiFilled: false,
      wordForm: {
        wordText: '',
        phonetic: '',
        partOfSpeech: '',
        definition: '',
        exampleSentence: '',
        exampleTranslation: ''
      }
    })
  },

  /** 关闭添加单词弹窗 */
  closeAddModal() {
    this.setData({ showAddModal: false })
  },

  preventBubble() {},
  
  doNothing() {},

  /** 选择目标单词书 */
  selectBook(e) {
    const bookId = e.currentTarget.dataset.bookId
    this.setData({ selectedBookId: bookId })
  },

  handleInput(e) {
    const field = e.currentTarget.dataset.field
    const value = e.detail.value
    this.setData({
      [`wordForm.${field}`]: value
    })
  },

  /** AI 自动填充单词信息 */
  async aiFillWord() {
    const { wordText } = this.data.wordForm

    if (!wordText.trim()) {
      wx.showToast({ title: '请先输入单词', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: 'AI分析中...' })

      const result = await wordAPI.aiFillWord(wordText)
      console.log('AI填充响应:', JSON.stringify(result))

      if (result && result.code === 200 && result.data) {
        const wordData = result.data
        this.setData({
          wordForm: {
            wordText: wordData.wordText || wordText,
            phonetic: wordData.phonetic || '',
            partOfSpeech: wordData.partOfSpeech || '',
            definition: wordData.definition || '',
            exampleSentence: wordData.exampleSentence || '',
            exampleTranslation: wordData.exampleTranslation || ''
          },
          aiFilled: true
        })
        wx.showToast({ title: 'AI填充成功', icon: 'success' })
      } else {
        wx.showToast({ title: result?.message || '填充失败', icon: 'none' })
      }

      wx.hideLoading()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: 'AI填充失败', icon: 'none' })
      console.error('aiFillWord error:', err)
    }
  },

  /** 提交添加单词 */
  async submitAddWord() {
    const { selectedBookId, wordForm, aiFilled } = this.data

    if (!selectedBookId) {
      wx.showToast({ title: '请选择单词书', icon: 'none' })
      return
    }

    if (!wordForm.wordText.trim()) {
      wx.showToast({ title: '请输入单词', icon: 'none' })
      return
    }

    if (!wordForm.definition.trim()) {
      wx.showToast({ title: '请输入释义', icon: 'none' })
      return
    }

    if (!aiFilled) {
      wx.showToast({ title: '请先使用AI代填', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: '添加中...' })

      const wordData = {
        wordText: wordForm.wordText,
        phonetic: wordForm.phonetic,
        partOfSpeech: wordForm.partOfSpeech,
        definition: wordForm.definition,
        exampleSentence: wordForm.exampleSentence,
        exampleTranslation: wordForm.exampleTranslation
      }

      console.log('添加单词到单词书请求数据:', { bookId: selectedBookId, ...wordData })

      await vocabAPI.addWordToBook(selectedBookId, wordData)

      wx.hideLoading()
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.closeAddModal()
      this.loadBooks()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '添加失败', icon: 'none' })
      console.error('submitAddWord error:', err)
    }
  },

  /** 显示创建单词书弹窗 */
  showCreateBookModal() {
    this.setData({
      showCreateBookModal: true,
      newBookName: '',
      newBookDesc: ''
    })
  },

  /** 关闭创建单词书弹窗 */
  closeCreateBookModal() {
    this.setData({ showCreateBookModal: false })
  },

  onBookNameInput(e) {
    this.setData({ newBookName: e.detail.value })
  },

  onBookDescInput(e) {
    this.setData({ newBookDesc: e.detail.value })
  },

  /** 执行创建单词书 */
  async createBook() {
    const { newBookName, newBookDesc } = this.data
    
    if (!newBookName.trim()) {
      wx.showToast({ title: '请输入单词书名称', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: '创建中...' })
      
      const userInfo = wx.getStorageSync('userInfo')
      const userId = userInfo?.id || 1
      
      await vocabAPI.createBook(userId, newBookName, newBookDesc)
      
      wx.hideLoading()
      wx.showToast({ title: '创建成功', icon: 'success' })
      this.closeCreateBookModal()
      this.loadBooks()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '创建失败', icon: 'none' })
      console.error('createBook error:', err)
    }
  },

  /** 打开编辑单词书弹窗 */
  editBookTap(e) {
    console.log('=== editBookTap 被调用 ===')
    const dataset = e.currentTarget.dataset
    console.log('dataset:', dataset)
    console.log('bookid类型:', typeof dataset.bookid)
    
    this.setData({
      showEditBookModal: true,
      editBookId: parseInt(dataset.bookid) || dataset.bookid,
      editBookName: dataset.bookname,
      editBookDesc: dataset.desc || ''
    })
    console.log('已打开编辑模态框，editBookId:', this.data.editBookId)
  },

  /** 关闭编辑弹窗 */
  closeEditModal() {
    this.setData({ showEditBookModal: false })
  },

  editNameInput(e) {
    this.setData({ editBookName: e.detail.value })
  },

  editDescInput(e) {
    this.setData({ editBookDesc: e.detail.value })
  },

  /** 提交修改单词书 */
  confirmEditBook() {
    console.log('=== 开始修改单词书 ===')
    const { editBookId, editBookName, editBookDesc } = this.data
    console.log('参数:', { editBookId, editBookName, editBookDesc })
    
    if (!editBookName.trim()) {
      wx.showToast({ title: '请输入名称', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存中...' })
    
    const token = wx.getStorageSync('token')
    console.log('token:', token ? '存在' : '不存在')
    
    const requestData = {
      bookName: editBookName,
      description: editBookDesc
    }
    console.log('请求数据:', requestData)
    console.log('请求URL:', `http://localhost:8080/api/vocabulary-book/${editBookId}`)
    
    wx.request({
      url: `http://localhost:8080/api/vocabulary-book/${editBookId}`,
      method: 'PUT',
      data: requestData,
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        console.log('修改请求响应状态:', res.statusCode)
        console.log('修改请求响应数据:', res.data)
        wx.hideLoading()
        if (res.statusCode === 200) {
          if (res.data && res.data.code === 200) {
            wx.showToast({ title: '修改成功', icon: 'success' })
            this.closeEditModal()
            this.loadBooks()
          } else {
            wx.showToast({ title: res.data?.message || '修改失败', icon: 'none' })
          }
        } else {
          wx.showToast({ title: `HTTP错误: ${res.statusCode}`, icon: 'none' })
        }
      },
      fail: (err) => {
        console.error('修改请求失败:', err)
        wx.hideLoading()
        wx.showToast({ title: '网络请求失败', icon: 'none' })
      }
    })
  },

  /** 删除单词书（带确认弹窗） */
  deleteBookTap(e) {
    console.log('=== 触发删除按钮 ===')
    const dataset = e.currentTarget.dataset
    console.log('dataset:', dataset)
    
    wx.showModal({
      title: '删除单词书',
      content: `确定删除「${dataset.bookname}」？`,
      confirmText: '删除',
      confirmColor: '#f5576c',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' })
          
          const token = wx.getStorageSync('token')
          
          console.log('删除请求URL:', `http://localhost:8080/api/vocabulary-book/${dataset.bookid}`)
          
          wx.request({
            url: `http://localhost:8080/api/vocabulary-book/${dataset.bookid}`,
            method: 'DELETE',
            header: {
              'Authorization': `Bearer ${token}`
            },
            success: (res) => {
              console.log('删除请求响应状态:', res.statusCode)
              console.log('删除请求响应数据:', res.data)
              wx.hideLoading()
              if (res.statusCode === 200) {
                if (res.data && res.data.code === 200) {
                  wx.showToast({ title: '删除成功', icon: 'success' })
                  this.loadBooks()
                } else {
                  wx.showToast({ title: res.data?.message || '删除失败', icon: 'none' })
                }
              } else {
                wx.showToast({ title: `HTTP错误: ${res.statusCode}`, icon: 'none' })
              }
            },
            fail: (err) => {
              console.error('删除请求失败:', err)
              wx.hideLoading()
              wx.showToast({ title: '网络请求失败', icon: 'none' })
            }
          })
        }
      }
    })
  }
})