const { vocabAPI, wordAPI } = require('../../utils/api')

/** 单词书详情页 - 展示单词列表并支持增删改查 */
Page({
  data: {
    bookId: null,
    bookName: '',
    words: [],
    filteredWords: [],
    searchKeyword: '',
    showModal: false,
    showWordDetail: false,
    showEditModal: false,
    selectedWord: null,
    editWordId: null,
    aiFilled: false,
    batchMode: false,
    selectedWords: {},
    selectedCount: 0,
    wordForm: {
      wordText: '',
      phonetic: '',
      partOfSpeech: '',
      definition: '',
      exampleSentence: '',
      exampleTranslation: ''
    },
    editForm: {
      wordText: '',
      phonetic: '',
      partOfSpeech: '',
      definition: '',
      exampleSentence: '',
      exampleTranslation: ''
    }
  },

  onLoad(options) {
    if (options?.id && options?.name) {
      this.setData({
        bookId: parseInt(options.id),
        bookName: decodeURIComponent(options.name)
      })
      this.loadWords()
    }
  },

  onShow() {
    if (this.data.bookId) {
      this.loadWords()
    }
  },

  /** 加载单词书中的单词列表 */
  loadWords() {
    if (!this.data.bookId) return
    
    vocabAPI.getWordsByBook(this.data.bookId).then(res => {
      console.log('getWordsByBook result:', res)
      const words = res && res.code === 200 ? res.data : []
      console.log('words array:', words)
      this.setData({
        words: words,
        filteredWords: words
      })
    }).catch(err => {
      console.error('loadWords error:', err)
      this.setData({ words: [], filteredWords: [] })
    })
  },

  /** 返回上一页 */
  goBack() {
    wx.navigateBack()
  },

  onSearchInput(e) {
    const keyword = e.detail.value
    this.setData({ searchKeyword: keyword })
    
    if (!keyword.trim()) {
      this.setData({ filteredWords: this.data.words })
    } else {
      const filtered = this.data.words.filter(word => 
        word.wordText.toLowerCase().includes(keyword.toLowerCase()) ||
        word.definition.includes(keyword)
      )
      this.setData({ filteredWords: filtered })
    }
  },

  /** 查看单词详情 */
  showWordDetail(e) {
    const word = e.currentTarget.dataset.word
    this.setData({
      selectedWord: word,
      showWordDetail: true
    })
  },

  /** 关闭单词详情 */
  closeWordDetail() {
    this.setData({ showWordDetail: false })
  },

  /** 显示添加单词弹窗 */
  showAddWordModal() {
    this.setData({
      showModal: true,
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
  closeModal() {
    this.setData({ showModal: false })
  },

  preventBubble() {},

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
    const { bookId, wordForm, aiFilled } = this.data

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

      console.log('添加单词到单词书请求数据:', { bookId, ...wordData })

      await vocabAPI.addWordToBook(bookId, wordData)

      wx.hideLoading()
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.closeModal()
      this.loadWords()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '添加失败', icon: 'none' })
      console.error('submitAddWord error:', err)
    }
  },

  /** 打开编辑单词弹窗 */
  showEditWordModal(e) {
    const word = e.currentTarget.dataset.word
    this.setData({
      editWordId: word.id,
      showEditModal: true,
      editForm: {
        wordText: word.wordText || '',
        phonetic: word.phonetic || '',
        partOfSpeech: word.partOfSpeech || '',
        definition: word.definition || '',
        exampleSentence: word.exampleSentence || '',
        exampleTranslation: word.exampleTranslation || ''
      }
    })
  },

  /** 关闭编辑弹窗 */
  closeEditModal() {
    this.setData({ showEditModal: false })
  },

  handleEditInput(e) {
    const field = e.currentTarget.dataset.field
    const value = e.detail.value
    this.setData({
      [`editForm.${field}`]: value
    })
  },

  /** 提交修改单词 */
  async submitEditWord() {
    const { editWordId, editForm } = this.data

    if (!editWordId) {
      wx.showToast({ title: '单词ID不存在', icon: 'none' })
      return
    }

    if (!editForm.wordText.trim()) {
      wx.showToast({ title: '请输入单词', icon: 'none' })
      return
    }

    if (!editForm.definition.trim()) {
      wx.showToast({ title: '请输入释义', icon: 'none' })
      return
    }

    try {
      wx.showLoading({ title: '保存中...' })

      await wordAPI.updateWord(editWordId, editForm)

      wx.hideLoading()
      wx.showToast({ title: '修改成功', icon: 'success' })
      this.closeEditModal()
      this.loadWords()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '修改失败', icon: 'none' })
      console.error('submitEditWord error:', err)
    }
  },

  /** 删除单词（带确认弹窗） */
  deleteWord(e) {
    const word = e.currentTarget.dataset.word
    const { bookId } = this.data
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除单词"${word.wordText}"吗？`,
      confirmColor: '#f5576c',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '删除中...' })
            
            await vocabAPI.removeWordFromBook(bookId, word.id)
            
            wx.hideLoading()
            wx.showToast({ title: '删除成功', icon: 'success' })
            this.loadWords()
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '删除失败', icon: 'none' })
            console.error('deleteWord error:', err)
          }
        }
      }
    })
  },

  /** 切换批量管理模式 */
  toggleBatchMode() {
    const { batchMode } = this.data
    this.setData({
      batchMode: !batchMode,
      selectedWords: {},
      selectedCount: 0
    })
  },

  /** 切换单词选中状态 */
  toggleWordSelection(e) {
    const word = e.currentTarget.dataset.word
    const wordId = word.id ? word.id : e.currentTarget.dataset.index
    const { selectedWords, selectedCount } = this.data
    
    const newSelected = { ...selectedWords }
    if (newSelected[wordId]) {
      delete newSelected[wordId]
    } else {
      newSelected[wordId] = true
    }
    
    this.setData({
      selectedWords: newSelected,
      selectedCount: Object.keys(newSelected).length
    })
  },

  /** 全选/取消全选 */
  toggleSelectAll() {
    const { filteredWords, selectedCount } = this.data
    
    if (selectedCount === filteredWords.length && filteredWords.length > 0) {
      this.setData({
        selectedWords: {},
        selectedCount: 0
      })
    } else {
      const newSelected = {}
      filteredWords.forEach((word, index) => {
        const wordId = word.id ? word.id : index
        newSelected[wordId] = true
      })
      this.setData({
        selectedWords: newSelected,
        selectedCount: filteredWords.length
      })
    }
  },

  /** 批量删除选中单词 */
  batchDeleteWords() {
    const { selectedWords, selectedCount, bookId } = this.data
    
    if (selectedCount === 0) {
      wx.showToast({ title: '请先选择要删除的单词', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedCount} 个单词吗？`,
      confirmColor: '#f5576c',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '删除中...' })
            
            const wordIds = Object.keys(selectedWords).map(id => parseInt(id))
            
            for (const wordId of wordIds) {
              await vocabAPI.removeWordFromBook(bookId, wordId)
            }
            
            wx.hideLoading()
            wx.showToast({ title: '批量删除成功', icon: 'success' })
            this.setData({
              batchMode: false,
              selectedWords: {},
              selectedCount: 0
            })
            this.loadWords()
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '批量删除失败', icon: 'none' })
            console.error('batchDeleteWords error:', err)
          }
        }
      }
    })
  }
})