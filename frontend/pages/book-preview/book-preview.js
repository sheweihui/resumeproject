const { storeAPI } = require('../../utils/api')

/** 单词书预览页（商店购买前预览） */
Page({
  data: {
    bookId: null,
    bookName: '',
    words: [],
    filteredWords: [],
    searchKeyword: '',
    isLoading: true
  },

  onLoad(options) {
    console.log('preview onLoad options:', options)
    if (options?.id && options?.name) {
      const bookId = parseInt(options.id)
      console.log('bookId:', bookId, typeof bookId)
      this.setData({
        bookId: bookId,
        bookName: decodeURIComponent(options.name)
      })
      console.log('data after set:', this.data.bookId, this.data.bookName)
      this.loadWords()
    }
  },

  /** 加载单词列表 */
  loadWords() {
    console.log('loadWords called, bookId:', this.data.bookId)
    if (!this.data.bookId) {
      console.log('bookId is empty, return')
      return
    }

    this.setData({ isLoading: true })

    console.log('calling storeAPI.getBookWords with:', this.data.bookId)
    storeAPI.getBookWords(this.data.bookId).then(res => {
      console.log('preview getBookWords result:', res)
      const words = res && res.code === 200 ? res.data : []
      this.setData({
        words: words,
        filteredWords: words,
        isLoading: false
      })
    }).catch(err => {
      console.error('loadWords error:', err)
      this.setData({ isLoading: false })
    })
  },

  onSearchInput(e) {
    const keyword = e.detail.value.toLowerCase()
    const { words } = this.data

    if (!keyword) {
      this.setData({ filteredWords: words, searchKeyword: '' })
      return
    }

    const filtered = words.filter(word =>
      word.wordText.toLowerCase().includes(keyword) ||
      (word.definition && word.definition.toLowerCase().includes(keyword))
    )

    this.setData({
      filteredWords: filtered,
      searchKeyword: keyword
    })
  },

  /** 返回上一页 */
  goBack() {
    wx.navigateBack()
  }
})