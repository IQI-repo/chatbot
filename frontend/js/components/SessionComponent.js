/**
 * Session Component
 * Displays and manages chat sessions
 */
import chatService from '../services/chatService.js';
import ModalComponent from './ModalComponent.js';

export default class SessionComponent {
  constructor(appContainer, onSessionSelect) {
    this.appContainer = appContainer;
    this.onSessionSelect = onSessionSelect;
    this.sessions = [];
    this.modal = new ModalComponent();
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Chat mới
          </button>
        </div>
        <div id="sessions-container" class="sessions-container">
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
   * @returns {Promise<Array>} - Promise that resolves to the sessions array
   */
  async loadSessions() {
    try {
      this.sessions = await chatService.getUserSessions();
      this.renderSessions();
      return this.sessions;
    } catch (error) {
      console.error('Error loading sessions:', error);
      this.sessionsContainer.innerHTML = `
        <div class="error-message">
          Không thể tải lịch sử chat. Vui lòng thử lại sau.
        </div>
      `;
      return [];
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
          <div class="session-actions">
            <button class="delete-session-btn" data-id="${session.id}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"></path>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Add click event listeners to session items
    const sessionItems = this.sessionsContainer.querySelectorAll('.session-item');
    sessionItems.forEach(item => {
      // Prevent click event on delete button from triggering session selection
      const deleteBtn = item.querySelector('.delete-session-btn');
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent event bubbling
        const sessionId = parseInt(deleteBtn.dataset.id);
        this.confirmDeleteSession(sessionId);
      });
      
      // Session selection click event
      item.addEventListener('click', (e) => {
        // Don't select session if clicking on delete button
        if (e.target.closest('.delete-session-btn')) {
          return;
        }
        
        const sessionId = parseInt(item.dataset.id);
        const session = this.sessions.find(s => s.id === sessionId);
        
        if (session) {
          chatService.setCurrentSession(session);
          // Update URL to include session ID
          history.pushState({sessionId}, '', `/chat/${sessionId}`);
          if (this.onSessionSelect) {
            this.onSessionSelect(session);
          }
        }
      });
    });
  }
  
  /**
   * Show confirmation modal before deleting a session
   * @param {number} sessionId - ID of the session to delete
   */
  confirmDeleteSession(sessionId) {
    this.modal.show(
      'Xóa cuộc trò chuyện', 
      'Bạn có chắc chắn muốn xóa cuộc trò chuyện này? Hành động này không thể hoàn tác.',
      () => this.deleteSession(sessionId)
    );
  }
  
  /**
   * Delete a chat session
   * @param {number} sessionId - ID of the session to delete
   */
  async deleteSession(sessionId) {
    try {
      await chatService.deleteSession(sessionId);
      
      // Remove session from local array
      this.sessions = this.sessions.filter(session => session.id !== sessionId);
      
      // Re-render sessions list
      this.renderSessions();
      
      // If current session was deleted, create a new one
      const currentSession = chatService.getCurrentSession();
      if (!currentSession) {
        this.createNewSession();
      } else {
        // Update URL to reflect current session
        history.replaceState({sessionId: currentSession.id}, '', `/chat/${currentSession.id}`);
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      alert('Không thể xóa cuộc trò chuyện. Vui lòng thử lại sau.');
    }
  }

  /**
   * Create a new chat session
   */
  async createNewSession() {
    try {
      const newSession = await chatService.createSession();
      this.sessions.unshift(newSession);
      this.renderSessions();
      
      // Update URL to include the new session ID
      history.pushState({sessionId: newSession.id}, '', `/chat/${newSession.id}`);
      
      if (this.onSessionSelect) {
        this.onSessionSelect(newSession);
      }
    } catch (error) {
      console.error('Error creating new session:', error);
      alert('Không thể tạo cuộc trò chuyện mới. Vui lòng thử lại sau.');
    }
  }
}
