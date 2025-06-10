/**
 * Chat Service
 * Handles interactions with the chat API
 */
import authService from './authService.js';

class ChatService {
  constructor() {
    this.API_URL = '/api/chat-mysql';
    this.currentSession = null;
  }

  /**
   * Get all chat sessions for the current user
   * @returns {Promise} - Promise with sessions data
   */
  async getUserSessions() {
    try {
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');
      
      console.log('Getting sessions for user:', user.id);

      const response = await fetch(`${this.API_URL}/sessions/user/${user.id}`, {
        headers: {
          'Authorization': `Bearer ${user.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch sessions');
      }

      const data = await response.json();
      return data.sessions;
    } catch (error) {
      console.error('Error fetching sessions:', error);
      throw error;
    }
  }

  /**
   * Create a new chat session
   * @param {string} context - Optional context for the session
   * @returns {Promise} - Promise with new session data
   */
  async createSession(context = null) {
    try {
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');
      
      // Log user data to help with debugging
      console.log('Creating session with user:', user);
      
      // Ensure we have a valid user ID
      if (!user.id) {
        throw new Error('User ID is missing');
      }

      // Prepare request body
      const requestBody = {
        user_id: user.id,
        context: context || null,
        bot_model: 'default'
      };
      
      console.log('Session request body:', requestBody);

      const response = await fetch(`${this.API_URL}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`,
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Server error response:', errorData);
        throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Session created successfully:', data);
      this.currentSession = data.session;
      return data.session;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  }

  /**
   * End the current chat session
   * @returns {Promise} - Promise with result
   */
  async endCurrentSession() {
    try {
      if (!this.currentSession) throw new Error('No active session');
      
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');

      const response = await fetch(`${this.API_URL}/sessions/${this.currentSession.id}/end`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${user.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to end session');
      }

      const data = await response.json();
      this.currentSession = null;
      return data;
    } catch (error) {
      console.error('Error ending session:', error);
      throw error;
    }
  }

  /**
   * Get messages for a specific session
   * @param {number} sessionId - Session ID
   * @returns {Promise} - Promise with messages data
   */
  async getSessionMessages(sessionId) {
    try {
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');

      const response = await fetch(`${this.API_URL}/messages/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${user.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch messages');
      }

      const data = await response.json();
      return data.messages;
    } catch (error) {
      console.error('Error fetching messages:', error);
      throw error;
    }
  }

  /**
   * Send a message in the current session
   * @param {string} message - Message content
   * @param {object} metadata - Optional metadata
   * @returns {Promise} - Promise with message data and bot reply
   */
  async sendMessage(message, metadata = null) {
    try {
      if (!this.currentSession) {
        // Create a new session if none exists
        await this.createSession();
      }
      
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');

      const response = await fetch(`${this.API_URL}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`,
        },
        body: JSON.stringify({
          session_id: this.currentSession.id,
          sender: 'user',
          message,
          metadata
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * Set the current active session
   * @param {object} session - Session object
   */
  setCurrentSession(session) {
    this.currentSession = session;
  }

  /**
   * Get the current active session
   * @returns {object} - Current session object
   */
  getCurrentSession() {
    return this.currentSession;
  }
  
  /**
   * Delete a chat session
   * @param {number} sessionId - Session ID to delete
   * @returns {Promise} - Promise with result
   */
  async deleteSession(sessionId) {
    try {
      const user = authService.getCurrentUser();
      if (!user) throw new Error('User not logged in');

      const response = await fetch(`${this.API_URL}/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${user.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete session');
      }

      const data = await response.json();
      
      // If we're deleting the current session, clear it
      if (this.currentSession && this.currentSession.id === sessionId) {
        this.currentSession = null;
      }
      
      return data;
    } catch (error) {
      console.error('Error deleting session:', error);
      throw error;
    }
  }
}

// Export as singleton
const chatService = new ChatService();
export default chatService;
