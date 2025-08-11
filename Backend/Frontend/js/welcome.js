// ========================================
// RAG ChatBot - Welcome Page JavaScript
// ========================================

// ========================================
// WELCOME PAGE INITIALIZATION
// ========================================

/**
 * Initialize welcome page when DOM is loaded
 */
function initializeWelcome() {
  setupEventListeners();
  console.log("Welcome page initialized");
}

/**
 * Set up event listeners for welcome page
 */
function setupEventListeners() {
  // Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });
}

// ========================================
// NAVIGATION FUNCTIONS
// ========================================

/**
 * Scroll to features section smoothly
 */
function scrollToFeatures() {
  const featuresSection = document.querySelector(".features-section");
  if (featuresSection) {
    featuresSection.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}

/**
 * Navigate to login page
 */
function goToLogin() {
  window.location.href = "/login";
}

/**
 * Navigate to admin registration page
 */
function goToAdminRegister() {
  window.location.href = "/admin-register";
}

// ========================================
// ANIMATION EFFECTS
// ========================================

/**
 * Add fade-in animation to elements when they come into view
 */
function setupScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("fade-in");
      }
    });
  }, observerOptions);

  // Observe elements for animation
  document
    .querySelectorAll(".feature-item, .about-section, .cta-section")
    .forEach((el) => {
      observer.observe(el);
    });
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Check if user is already logged in and redirect if necessary
 */
function checkLoginStatus() {
  const user = sessionStorage.getItem("user");
  if (user) {
    // User is logged in, redirect to dashboard
    window.location.href = "/dashboard";
  }
}

// ========================================
// PAGE INITIALIZATION
// ========================================

// Initialize welcome page when DOM is loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeWelcome);
} else {
  initializeWelcome();
}

// Set up scroll animations after a short delay
setTimeout(setupScrollAnimations, 100);

// Check login status on page load
document.addEventListener("DOMContentLoaded", checkLoginStatus);
