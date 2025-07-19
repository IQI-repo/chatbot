/**
 * Authentication Service
 * Handles user login, logout, and session management
 */
class AuthService {
  constructor() {
    this.API_URL = 'https://boship.vn';
    this.currentUser = this.getUserFromStorage();
  }

  /**
   * Get user from local storage
   */
  getUserFromStorage() {
    const userJson = localStorage.getItem('chatbot_user');
    return userJson ? JSON.parse(userJson) : null;
  }

  /**
   * Save user to local storage
   */
  saveUserToStorage(user) {
    localStorage.setItem('chatbot_user', JSON.stringify(user));
    this.currentUser = user;
  }

  /**
   * Clear user from local storage
   */
  clearUserFromStorage() {
    localStorage.removeItem('chatbot_user');
    this.currentUser = null;
  }

  /**
   * Check if user is logged in
   */
  isLoggedIn() {
    return !!this.currentUser;
  }

  /**
   * Get current user
   */
  getCurrentUser() {
    return this.currentUser;
  }

  /**
   * Login user
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise} - Promise with user data or error
   */
  async login(email, password) {
    try {
      console.log('Attempting login for:', email);
      
      const response = await fetch(`${this.API_URL}/users/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const responseData = await response.json();
      console.log('Login response data:', responseData);
      
      // Based on the actual API response structure
      if (responseData.user && responseData.accessToken) {
        // Structure the user data properly
        const processedUserData = {
          id: responseData.user.id,
          name: responseData.user.name || email.split('@')[0],
          email: responseData.user.email || email,
          token: responseData.accessToken,
          refreshToken: responseData.refreshToken,
          // Include other user fields
          phone: responseData.user.phone,
          // Add any other fields needed from the user object
        };
        
        console.log('Processed user data:', processedUserData);
        this.saveUserToStorage(processedUserData);
        return processedUserData;
      } else {
        console.error('Invalid login response structure:', responseData);
        throw new Error('Invalid login response structure');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Logout user
   */
  logout() {
    this.clearUserFromStorage();
  }
}

// Export as singleton
const authService = new AuthService();
export default authService;
