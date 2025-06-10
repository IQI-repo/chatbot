/**
 * Session Component
 * Displays and manages chat sessions
 */
import chatService from '../services/chatService.js';

export default class SessionComponent {
  constructor(appContainer, onSessionSelect) {
    this.appContainer = appContainer;
    this.onSessionSelect = onSessionSelect;
    this.sessions = [];
    this.render();
    this.loadSessions();
  }

  /**
   * Render the session component
   */
  render() {
    this.appContainer.innerHTML = `
      <div class="session-list">
        <div class="session-header">
          <div class="session-title">Lịch sử chat</div>
          <button class="new-chat-button" id="new-chat-button">
            Chat mới
          </button>
        </div>
        <div id="sessions-container">
          <div class="loading-sessions">Đang tải...</div>
        </div>
      </div>
    `;

    // Store references to DOM elements
    this.sessionsContainer = document.getElementById('sessions-container');
    
    // Attach event listeners
    document.getElementById('new-chat-button').addEventListener('click', () => this.createNewSession());
  }

  /**
   * Load user sessions
   */
  async loadSessions() {
    try {
      this.sessions = await chatService.getUserSessions();
      this.renderSessions();
    } catch (error) {
      console.error('Error loading sessions:', error);
      this.sessionsContainer.innerHTML = `
        <div class="error-message">
          Không thể tải lịch sử chat. Vui lòng thử lại sau.
        </div>
      `;
    }
  }

  /**
   * Render the sessions list
   */
  renderSessions() {
    if (this.sessions.length === 0) {
      this.sessionsContainer.innerHTML = `
        <div class="no-sessions">
          Không có lịch sử chat nào. Hãy bắt đầu một cuộc trò chuyện mới!
        </div>
      `;
      return;
    }

    this.sessionsContainer.innerHTML = this.sessions.map(session => {
      const date = new Date(session.started_at);
      const formattedDate = date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });

      return `
        <div class="session-item" data-id="${session.id}">
          <div class="session-item-header">
            <div class="session-title">Chat #${session.id}</div>
            <div class="session-date">${formattedDate}</div>
          </div>
          <div class="session-preview">
            ${session.context || 'Cuộc trò chuyện mới'}
          </div>
        </div>
      `;
    }).join('');

    // Add click event listeners to session items
    const sessionItems = this.sessionsContainer.querySelectorAll('.session-item');
    sessionItems.forEach(item => {
      item.addEventListener('click', () => {
        const sessionId = parseInt(item.dataset.id);
        const session = this.sessions.find(s => s.id === sessionId);
        
        if (session) {
          chatService.setCurrentSession(session);
          if (this.onSessionSelect) {
            this.onSessionSelect(session);
          }
        }
      });
    });
  }

  /**
   * Create a new chat session
   */
  async createNewSession() {
    try {
      const newSession = await chatService.createSession();
      this.sessions.unshift(newSession);
      this.renderSessions();
      
      if (this.onSessionSelect) {
        this.onSessionSelect(newSession);
      }
    } catch (error) {
      console.error('Error creating new session:', error);
      alert('Không thể tạo cuộc trò chuyện mới. Vui lòng thử lại sau.');
    }
  }
}
