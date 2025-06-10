/**
 * Chat Component
 * Handles the chat interface and message exchange
 */
import authService from '../services/authService.js';
import chatService from '../services/chatService.js';
import ModalComponent from './ModalComponent.js';

export default class ChatComponent {
  constructor(appContainer, onLogout) {
    this.appContainer = appContainer;
    this.onLogout = onLogout;
    this.messages = [];
    this.isTyping = false;
    this.modal = new ModalComponent();
    this.render();
    this.attachEventListeners();
  }

  /**
   * Render the chat component
   */
  render() {
    const user = authService.getCurrentUser();
    const session = chatService.getCurrentSession();
    const userName = user?.name || 'User';
    
    this.appContainer.innerHTML = `
      <div class="chat-container">
        <div class="chat-header">
          <div class="user-info">
            <div class="user-avatar">${userName.charAt(0).toUpperCase()}</div>
            <span>${userName}</span>
          </div>
          <div class="chat-header-actions">
            <button class="delete-chat-button" id="delete-chat-button" title="Xóa cuộc trò chuyện">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"></path>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            </button>
            <button class="logout-button" id="logout-button">Đăng xuất</button>
          </div>
        </div>
        <div class="chat-messages" id="chat-messages">
          <!-- Messages will be added here -->
          <div class="message bot">
            <div class="message-header">
              <span class="message-sender">Bot</span>
            </div>
            <div class="message-content">
              Xin chào ${userName}! Tôi có thể giúp gì cho bạn?
            </div>
          </div>
          <div class="typing-indicator" id="typing-indicator">
            <div class="message-content">
              <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="chat-input">
          <input type="text" id="message-input" placeholder="Nhập tin nhắn...">
          <button id="send-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    `;

    // Store references to DOM elements
    this.chatMessages = document.getElementById('chat-messages');
    this.messageInput = document.getElementById('message-input');
    this.sendButton = document.getElementById('send-button');
    this.typingIndicator = document.getElementById('typing-indicator');
    
    // Load previous messages if session exists
    if (session) {
      this.loadSessionMessages(session.id);
    }
  }

  /**
   * Load messages for a specific session
   */
  async loadSessionMessages(sessionId) {
    try {
      console.log('Loading messages for session:', sessionId);
      const messages = await chatService.getSessionMessages(sessionId);
      console.log('Received messages:', messages);
      this.messages = messages;
      
      // Clear all existing messages including the welcome message
      while (this.chatMessages.firstChild) {
        if (this.chatMessages.firstChild === this.typingIndicator) {
          break;
        }
        this.chatMessages.removeChild(this.chatMessages.firstChild);
      }
      
      // If no messages, add a welcome message
      if (messages.length === 0) {
        const user = authService.getCurrentUser();
        const userName = user?.name || 'User';
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'message bot';
        welcomeMessage.innerHTML = `
          <div class="message-header">
            <span class="message-sender">Bot</span>
          </div>
          <div class="message-content">
            Xin chào ${userName}! Tôi có thể giúp gì cho bạn?
          </div>
        `;
        this.chatMessages.insertBefore(welcomeMessage, this.typingIndicator);
      } else {
        // Add messages to the chat
        messages.forEach(message => {
          this.addMessage(message.message, message.sender === 'user');
        });
      }
      
      // Scroll to bottom
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    } catch (error) {
      console.error('Error loading messages:', error);
      this.addMessage('Failed to load previous messages', false);
    }
  }

  /**
   * Add a message to the chat
   */
  addMessage(content, isUser = false) {
    const user = authService.getCurrentUser();
    const userName = user?.name || 'User';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    
    // Add sender name and content
    messageDiv.innerHTML = `
      <div class="message-header">
        <span class="message-sender">${isUser ? userName : 'Bot'}</span>
      </div>
      <div class="message-content">
        ${content}
      </div>
    `;
    
    // Insert before the typing indicator
    this.chatMessages.insertBefore(messageDiv, this.typingIndicator);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  /**
   * Send a message
   */
  async sendMessage() {
    const message = this.messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    this.addMessage(message, true);
    this.messageInput.value = '';

    // Show typing indicator
    this.isTyping = true;
    this.typingIndicator.classList.add('active');
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

    try {
      const response = await chatService.sendMessage(message);

      // Hide typing indicator
      this.isTyping = false;
      this.typingIndicator.classList.remove('active');

      // Add bot response to chat
      if (response.reply) {
        this.addMessage(response.reply.message, false);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      this.isTyping = false;
      this.typingIndicator.classList.remove('active');
      this.addMessage('Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau.', false);
    }
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Send message on button click
    this.sendButton.addEventListener('click', () => this.sendMessage());
    
    // Send message on Enter key
    this.messageInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.sendMessage();
      }
    });
    
    // Logout button
    const logoutButton = document.getElementById('logout-button');
    logoutButton.addEventListener('click', () => {
      if (this.onLogout) {
        this.onLogout();
      }
    });
    
    // Delete chat button
    const deleteButton = document.getElementById('delete-chat-button');
    if (deleteButton) {
      deleteButton.addEventListener('click', () => this.confirmDeleteChat());
    }
    
    // Focus input on load
    this.messageInput.focus();
  }
  
  /**
   * Show confirmation modal before deleting the current chat
   */
  confirmDeleteChat() {
    const currentSession = chatService.getCurrentSession();
    if (!currentSession) {
      alert('Không có cuộc trò chuyện nào để xóa.');
      return;
    }
    
    this.modal.show(
      'Xóa cuộc trò chuyện', 
      'Bạn có chắc chắn muốn xóa cuộc trò chuyện này? Hành động này không thể hoàn tác.',
      () => this.deleteCurrentChat()
    );
  }
  
  /**
   * Delete the current chat session
   */
  async deleteCurrentChat() {
    try {
      const currentSession = chatService.getCurrentSession();
      if (!currentSession) return;
      
      await chatService.deleteSession(currentSession.id);
      
      // Create a new session
      const newSession = await chatService.createSession();
      
      // Update URL to the new session
      history.replaceState({sessionId: newSession.id}, '', `/chat/${newSession.id}`);
      
      // Reload the chat component
      this.messages = [];
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error('Error deleting chat session:', error);
      alert('Không thể xóa cuộc trò chuyện. Vui lòng thử lại sau.');
    }
  }
}
