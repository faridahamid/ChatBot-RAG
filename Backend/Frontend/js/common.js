// ========================================
// RAG ChatBot - Common JavaScript Functions
// ========================================

// ========================================
// AUTHENTICATION & SESSION MANAGEMENT
// ========================================

/**
 * Check if user is logged in
 * @returns {boolean} True if user is logged in
 */
function isLoggedIn() {
  const user = sessionStorage.getItem("user");
  return user !== null;
}

/**
 * Get current user data from session
 * @returns {Object|null} User object or null if not logged in
 */
function getCurrentUser() {
  const userStr = sessionStorage.getItem("user");
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (error) {
      console.error("Error parsing user data:", error);
      return null;
    }
  }
  return null;
}

/**
 * Check if current user is admin
 * @returns {boolean} True if user is admin
 */
function isAdmin() {
  const user = getCurrentUser();
  return user && user.role === "admin";
}

/**
 * Check if current user is regular user
 * @returns {boolean} True if user is regular user
 */
function isRegularUser() {
  const user = getCurrentUser();
  return user && user.role === "user";
}

/**
 * Logout user and redirect to home
 */
function logout() {
  sessionStorage.removeItem("user");
  showMessage("Logging out...", "success");
  setTimeout(() => {
    window.location.href = "/";
  }, 1000);
}

/**
 * Redirect to login if not authenticated
 */
function requireAuth() {
  if (!isLoggedIn()) {
    showMessage("Please log in to access this page.", "error");
    setTimeout(() => {
      window.location.href = "/login";
    }, 2000);
    return false;
  }
  return true;
}

/**
 * Redirect to login if not admin
 */
function requireAdmin() {
  if (!requireAuth()) return false;
  if (!isAdmin()) {
    showMessage("Access denied. Admin privileges required.", "error");
    setTimeout(() => {
      window.location.href = "/dashboard";
    }, 2000);
    return false;
  }
  return true;
}

// ========================================
// MESSAGE & NOTIFICATION SYSTEM
// ========================================

/**
 * Show a message to the user
 * @param {string} message - Message text
 * @param {string} type - Message type (success, error, info)
 * @param {number} duration - Duration in milliseconds (optional)
 */
