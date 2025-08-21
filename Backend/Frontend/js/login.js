// ========================================
// RAG ChatBot - Login JavaScript
// ========================================

// ========================================
// LOGIN INITIALIZATION
// ========================================

/**
 * Initialize login page when DOM is loaded
 */
function initializeLogin() {
  setupEventListeners();
  console.log("Login page initialized");
}

/**
 * Set up event listeners for login page
 */
function setupEventListeners() {
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }

  // Add enter key handlers for form fields
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");

  if (usernameInput) {
    addEnterKeyHandler(usernameInput, () => passwordInput.focus());
  }

  if (passwordInput) {
    addEnterKeyHandler(passwordInput, handleLogin);
  }
}

// ========================================
// ROLE SELECTION
// ========================================

/**
 * Select a role for login
 * @param {string} role - Role to select (admin or user)
 */
// Role selection removed; login no longer requires role

// ========================================
// LOGIN HANDLING
// ========================================

/**
 * Handle login form submission
 * @param {Event} event - Form submit event
 */
async function handleLogin(event) {
  event.preventDefault();

  const form = event.target;
  if (!validateForm(form)) {
    showError("Please fill in all required fields.");
    return;
  }

  const formData = new FormData(form);
  const username = formData.get("username");
  const password = formData.get("password");
  // No role required

  // Disable login button and show loading state
  const loginBtn = document.getElementById("loginBtn");
  const originalText = loginBtn.textContent;
  loginBtn.disabled = true;
  loginBtn.textContent = "Logging in...";

  try {
    await performLogin(username, password);
  } catch (error) {
    console.error("Login failed:", error);
    showError("Login failed. Please try again.");
  } finally {
    // Re-enable login button
    loginBtn.disabled = false;
    loginBtn.textContent = originalText;
  }
}

/**
 * Perform the actual login request
 * @param {string} username - Username
 * @param {string} password - Password
 * @param {string} role - User role
 */
async function performLogin(username, password) {
  const headers = { "Content-Type": "application/json" };
  const body = JSON.stringify({ username, password });

  try {
    let response = await fetch("/admin/user/login", {
      method: "POST",
      headers,
      body,
    });
    let data = await response.json();

    if (!response.ok && response.status === 401) {
      response = await fetch("/admin/super-admin/login", {
        method: "POST",
        headers,
        body,
      });
      data = await response.json();
    }

    if (response.ok) {
      // Store user data in session
      const userData = {
        id: data.user_id ?? data.user?.id,
        username: data.username ?? data.user?.username,
        role: data.role ?? data.user?.role,
        organization_id: data.organization_id ?? data.user?.organization_id,
        organization_name: data.organization_name ?? data.user?.organization_name,
      };

      sessionStorage.setItem("user", JSON.stringify(userData));

      showSuccess("Login successful! Redirecting...");

      // Redirect based on role
      setTimeout(() => {
        if ((data.role ?? data.user?.role) === "super-admin") {
          window.location.href = "/super-admin";
        } else {
          window.location.href = "/dashboard";
        }
      }, 1500);
    } else {
      // Handle login errors
      let errorMessage = "Login failed.";

      if (data.detail) {
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((d) => d.msg || d).join(", ");
        } else if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (data.detail.message) {
          errorMessage = data.detail.message;
        }
      }

      showError(errorMessage);
    }
  } catch (error) {
    console.error("Network error during login:", error);
    throw new Error("Network error. Please check your connection.");
  }
}

// ========================================
// FORM VALIDATION
// ========================================

/**
 * Validate login form
 * @param {HTMLFormElement} form - Form element to validate
 * @returns {boolean} True if form is valid
 */
function validateLoginForm(form) {
  const username = form.querySelector("#username").value.trim();
  const password = form.querySelector("#password").value.trim();

  if (!username) {
    showError("Username is required.");
    return false;
  }

  if (!password) {
    showError("Password is required.");
    return false;
  }

  return true;
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Clear login form
 */
function clearLoginForm() {
  const form = document.getElementById("loginForm");
  if (form) {
    clearForm(form);
  }
}

/**
 * Focus on username field
 */
function focusUsername() {
  const usernameInput = document.getElementById("username");
  if (usernameInput) {
    usernameInput.focus();
  }
}

// ========================================
// PAGE INITIALIZATION
// ========================================

// Initialize login page when DOM is loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeLogin);
} else {
  initializeLogin();
}

// Focus on username field when page loads
document.addEventListener("DOMContentLoaded", focusUsername);
