/**
 * Modal Component
 * Reusable modal dialog component
 */
export default class ModalComponent {
  constructor() {
    this.modalOverlay = null;
    this.modalContainer = null;
    this.createModal();
  }

  /**
   * Create the modal DOM structure
   */
  createModal() {
    // Create modal overlay
    this.modalOverlay = document.createElement('div');
    this.modalOverlay.className = 'modal-overlay';
    
    // Create modal container
    this.modalContainer = document.createElement('div');
    this.modalContainer.className = 'modal-container';
    
    // Add modal content structure
    this.modalContainer.innerHTML = `
      <div class="modal-header">
        <h3 class="modal-title">Xác nhận</h3>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-body">
        <p>Bạn có chắc chắn muốn thực hiện hành động này?</p>
      </div>
      <div class="modal-footer">
        <button class="modal-button modal-button-cancel">Hủy</button>
        <button class="modal-button modal-button-confirm">Xác nhận</button>
      </div>
    `;
    
    // Add modal to DOM
    this.modalOverlay.appendChild(this.modalContainer);
    document.body.appendChild(this.modalOverlay);
    
    // Add event listeners
    const closeButton = this.modalContainer.querySelector('.modal-close');
    const cancelButton = this.modalContainer.querySelector('.modal-button-cancel');
    
    closeButton.addEventListener('click', () => this.hide());
    cancelButton.addEventListener('click', () => this.hide());
    
    // Close modal when clicking outside
    this.modalOverlay.addEventListener('click', (e) => {
      if (e.target === this.modalOverlay) {
        this.hide();
      }
    });
  }

  /**
   * Show the modal with custom title, message and confirm action
   * @param {string} title - Modal title
   * @param {string} message - Modal message
   * @param {function} onConfirm - Callback function when confirm button is clicked
   */
  show(title, message, onConfirm) {
    // Update modal content
    this.modalContainer.querySelector('.modal-title').textContent = title;
    this.modalContainer.querySelector('.modal-body p').textContent = message;
    
    // Update confirm button action
    const confirmButton = this.modalContainer.querySelector('.modal-button-confirm');
    
    // Remove previous event listeners
    const newConfirmButton = confirmButton.cloneNode(true);
    confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
    
    // Add new event listener
    newConfirmButton.addEventListener('click', () => {
      if (onConfirm) {
        onConfirm();
      }
      this.hide();
    });
    
    // Show modal
    this.modalOverlay.classList.add('active');
  }

  /**
   * Hide the modal
   */
  hide() {
    this.modalOverlay.classList.remove('active');
  }
}