function showMessage(message, type = "info", duration = 5000) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll(".message");
  existingMessages.forEach((msg) => msg.remove());

  // Create message element
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type} fade-in`;
  messageDiv.textContent = message;

  // Find or create message container
  let messageContainer = document.getElementById("message");
  if (!messageContainer) {
    messageContainer = document.createElement("div");
    messageContainer.id = "message";
    messageContainer.style.display = "none";
    document.body.insertBefore(messageContainer, document.body.firstChild);
  }

  // Add message to container
  messageContainer.appendChild(messageDiv);
  messageContainer.style.display = "block";

  // Auto-hide after duration
  if (duration > 0) {
    setTimeout(() => {
      messageDiv.style.opacity = "0";
      setTimeout(() => {
        if (messageDiv.parentNode) {
          messageDiv.remove();
        }
        if (messageContainer.children.length === 0) {
          messageContainer.style.display = "none";
        }
      }, 300);
    }, duration);
  }
}

/**
 * Show success message
 * @param {string} message - Success message
 */
function showSuccess(message) {
  showMessage(message, "success");
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showError(message) {
  showMessage(message, "error");
}

/**
 * Show info message
 * @param {string} message - Info message
 */
function showInfo(message) {
  showMessage(message, "info");
}

// ========================================
// FORM VALIDATION
// ========================================

/**
 * Validate required fields in a form
 * @param {HTMLFormElement} form - Form element to validate
 * @returns {boolean} True if form is valid
 */
function validateForm(form) {
  const requiredFields = form.querySelectorAll("[required]");
  let isValid = true;

  requiredFields.forEach((field) => {
    if (!field.value.trim()) {
      field.style.borderColor = "#e74c3c";
      isValid = false;
    } else {
      field.style.borderColor = "";
    }
  });

  return isValid;
}

/**
 * Clear form fields
 * @param {HTMLFormElement} form - Form element to clear
 */
function clearForm(form) {
  const inputs = form.querySelectorAll("input, textarea, select");
  inputs.forEach((input) => {
    if (input.type === "radio" || input.type === "checkbox") {
      input.checked = false;
    } else {
      input.value = "";
    }
  });
}

// ========================================
// API UTILITIES
// ========================================

/**
 * Make API request with error handling
 * @param {string} url - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch response
 */
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return response;
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
}

/**
 * Handle API errors gracefully
 * @param {Error} error - Error object
 * @param {string} fallbackMessage - Fallback error message
 */
function handleApiError(
  error,
  fallbackMessage = "An error occurred. Please try again."
) {
  console.error("API Error:", error);

  let message = fallbackMessage;
  if (error.message && error.message !== "Failed to fetch") {
    message = error.message;
  }

  showError(message);
}

// ========================================
// DOM UTILITIES
// ========================================

/**
 * Show element with fade in animation
 * @param {HTMLElement} element - Element to show
 */
function showElement(element) {
  element.style.display = "block";
  element.classList.add("fade-in");
}

/**
 * Hide element with fade out animation
 * @param {HTMLElement} element - Element to hide
 */
function hideElement(element) {
  element.classList.remove("fade-in");
  element.style.opacity = "0";
  setTimeout(() => {
    element.style.display = "none";
    element.style.opacity = "1";
  }, 300);
}

/**
 * Toggle element visibility
 * @param {HTMLElement} element - Element to toggle
 */
function toggleElement(element) {
  if (element.style.display === "none" || element.style.display === "") {
    showElement(element);
  } else {
    hideElement(element);
  }
}

/**
 * Scroll to element smoothly
 * @param {HTMLElement} element - Element to scroll to
 * @param {number} offset - Offset from top (optional)
 */
function scrollToElement(element, offset = 0) {
  const elementPosition = element.offsetTop - offset;
  window.scrollTo({
    top: elementPosition,
    behavior: "smooth",
  });
}

// ========================================
// STRING UTILITIES
// ========================================

/**
 * Capitalize first letter of string
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Format date to readable string
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
  const d = new Date(date);
  return d.toLocaleDateString() + " " + d.toLocaleTimeString();
}

/**
 * Truncate string to specified length
 * @param {string} str - String to truncate
 * @param {number} length - Maximum length
 * @returns {string} Truncated string
 */
function truncateString(str, length = 50) {
  if (str.length <= length) return str;
  return str.substring(0, length) + "...";
}

// ========================================
// EVENT HANDLERS
// ========================================

/**
 * Add enter key handler to input fields
 * @param {HTMLElement} element - Element to add handler to
 * @param {Function} callback - Function to call on enter
 */
function addEnterKeyHandler(element, callback) {
  element.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      callback();
    }
  });
}

/**
 * Add click outside handler
 * @param {HTMLElement} element - Element to monitor
 * @param {Function} callback - Function to call when clicking outside
 */
function addClickOutsideHandler(element, callback) {
  document.addEventListener("click", (event) => {
    if (!element.contains(event.target)) {
      callback();
    }
  });
}

// ========================================
// INITIALIZATION
// ========================================

/**
 * Initialize common functionality when DOM is loaded
 */
function initializeCommon() {
  // Add global error handler
  window.addEventListener("error", (event) => {
    console.error("Global error:", event.error);
    showError("An unexpected error occurred. Please refresh the page.");
  });

  // Add unhandled promise rejection handler
  window.addEventListener("unhandledrejection", (event) => {
    console.error("Unhandled promise rejection:", event.reason);
    showError("An unexpected error occurred. Please try again.");
  });

  console.log("Common functionality initialized");

  // Enforce password change if required
  try {
    const forceStr = sessionStorage.getItem("forceChangePassword");
    if (forceStr) {
      const data = JSON.parse(forceStr);
      renderForceChangeOverlay(data && data.user_id);
    }
  } catch (e) {
    console.warn("forceChangePassword parse error", e);
  }
}

// Initialize when DOM is loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeCommon);
} else {
  initializeCommon();
}

// ============================
// Forced Password Change Overlay
// ============================
function renderForceChangeOverlay(userId) {
  // Create overlay
  const overlay = document.createElement("div");
  overlay.id = "force-change-overlay";
  overlay.style.position = "fixed";
  overlay.style.inset = "0";
  overlay.style.zIndex = "9999";
  overlay.style.background = "rgba(0,0,0,0.75)";
  overlay.style.display = "flex";
  overlay.style.alignItems = "center";
  overlay.style.justifyContent = "center";

  const panel = document.createElement("div");
  panel.style.width = "90%";
  panel.style.maxWidth = "420px";
  panel.style.background = "#1e1b2b";
  panel.style.color = "#fff";
  panel.style.borderRadius = "14px";
  panel.style.padding = "20px";
  panel.style.boxShadow = "0 10px 30px rgba(0,0,0,0.5)";

  panel.innerHTML = `
    <h2 style="margin:0 0 8px;color:#B18CFF;">Change your password</h2>
    <p style="margin:0 0 14px;color:#c9c4d6;">You must change your password before using the app.</p>
    <div id="fcp-msg" class="message" style="display:none;"></div>
    <form id="fcp-form">
      <div style="margin:10px 0;">
        <label>Current password</label>
        <input id="fcp-current" type="password" required style="width:100%;padding:10px;border-radius:8px;border:1px solid #3b3452;background:#2a2540;color:#fff;" />
      </div>
      <div style="margin:10px 0;">
        <label>New password</label>
        <input id="fcp-new" type="password" required minlength="6" style="width:100%;padding:10px;border-radius:8px;border:1px solid #3b3452;background:#2a2540;color:#fff;" />
      </div>
      <div style="margin:10px 0;">
        <label>Confirm new password</label>
        <input id="fcp-confirm" type="password" required minlength="6" style="width:100%;padding:10px;border-radius:8px;border:1px solid #3b3452;background:#2a2540;color:#fff;" />
      </div>
      <button id="fcp-submit" type="submit" style="width:100%;padding:12px;border:0;border-radius:10px;background:#8a2be2;color:#fff;font-weight:700;">Change Password</button>
    </form>
  `;

  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  const form = panel.querySelector("#fcp-form");
  const msg = panel.querySelector("#fcp-msg");
  const currentEl = panel.querySelector("#fcp-current");
  const newEl = panel.querySelector("#fcp-new");
  const confirmEl = panel.querySelector("#fcp-confirm");
  const submitBtn = panel.querySelector("#fcp-submit");

  function setMsg(text, type) {
    msg.textContent = text;
    msg.className = `message ${type}`;
    msg.style.display = "block";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (newEl.value !== confirmEl.value) {
      setMsg("New passwords do not match.", "error");
      return;
    }
    if (!userId) {
      setMsg("Missing user. Please log in again.", "error");
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Changing...";
    try {
      const fd = new FormData();
      fd.append("user_id", userId);
      fd.append("current_password", currentEl.value);
      fd.append("new_password", newEl.value);
      const res = await fetch("/change-password", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        // Clear session and force flag, then go to login
        sessionStorage.removeItem("user");
        sessionStorage.removeItem("forceChangePassword");
        setMsg("Password changed. Redirecting to login...", "success");
        setTimeout(() => { window.location.href = "/login"; }, 800);
      } else {
        setMsg(data.detail || "Failed to change password.", "error");
      }
    } catch (err) {
      setMsg("Network error.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Change Password";
    }
  });
}
