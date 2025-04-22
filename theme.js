function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButton(savedTheme);
  }
  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
  }
  function updateThemeButton(theme) {
    const themeButtons = document.querySelectorAll('.theme-toggle');
    themeButtons.forEach(button => {
      button.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    });
  }
  document.addEventListener('DOMContentLoaded', initializeTheme);
  window.toggleTheme = toggleTheme;