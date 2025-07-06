/**
 * Simple Authentication JavaScript for AI Tutor
 * Handles login, registration, and user management with session cookies
 */

class SimpleAuthManager {
    constructor() {
        this.baseURL = window.location.origin;
        this.user = null;
        
        this.initializeEventListeners();
        this.checkAuthState();
    }

    initializeEventListeners() {
        // Form submissions
        document.getElementById('loginFormElement').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('registerFormElement').addEventListener('submit', (e) => this.handleRegister(e));
        document.getElementById('changePasswordFormElement').addEventListener('submit', (e) => this.handleChangePassword(e));

        // Navigation buttons
        document.getElementById('showRegister').addEventListener('click', (e) => {
            e.preventDefault();
            this.showForm('register');
        });
        
        document.getElementById('showLogin').addEventListener('click', (e) => {
            e.preventDefault();
            this.showForm('login');
        });
        
        document.getElementById('changePasswordBtn').addEventListener('click', () => {
            this.showForm('changePassword');
        });
        
        document.getElementById('backToProfile').addEventListener('click', (e) => {
            e.preventDefault();
            this.showForm('profile');
        });
        
        document.getElementById('logoutBtn').addEventListener('click', () => this.handleLogout());
        document.getElementById('goToAppBtn').addEventListener('click', () => {
            window.location.href = '/frontend/index.html';
        });
    }

    async checkAuthState() {
        try {
            // Check if user is logged in by trying to get profile
            const response = await fetch(`${this.baseURL}/api/v1/auth/profile`, {
                method: 'GET',
                credentials: 'include' // Include session cookie
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.user = result.user;
                    this.showUserProfile();
                    return;
                }
            }
        } catch (error) {
            console.log('No active session');
        }
        
        // If not logged in, show login form
        this.showForm('login');
    }

    showForm(formType) {
        // Hide all forms
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('userProfile').classList.add('hidden');
        document.getElementById('changePasswordForm').classList.add('hidden');

        // Show selected form
        switch(formType) {
            case 'login':
                document.getElementById('loginForm').classList.remove('hidden');
                break;
            case 'register':
                document.getElementById('registerForm').classList.remove('hidden');
                break;
            case 'profile':
                this.showUserProfile();
                break;
            case 'changePassword':
                document.getElementById('changePasswordForm').classList.remove('hidden');
                break;
        }
    }

    showUserProfile() {
        if (this.user) {
            document.getElementById('profileName').textContent = this.user.name;
            document.getElementById('profileEmail').textContent = this.user.email;
            document.getElementById('profileRole').textContent = this.user.role;
            document.getElementById('userProfile').classList.remove('hidden');
        }
    }

    showLoading(show = true) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }

    showMessage(message, type = 'info') {
        const messageEl = document.getElementById('message');
        const messageText = document.getElementById('messageText');
        
        messageText.textContent = message;
        messageEl.className = `message ${type}`;
        messageEl.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageEl.classList.add('hidden');
        }, 5000);
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const loginData = {
            email: formData.get('email'),
            password: formData.get('password')
        };

        this.showLoading(true);

        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(loginData),
                credentials: 'include' // Include cookies
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.user = result.user;
                this.showMessage(`Welcome back, ${this.user.name}!`, 'success');
                setTimeout(() => {
                    // Redirect to main app
                    window.location.href = '/frontend/index.html';
                }, 1500);
            } else {
                this.showMessage(result.detail || 'Login failed', 'error');
            }
        } catch (error) {
            this.showMessage('Network error. Please try again.', 'error');
            console.error('Login error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const registerData = {
            name: formData.get('name'),
            email: formData.get('email'),
            password: formData.get('password'),
            role: formData.get('role')
        };

        this.showLoading(true);

        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(registerData),
                credentials: 'include' // Include cookies
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.user = result.user;
                this.showMessage(`Welcome to AI Tutor, ${this.user.name}!`, 'success');
                setTimeout(() => {
                    // Redirect to main app
                    window.location.href = '/frontend/index.html';
                }, 1500);
            } else {
                this.showMessage(result.detail || 'Registration failed', 'error');
            }
        } catch (error) {
            this.showMessage('Network error. Please try again.', 'error');
            console.error('Registration error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    async handleChangePassword(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const newPassword = formData.get('newPassword');
        const confirmPassword = formData.get('confirmPassword');
        
        if (newPassword !== confirmPassword) {
            this.showMessage('New passwords do not match', 'error');
            return;
        }

        const passwordData = {
            old_password: formData.get('oldPassword'),
            new_password: newPassword
        };

        this.showLoading(true);

        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(passwordData),
                credentials: 'include' // Include cookies
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showMessage('Password changed successfully!', 'success');
                setTimeout(() => {
                    this.showUserProfile();
                }, 1500);
            } else {
                this.showMessage(result.detail || 'Password change failed', 'error');
            }
        } catch (error) {
            this.showMessage('Network error. Please try again.', 'error');
            console.error('Password change error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    async handleLogout() {
        this.showLoading(true);

        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/logout`, {
                method: 'POST',
                credentials: 'include' // Include cookies
            });

            this.user = null;
            this.showMessage('Logged out successfully!', 'success');
            setTimeout(() => {
                this.showForm('login');
            }, 1500);
            
        } catch (error) {
            this.user = null;
            this.showMessage('Logged out (offline)', 'info');
            this.showForm('login');
        } finally {
            this.showLoading(false);
        }
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.user;
    }

    // Get current user info
    getCurrentUser() {
        return this.user;
    }
}

// Initialize authentication manager when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new SimpleAuthManager();
});

// Export for use in other scripts
window.SimpleAuthManager = SimpleAuthManager;
