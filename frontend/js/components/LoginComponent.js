/**
 * Login Component
 * Handles user authentication
 */
import authService from '../services/authService.js';

export default class LoginComponent {
  constructor(appContainer, onLoginSuccess) {
    this.appContainer = appContainer;
    this.onLoginSuccess = onLoginSuccess;
    this.render();
    this.attachEventListeners();
  }

  /**
   * Render the login component
   */
  render() {
    this.appContainer.innerHTML = `
      <div class="login-container">
        <div class="login-header">
          <h2>Đăng nhập</h2>
        </div>
        <form class="login-form" id="login-form">
          <div class="form-group">
            <label for="email">Email</label>
            <input type="email" id="email" placeholder="Nhập email" required>
          </div>
          <div class="form-group">
            <label for="password">Mật khẩu</label>
            <input type="password" id="password" placeholder="Nhập mật khẩu" required>
          </div>
          <button type="submit" class="login-button">Đăng nhập</button>
          <div class="error-message" id="login-error"></div>
        </form>
      </div>
    `;
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('login-error');
    
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      
      try {
        errorMessage.textContent = '';
        const loginButton = loginForm.querySelector('button');
        loginButton.textContent = 'Đang đăng nhập...';
        loginButton.disabled = true;
        
        const userData = await authService.login(email, password);
        
        if (this.onLoginSuccess) {
          this.onLoginSuccess(userData);
        }
      } catch (error) {
        errorMessage.textContent = error.message || 'Đăng nhập thất bại. Vui lòng thử lại.';
        loginForm.querySelector('button').textContent = 'Đăng nhập';
        loginForm.querySelector('button').disabled = false;
      }
    });
  }
}
