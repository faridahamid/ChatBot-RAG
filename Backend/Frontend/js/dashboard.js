// ========================================
// RAG ChatBot - Dashboard JavaScript
// ========================================

// ========================================
// DASHBOARD INITIALIZATION
// ========================================

/**
 * Initialize dashboard when page loads
 */
function initializeDashboard() {
  if (!requireAuth()) return;

  loadUserInfo();
  setupEventListeners();
  console.log("Dashboard initialized");
}

/**
 * Set up event listeners for dashboard
 */
function setupEventListeners() {
  // Add enter key handler for chat input
  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    addEnterKeyHandler(chatInput, sendMessage);
  }
}

// ========================================
// USER INFORMATION MANAGEMENT
// ========================================

/**
 * Load and display user information
 */
function loadUserInfo() {
  const user = getCurrentUser();
  if (!user) {
    showError("No user information found. Please log in again.");
    setTimeout(() => {
      window.location.href = "/login";
    }, 2000);
    return;
  }

  try {
    // Display user information
    document.getElementById("username").textContent = user.username || "N/A";
    document.getElementById("role").textContent = user.role || "N/A";
    document.getElementById("organization").textContent =
      user.organization_name || "N/A";
    document.getElementById("userid").textContent = user.id || "N/A";

    // Show/hide admin actions based on role
    if (user.role === "admin") {
      showAdminActions();
    } else {
      showChatInterface();
    }

    showSuccess("Welcome back! You are successfully logged in.");
  } catch (error) {
    console.error("Error loading user information:", error);
    showError("Error loading user information.");
  }
}

/**
 * Show admin-specific action buttons
 */
function showAdminActions() {
  const adminActions = document.getElementById("adminActions");
  const adminUserActions = document.getElementById("adminUserActions");

  if (adminActions) adminActions.style.display = "inline-block";
  if (adminUserActions) adminUserActions.style.display = "inline-block";
}

/**
 * Show chat interface for regular users
 */
function showChatInterface() {
  const chatSection = document.getElementById("chatSection");
  if (chatSection) {
    chatSection.style.display = "block";
  }
}

// ========================================
// CHAT FUNCTIONALITY
// ========================================

/**
 * Handle key press in chat input
 * @param {KeyboardEvent} event - Key press event
 */
function handleKeyPress(event) {
  if (event.key === "Enter") {
    sendMessage();
  }
}

/**
 * Add a message to the chat
 * @param {string} content - Message content
 * @param {string} role - Message role (user/assistant)
 * @param {Date} timestamp - Message timestamp
 */
function addMessage(content, role, timestamp = new Date()) {
  const chatMessages = document.getElementById("chatMessages");
  if (!chatMessages) return;

  const messageDiv = document.createElement("div");
  messageDiv.className = `message-bubble ${role} fade-in`;

  const timeStr = timestamp.toLocaleTimeString();
  messageDiv.innerHTML = `
    <div>${content}</div>
    <div class="timestamp">${timeStr}</div>
  `;

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Send a message to the AI assistant
 */
async function sendMessage() {
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");

  if (!input || !sendBtn) return;

  const question = input.value.trim();
  if (!question) return;

  // Get user info from session
  const user = getCurrentUser();
  if (!user) {
    showError("Session expired. Please log in again.");
    return;
  }

  const orgId = user.organization_id;
  const userId = user.id;

  if (!orgId || !userId) {
    showError("Missing user information. Please log in again.");
    return;
  }

  // Add user message to chat
  addMessage(question, "user");

  // Clear input and disable send button
  input.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "Sending...";

  // Add loading indicator
  const loadingDiv = document.createElement("div");
  loadingDiv.className = "loading-indicator";
  loadingDiv.textContent = "AI is thinking...";
  document.getElementById("chatMessages").appendChild(loadingDiv);

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        org_id: orgId,
        user_id: userId,
        question: question,
      }),
    });

    const data = await response.json();

    // Remove loading indicator
    loadingDiv.remove();

    if (response.ok) {
      addMessage(data.answer, "assistant");
    } else {
      addMessage(
        `Error: ${data.detail || "Failed to get response"}`,
        "assistant"
      );
    }
  } catch (error) {
    console.error("Error sending message:", error);
    loadingDiv.remove();
    addMessage("Sorry, I encountered an error. Please try again.", "assistant");
  } finally {
    // Re-enable send button
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

// ========================================
// ADMIN ACTIONS
// ========================================

/**
 * Navigate to admin upload page
 */
function goToAdminUpload() {
  if (!requireAdmin()) return;
  window.location.href = "/admin-upload";
}

/**
 * Navigate to admin user management page
 */
function goToAdminUsers() {
  if (!requireAdmin()) return;
  window.location.href = "/admin-users";
}

// ========================================
// NAVIGATION FUNCTIONS
// ========================================

/**
 * Go to welcome page
 */
function goToWelcome() {
  window.location.href = "/";
}

/**
 * Go back to login page
 */
function goToLogin() {
  window.location.href = "/login";
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Format user role for display
 * @param {string} role - User role
 * @returns {string} Formatted role string
 */
function formatRole(role) {
  return capitalizeFirst(role);
}

/**
 * Format organization name for display
 * @param {string} name - Organization name
 * @returns {string} Formatted organization name
 */
function formatOrganizationName(name) {
  return name || "Unknown Organization";
}

// ========================================
// PAGE INITIALIZATION
// ========================================

// Initialize dashboard when DOM is loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeDashboard);
} else {
  initializeDashboard();
}
