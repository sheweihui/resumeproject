const { agentAPI, wordAPI } = require('../../utils/api')

Page({
  data: {
    messages: [
      {
        id: 1,
        type: 'ai',
        content: '你好！我是你的AI英语学习助手。有什么我可以帮助你的吗？比如查单词、练习发音或者测试你的词汇量。'
      }
    ],
    inputText: '',
    isLoading: false,
    conversationId: null,
    isLoggedIn: false,
    agentOnline: false,
    toView: 'bottom',
    failedMessages: {}
  },

  onLoad() {
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo?.id) {
      this.setData({ isLoggedIn: true })
    }
    this.checkAgentHealth()
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    this.setData({ isLoggedIn: !!userInfo?.id })
  },

  checkAgentHealth() {
    agentAPI.health()
      .then(res => {
        if (res.status === 'ok') {
          this.setData({ agentOnline: true })
        }
      })
      .catch(() => {
        this.setData({ agentOnline: false })
      })
  },

  scrollToBottom() {
    this.setData({ toView: 'bottom' })
  },

  sendMessage() {
    if (!this.data.inputText.trim() || this.data.isLoading) return

    const token = wx.getStorageSync('token')
    if (!token) {
      wx.showModal({
        title: '提示',
        content: '请先登录后使用AI助手',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/login/login' })
          }
        }
      })
      return
    }

    const newMessage = {
      id: Date.now(),
      type: 'user',
      content: this.data.inputText.trim()
    }

    this.setData({
      messages: [...this.data.messages, newMessage],
      inputText: '',
      isLoading: true
    }, () => {
      this.scrollToBottom()
    })

    this.callAgent(newMessage.content, newMessage.id)
  },

  async callAgent(question, messageId) {
    try {
      const userInfo = wx.getStorageSync('userInfo')
      let res

      if (this.data.agentOnline) {
        res = await agentAPI.chat(question, userInfo?.id, this.data.conversationId)

        const aiReply = {
          id: Date.now() + 1,
          type: 'ai',
          content: res.reply || '抱歉，没有收到回复'
        }

        this.setData({
          messages: [...this.data.messages, aiReply],
          isLoading: false,
          conversationId: res.conversation_id
        }, () => {
          this.scrollToBottom()
        })
      } else {
        await this.callAIFillWord(question)
      }
    } catch (err) {
      console.error('Agent 调用失败:', err)
      // 标记失败消息
      const { messages } = this.data
      const updatedMessages = messages.map(msg =>
        msg.id === messageId ? { ...msg, failed: true } : msg
      )
      this.setData({ messages: updatedMessages })
      await this.callAIFillWord(question)
    }
  },

  retryMessage(e) {
    const id = e.currentTarget.dataset.id
    const { messages } = this.data
    const failedMsg = messages.find(m => m.id === id)
    if (!failedMsg) return

    const updatedMessages = messages.map(m =>
      m.id === id ? { ...m, failed: false } : m
    )
    this.setData({
      messages: updatedMessages,
      isLoading: true
    }, () => {
      this.scrollToBottom()
    })

    this.callAgent(failedMsg.content, id)
  },

  async callAIFillWord(wordText) {
    try {
      const res = await wordAPI.aiFillWord(wordText)

      if (res && res.code === 200 && res.data && res.data.wordText) {
        const content = this.formatWordResponse(res.data)
        const aiReply = { id: Date.now() + 1, type: 'ai', content }
        this.setData({ messages: [...this.data.messages, aiReply], isLoading: false }, () => {
          this.scrollToBottom()
        })
      } else {
        this.showFallbackMessage()
      }
    } catch (err) {
      console.error('callAIFillWord error:', err)
      this.showFallbackMessage()
    }
  },

  formatWordResponse(word) {
    let content = `**${word.wordText}** ${word.phonetic || ''}\n\n`
    content += `**释义：** ${word.partOfSpeech || ''} ${word.definition || ''}\n\n`
    if (word.exampleSentence) {
      content += `**例句：** ${word.exampleSentence}\n`
    }
    if (word.exampleTranslation) {
      content += `**翻译：** ${word.exampleTranslation}\n\n`
    }
    if (word.note) {
      content += `**备注：** ${word.note}\n\n`
    }
    content += '想了解更多单词吗？直接输入单词即可查询。'
    return content
  },

  showFallbackMessage() {
    const aiReply = {
      id: Date.now() + 1,
      type: 'ai',
      content: '暂时无法连接到AI服务，请确保后端和Agent服务都已启动。你可以稍后重试。'
    }
    this.setData({ messages: [...this.data.messages, aiReply], isLoading: false }, () => {
      this.scrollToBottom()
    })
  },

  clearChat() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有对话吗？',
      success: (res) => {
        if (res.confirm) {
          if (this.data.conversationId) {
            agentAPI.clearConversation(this.data.conversationId).catch(() => {})
          }
          this.setData({
            messages: [{
              id: 1,
              type: 'ai',
              content: '你好！我是你的AI英语学习助手。有什么我可以帮助你的吗？'
            }],
            conversationId: null
          })
        }
      }
    })
  },

  quickAction(e) {
    const action = e.currentTarget.dataset.action
    this.setData({ inputText: action })
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  }
})
