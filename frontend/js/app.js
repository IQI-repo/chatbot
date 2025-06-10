/**
 * Main App
 * Coordinates components and manages application state
 */
import authService from './services/authService.js';
import LoginComponent from './components/LoginComponent.js';
import ChatComponent from './components/ChatComponent.js';
import SessionComponent from './components/SessionComponent.js';

class App {
  constructor() {
    this.appContainer = document.getElementById('app');
    this.initialize();
    
    // Handle browser back/forward navigation
    window.addEventListener('popstate', (event) => {
      if (authService.isLoggedIn()) {
        this.handleUrlRouting();
      }
    });
  }

  /**
   * Initialize the application
   */
  initialize() {
    // Check if user is logged in
    if (authService.isLoggedIn()) {
      this.renderMainApp();
      // Handle URL routing after rendering the main app
      this.handleUrlRouting();
    } else {
      this.renderLogin();
    }
  }
  
  /**
   * Handle URL routing based on current path
   */
  handleUrlRouting() {
    const path = window.location.pathname;
    const chatRegex = /\/chat\/([0-9]+)/;
    const match = path.match(chatRegex);
    
    if (match && match[1]) {
      const sessionId = parseInt(match[1]);
      this.loadSpecificSession(sessionId);
    }
  }
  
  /**
   * Load a specific chat session by ID
   * @param {number} sessionId - The ID of the session to load
   */
  async loadSpecificSession(sessionId) {
    try {
      // Get all sessions
      const sessions = await this.sessionComponent.loadSessions();
      
      // Find the specific session
      const session = this.sessionComponent.sessions.find(s => s.id === sessionId);
      
      if (session) {
        // Set as current session
        chatService.setCurrentSession(session);
        
        // Re-render chat component
        this.renderChatComponent();
      } else {
        console.error(`Session with ID ${sessionId} not found`);
        // Redirect to base URL if session not found
        history.replaceState(null, '', '/');
      }
    } catch (error) {
      console.error('Error loading specific session:', error);
    }
  }

  /**
   * Render the login component
   */
  renderLogin() {
    new LoginComponent(this.appContainer, () => {
      this.renderMainApp();
    });
  }

  /**
   * Render the main application (sessions and chat)
   */
  renderMainApp() {
    // Create container for main app with side-by-side layout
    this.appContainer.innerHTML = `
      <div class="app-container">
        <div class="main-content">
          <div id="chat-container" class="chat-section"></div>
          <div id="session-container" class="session-section"></div>
        </div>
      </div>
    `;

    // Initialize session component
    this.sessionComponent = new SessionComponent(
      document.getElementById('session-container'),
      (session) => {
        // Re-render chat component when session is selected
        this.renderChatComponent();
      }
    );

    // Initialize chat component
    this.renderChatComponent();
  }

  /**
   * Render the chat component
   */
  renderChatComponent() {
    this.chatComponent = new ChatComponent(
      document.getElementById('chat-container'),
      () => {
        // Handle logout
        authService.logout();
        this.renderLogin();
      }
    );
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new App();
});
