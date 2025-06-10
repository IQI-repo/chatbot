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
  }

  /**
   * Initialize the application
   */
  initialize() {
    // Check if user is logged in
    if (authService.isLoggedIn()) {
      this.renderMainApp();
    } else {
      this.renderLogin();
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
    // Create container for main app
    this.appContainer.innerHTML = `
      <div class="app-container">
        <div id="session-container"></div>
        <div id="chat-container"></div>
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
