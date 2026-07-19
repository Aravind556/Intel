/**
 * AI Tutor Agent - Modern ChatGPT-Inspired JS Engine
 */

class AITutorApp {
    constructor() {
        this.baseURL = window.location.origin;
        this.user = null;
        this.currentConcept = null;
        this.currentSessionId = null;
        this.activeWindow = 'chatWindow';
        
        // Active quiz state
        this.activeQuiz = null;
        this.selectedMcqOption = null;

        this.initializeApp();
    }

    async initializeApp() {
        console.log('🚀 Initializing AI Tutor Frontend Engine...');

        // 1. Setup Navigation & Modal Listeners
        this.setupNavigation();
        this.setupModalListeners();
        this.setupPreferences();
        this.setupTextbookIngestion();
        
        // 2. Auth State and System Status Check
        await this.checkAuthState();
        await this.checkSystemHealth();

        // 3. Load PDFs & Sidebar items
        await this.loadPDFList();
        
        // 4. Connect Suggestion Cards
        this.setupSuggestionCards();

        // 5. Connect Active Chat Inputs
        this.setupChatEngine();

        // 6. Connect Quiz Engine
        this.setupQuizEngine();

        console.log('✅ AI Tutor Frontend Engine Ready!');
    }

    // =========================================================================
    // WINDOW NAVIGATION
    // =========================================================================
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const panels = document.querySelectorAll('.window-panel');
        const viewTitle = document.getElementById('currentViewTitle');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const targetWindow = e.currentTarget.getAttribute('data-window');
                
                // Toggle nav active state
                navItems.forEach(nav => nav.classList.remove('active'));
                e.currentTarget.classList.add('active');

                // Toggle window visibility
                panels.forEach(p => p.classList.remove('active'));
                const activePanel = document.getElementById(targetWindow);
                if (activePanel) {
                    activePanel.classList.add('active');
                }

                // Update Header Title
                this.activeWindow = targetWindow;
                viewTitle.textContent = e.currentTarget.textContent.trim();

                // If switching, load target state
                if (targetWindow === 'pdfWindow') {
                    this.loadPDFList();
                } else if (targetWindow === 'preferencesWindow') {
                    this.loadPreferences();
                } else if (targetWindow === 'masteryWindow') {
                    this.loadMasteryDashboard();
                }
            });
        });
    }

    switchWindow(windowId, navId) {
        const panels = document.querySelectorAll('.window-panel');
        const navItems = document.querySelectorAll('.nav-item');
        const viewTitle = document.getElementById('currentViewTitle');

        panels.forEach(p => p.classList.remove('active'));
        const activePanel = document.getElementById(windowId);
        if (activePanel) {
            activePanel.classList.add('active');
        }

        navItems.forEach(nav => nav.classList.remove('active'));
        const activeNav = document.getElementById(navId);
        if (activeNav) {
            activeNav.classList.add('active');
            viewTitle.textContent = activeNav.textContent.trim();
        }

        this.activeWindow = windowId;

        if (windowId === 'pdfWindow') {
            this.loadPDFList();
        } else if (windowId === 'preferencesWindow') {
            this.loadPreferences();
        } else if (windowId === 'masteryWindow') {
            this.loadMasteryDashboard();
        }
    }

    // =========================================================================
    // AUTHENTICATION & PROFILE
    // =========================================================================
    async checkAuthState() {
        try {
            const response = await fetch(`${this.baseURL}/api/v1/auth/profile`, {
                method: 'GET',
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.user) {
                    this.user = result.user;
                    this.updateAuthUI(true);
                    // Load saved preference defaults
                    await this.loadPreferences();
                    return;
                }
            }
        } catch (error) {
            console.log('No active session:', error);
        }
        this.updateAuthUI(false);
        window.location.href = '/frontend/auth.html';
    }

    updateAuthUI(loggedIn) {
        const userInfo = document.getElementById('userInfo');
        const authButtons = document.getElementById('authButtons');
        const userName = document.getElementById('userName');
        const userRole = document.getElementById('userRole');
        const userAvatar = document.getElementById('userAvatar');

        if (loggedIn && this.user) {
            userName.textContent = this.user.name;
            userRole.textContent = this.user.role || 'Student';
            userAvatar.textContent = this.user.name.charAt(0).toUpperCase();
            userInfo.style.display = 'flex';
            authButtons.style.display = 'none';
        } else {
            userInfo.style.display = 'none';
            authButtons.style.display = 'flex';
        }
    }

    async handleLogout() {
        try {
            await fetch(`${this.baseURL}/api/v1/auth/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.user = null;
            this.updateAuthUI(false);
            window.location.href = '/frontend/auth.html';
        }
    }

    // =========================================================================
    // SYSTEM STATUS & HEALTH
    // =========================================================================
    async checkSystemHealth() {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');

        try {
            const response = await fetch(`${this.baseURL}/health`);
            const data = await response.json();

            if (response.ok && data.status === 'healthy') {
                indicator.className = 'fas fa-circle status-indicator online';
                statusText.textContent = 'System Online';
            } else {
                throw new Error('Degraded');
            }
        } catch (error) {
            indicator.className = 'fas fa-circle status-indicator offline';
            statusText.textContent = 'System Offline';
        }
    }

    // =========================================================================
    // MODAL DIALOGUES
    // =========================================================================
    setupModalListeners() {
        const modal = document.getElementById('lessonPromptModal');
        const btnStartLessonAction = document.getElementById('btnStartLessonAction');
        const btnCancelLessonModal = document.getElementById('btnCancelLessonModal');
        const btnSubmitLessonModal = document.getElementById('btnSubmitLessonModal');
        const lessonConceptInput = document.getElementById('lessonConceptInput');
        const btnNewDoubt = document.getElementById('btnNewDoubt');

        // Open start lesson modal
        btnStartLessonAction.addEventListener('click', () => {
            modal.style.display = 'flex';
            lessonConceptInput.focus();
        });

        // Cancel modal
        btnCancelLessonModal.addEventListener('click', () => {
            modal.style.display = 'none';
            lessonConceptInput.value = '';
        });

        // Submit modal
        btnSubmitLessonModal.addEventListener('click', () => {
            const concept = lessonConceptInput.value.trim();
            if (concept) {
                modal.style.display = 'none';
                lessonConceptInput.value = '';
                this.startStructuredLesson(concept);
            }
        });

        // New Doubt Solver Chat
        btnNewDoubt.addEventListener('click', () => {
            this.currentConcept = null;
            this.currentSessionId = null;
            
            // Reset concept badges
            document.getElementById('activeConceptBadge').style.display = 'none';
            document.getElementById('activeConceptBadge').textContent = '';
            
            // Switch view
            this.switchWindow('chatWindow', 'navChat');
            
            // Clear message pane
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="message-bubble tutor fade-in" style="max-width:100%;">
                    <div class="msg-icon"><i class="fas fa-robot"></i></div>
                    <div class="msg-content">
                        <h3>General Doubt Solving Chat</h3>
                        <p style="margin-top: 8px;">Ask me any conceptual or factual question grounded in your textbook materials. I will answer and provide exact page citations.</p>
                    </div>
                </div>
            `;
        });
    }

    // =========================================================================
    // TEXTBOOK INGESTION / PDF MANAGEMENT
    // =========================================================================
    setupTextbookIngestion() {
        const uploadArea = document.getElementById('uploadArea');
        const pdfFileInput = document.getElementById('pdfFileInput');
        const uploadForm = document.getElementById('uploadForm');
        const cancelUploadBtn = document.getElementById('cancelUploadBtn');
        const uploadBtn = document.getElementById('uploadBtn');

        uploadArea.addEventListener('click', () => pdfFileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--accent-primary)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = 'var(--border-color)';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--border-color)';
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelection(e.dataTransfer.files[0]);
            }
        });

        pdfFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelection(e.target.files[0]);
            }
        });

        cancelUploadBtn.addEventListener('click', () => this.resetUploadForm());
        uploadBtn.addEventListener('click', () => this.uploadPDF());
    }

    handleFileSelection(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('Please select a valid PDF file.');
            return;
        }
        this.selectedFile = file;
        
        // Show configuration form
        document.getElementById('uploadForm').style.display = 'block';
        document.getElementById('uploadBtn').innerHTML = `<i class="fas fa-upload"></i> Ingest "${file.name}"`;
    }

    async uploadPDF() {
        if (!this.selectedFile) return;

        const uploadForm = document.getElementById('uploadForm');
        const uploadProgress = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        uploadForm.style.display = 'none';
        uploadProgress.style.display = 'block';
        
        progressFill.style.width = '20%';
        progressText.textContent = 'Uploading textbook to server...';

        const subject = document.getElementById('subjectInput').value.trim();
        const description = document.getElementById('descriptionInput').value.trim();

        const formData = new FormData();
        formData.append('file', this.selectedFile);
        if (subject) formData.append('subject', subject);
        if (description) formData.append('description', description);

        try {
            progressFill.style.width = '50%';
            progressText.textContent = 'Parsing text and building indexes...';

            const response = await fetch(`${this.baseURL}/api/v1/pdfs/upload`, {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                progressFill.style.width = '100%';
                progressText.textContent = 'Successfully processed textbook!';
                
                setTimeout(() => {
                    this.resetUploadForm();
                    this.loadPDFList();
                }, 1000);
            } else {
                throw new Error(data.message || data.detail || 'Processing failed');
            }
        } catch (error) {
            alert(`Ingestion failed: ${error.message}`);
            this.resetUploadForm();
        }
    }

    resetUploadForm() {
        document.getElementById('uploadForm').style.display = 'none';
        document.getElementById('uploadProgress').style.display = 'none';
        document.getElementById('subjectInput').value = '';
        document.getElementById('descriptionInput').value = '';
        document.getElementById('pdfFileInput').value = '';
        this.selectedFile = null;
    }

    async loadPDFList() {
        try {
            console.log('Fetching PDFs from API...');
            const response = await fetch(`${this.baseURL}/api/v1/pdfs`, {
                credentials: 'include'
            });
            console.log('PDF API response status:', response.status);
            if (response.ok) {
                const pdfs = await response.json();
                console.log('PDFs response json:', pdfs);
                this.renderPDFLists(pdfs);
            } else {
                console.warn('Failed to load PDFs (response not ok)');
            }
        } catch (error) {
            console.error('Failed to load PDFs:', error);
        }
    }

    renderPDFLists(pdfs) {
        console.log('renderPDFLists called with:', pdfs);
        const sidebarList = document.getElementById('sidebarPdfList');
        const mainList = document.getElementById('pdfList');
        const quizDocSelect = document.getElementById('quizDocumentSelect');
        console.log('DOM Elements check:', { sidebarList, mainList, quizDocSelect });

        if (quizDocSelect) {
            if (pdfs && pdfs.length > 0) {
                quizDocSelect.innerHTML = '<option value="">-- Select a document --</option>' + pdfs.map(pdf => `
                    <option value="${pdf.id}">${pdf.original_filename}</option>
                `).join('');
            } else {
                quizDocSelect.innerHTML = '<option value="">-- Select a document --</option>';
            }
        }

        if (!pdfs || pdfs.length === 0) {
            sidebarList.innerHTML = `<div class="empty-state" style="padding:10px; font-size:11px;">No documents uploaded.</div>`;
            mainList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No documents uploaded yet. Ingest a PDF to ground your lessons.</p>
                </div>
            `;
            return;
        }

        // Render Sidebar List
        sidebarList.innerHTML = pdfs.map(pdf => `
            <div class="library-item" title="${pdf.original_filename}">
                <div class="library-info">
                    <i class="fas fa-file-pdf"></i>
                    <span class="library-name">${pdf.original_filename}</span>
                </div>
                <button class="library-delete" onclick="window.tutorApp.deletePDF('${pdf.id}', event)">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `).join('');

        // Render Ingestion Manager List
        mainList.innerHTML = `
            <div class="pdf-list" style="display:flex; flex-direction:column; gap:12px;">
                ${pdfs.map(pdf => `
                    <div class="pdf-item">
                        <div class="pdf-info">
                            <i class="fas fa-file-pdf pdf-icon"></i>
                            <div class="pdf-details">
                                <h4 style="color:var(--text-primary); font-size:14px;">${pdf.original_filename}</h4>
                                <p style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                                    Subject: ${pdf.subject || 'Unlabeled'} • Chunks: ${pdf.total_chunks || 0} • Status: ${pdf.processing_status}
                                </p>
                            </div>
                        </div>
                        <button class="delete-btn" onclick="window.tutorApp.deletePDF('${pdf.id}', event)">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async deletePDF(id, event) {
        if (event) event.stopPropagation();
        if (!confirm('Are you sure you want to delete this document and all its indexed chunks?')) return;

        try {
            const response = await fetch(`${this.baseURL}/api/v1/pdfs/${id}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            if (response.ok) {
                await this.loadPDFList();
            } else {
                alert('Failed to delete document.');
            }
        } catch (error) {
            console.error('Delete error:', error);
        }
    }

    // =========================================================================
    // LEARNING PREFERENCES
    // =========================================================================
    setupPreferences() {
        const saveBtn = document.getElementById('btnSavePreferences');
        saveBtn.addEventListener('click', () => this.savePreferences());
    }

    async loadPreferences() {
        try {
            console.log('Fetching learning preferences...');
            const response = await fetch(`${this.baseURL}/api/v1/profile/preferences`, {
                credentials: 'include'
            });
            console.log('Preferences API response status:', response.status);
            if (response.ok) {
                const result = await response.json();
                console.log('Preferences response json:', result);
                if (result.success && result.preferences) {
                    const pref = result.preferences;
                    console.log('Applying preferences:', pref);
                    const analogyEl = document.getElementById('prefAnalogy');
                    const depthEl = document.getElementById('prefDepth');
                    const langEl = document.getElementById('prefLanguage');
                    console.log('Preferences DOM elements check:', { analogyEl, depthEl, langEl });
                    
                    if (pref.analogy_style && analogyEl) analogyEl.value = pref.analogy_style;
                    if (pref.explanation_depth && depthEl) depthEl.value = pref.explanation_depth;
                    if (pref.coding_language && langEl) langEl.value = pref.coding_language;
                    
                    if (this.user) {
                        this.user.preferences = pref;
                    }
                } else {
                    console.warn('Preferences success is false or no preferences key in response');
                }
            } else {
                console.warn('Failed to load preferences (response not ok)');
            }
        } catch (error) {
            console.error('Failed to load learning preferences:', error);
        }
    }

    async savePreferences() {
        const analogy = document.getElementById('prefAnalogy').value;
        const depth = document.getElementById('prefDepth').value;
        const lang = document.getElementById('prefLanguage').value;

        const preferencesPayload = {
            analogy_style: analogy,
            explanation_depth: depth,
            coding_language: lang
        };

        try {
            const response = await fetch(`${this.baseURL}/api/v1/profile/preferences`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preferences: preferencesPayload }),
                credentials: 'include'
            });

            if (response.ok) {
                alert('Learning preferences saved successfully!');
                if (this.user) {
                    this.user.preferences = preferencesPayload;
                }
            } else {
                alert('Failed to save learning preferences.');
            }
        } catch (error) {
            console.error('Save preferences error:', error);
        }
    }

    // =========================================================================
    // SUGGESTION CARDS
    // =========================================================================
    setupSuggestionCards() {
        const cards = document.querySelectorAll('.suggestion-card');
        cards.forEach(card => {
            card.addEventListener('click', (e) => {
                const action = e.currentTarget.getAttribute('data-action');
                const concept = e.currentTarget.getAttribute('data-concept');

                if (action === 'lesson') {
                    this.startStructuredLesson(concept);
                } else if (action === 'quiz') {
                    this.switchWindow('quizWindow', 'navChat');
                    document.getElementById('quizConceptInput').value = concept;
                } else if (action === 'preferences') {
                    this.switchWindow('preferencesWindow', 'navPreferences');
                }
            });
        });
    }

    // =========================================================================
    // CHAT / CONVERSATIONAL ENGINE
    // =========================================================================
    setupChatEngine() {
        const askBtn = document.getElementById('askBtn');
        const questionInput = document.getElementById('questionInput');
        const logoutBtn = document.getElementById('logoutBtn');

        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        askBtn.addEventListener('click', () => this.submitChatMessage());
        
        questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.submitChatMessage();
            }
        });
    }

    async startStructuredLesson(concept) {
        this.switchWindow('chatWindow', 'navChat');

        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = ''; // Clear previous messages

        // Hide Suggestions Panel
        document.getElementById('chatSuggestions').style.display = 'none';

        // 1. Set Active Concept Badge
        this.currentConcept = concept;
        const badge = document.getElementById('activeConceptBadge');
        badge.textContent = `Active Concept: ${concept}`;
        badge.style.display = 'inline-block';

        // 2. Append thinking bubble
        const thinkingId = this.appendThinkingBubble();

        try {
            const response = await fetch(`${this.baseURL}/api/v1/tutor/start-lesson`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ concept: concept }),
                credentials: 'include'
            });

            const result = await response.json();
            this.removeThinkingBubble(thinkingId);

            if (response.ok && result.success) {
                this.currentSessionId = result.session_id;
                this.appendTutorBubble(result.response_text, result.citations);
            } else {
                this.appendTutorBubble(`⚠️ Failed to start structured lesson: ${result.error || 'Server error'}`);
            }
        } catch (error) {
            this.removeThinkingBubble(thinkingId);
            this.appendTutorBubble(`❌ Error connecting to backend: ${error.message}`);
        }
    }

    async submitChatMessage() {
        const input = document.getElementById('questionInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        input.style.height = 'auto'; // Reset text area size

        // Hide Suggestions Panel
        document.getElementById('chatSuggestions').style.display = 'none';

        // Append Student Message
        this.appendStudentBubble(message);

        // Append thinking bubble
        const thinkingId = this.appendThinkingBubble();

        try {
            let response, result;
            
            if (this.currentConcept && this.currentSessionId) {
                // Lesson Chat active
                response = await fetch(`${this.baseURL}/api/v1/tutor/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        session_id: this.currentSessionId,
                        concept: this.currentConcept
                    }),
                    credentials: 'include'
                });
                result = await response.json();
            } else {
                // General Doubt Solver Fallback
                response = await fetch(`${this.baseURL}/api/v1/ask`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: message }),
                    credentials: 'include'
                });
                result = await response.json();
                // Map result schemas
                if (result.success) {
                    result.response_text = result.answer.detailed_explanation || result.answer.quick_answer;
                    result.citations = result.sources.primary_sources ? result.sources.primary_sources.map(s => `${s.title} (Page ${s.page})`) : [];
                }
            }

            this.removeThinkingBubble(thinkingId);

            if (response.ok && result.success) {
                this.appendTutorBubble(result.response_text, result.citations);
            } else {
                this.appendTutorBubble(`⚠️ Sorry, I could not complete your request. ${result.error || 'Unknown error.'}`);
            }

        } catch (error) {
            this.removeThinkingBubble(thinkingId);
            this.appendTutorBubble(`❌ Error: ${error.message}`);
        }
    }

    // Bubbles DOM Appenders
    appendStudentBubble(text) {
        const chatMessages = document.getElementById('chatMessages');
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble student fade-in';
        bubble.innerHTML = `
            <div class="msg-icon"><i class="fas fa-user"></i></div>
            <div class="msg-content">
                <p>${this.escapeHtml(text)}</p>
            </div>
        `;
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    appendThinkingBubble() {
        const id = 'thinking-' + Date.now();
        const chatMessages = document.getElementById('chatMessages');
        const bubble = document.createElement('div');
        bubble.id = id;
        bubble.className = 'message-bubble tutor fade-in';
        bubble.innerHTML = `
            <div class="msg-icon"><i class="fas fa-robot"></i></div>
            <div class="msg-content" style="display:flex; align-items:center; gap:8px;">
                <span class="status-indicator checking"><i class="fas fa-circle"></i></span>
                <span style="color:var(--text-secondary); font-size:13px; font-style:italic;">AI Tutor is constructing grounded response...</span>
            </div>
        `;
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    removeThinkingBubble(id) {
        const bubble = document.getElementById(id);
        if (bubble) bubble.remove();
    }

    appendTutorBubble(rawText, citations) {
        const chatMessages = document.getElementById('chatMessages');
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble tutor fade-in';

        let citationBadges = '';
        if (citations && citations.length > 0) {
            citationBadges = `
                <div class="citations-wrapper">
                    ${citations.map(c => `
                        <span class="citation-badge">
                            <i class="fas fa-bookmark"></i> ${c}
                        </span>
                    `).join('')}
                </div>
            `;
        }

        bubble.innerHTML = `
            <div class="msg-icon"><i class="fas fa-robot"></i></div>
            <div class="msg-content">
                <div class="markdown-body">${this.formatMarkdown(rawText)}</div>
                ${citationBadges}
            </div>
        `;

        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // =========================================================================
    // INTERACTIVE QUIZ ENGINE
    // =========================================================================
    setupQuizEngine() {
        const btnLaunchQuiz = document.getElementById('btnLaunchQuiz');
        const btnSubmitQuizAnswer = document.getElementById('btnSubmitQuizAnswer');
        const btnNextQuizQuestion = document.getElementById('btnNextQuizQuestion');
        const btnTakeQuizAction = document.getElementById('btnTakeQuizAction');
        const btnRestartQuiz = document.getElementById('btnRestartQuiz');

        // Sidebar link shortcut
        btnTakeQuizAction.addEventListener('click', () => {
            this.switchWindow('quizWindow', 'navChat');
            if (this.currentConcept) {
                document.getElementById('quizConceptInput').value = this.currentConcept;
            }
        });

        btnLaunchQuiz.addEventListener('click', () => this.launchQuiz());
        btnSubmitQuizAnswer.addEventListener('click', () => this.submitQuizAnswer());
        
        btnNextQuizQuestion.addEventListener('click', () => {
            document.getElementById('quizEvaluationCard').style.display = 'none';
            
            if (this.quizSession && this.quizSession.currentIndex < this.quizSession.questions.length - 1) {
                this.quizSession.currentIndex++;
                document.getElementById('quizActivePane').style.display = 'block';
                this.displayQuizQuestion();
            } else {
                // Show final summary pane!
                document.getElementById('quizSummaryPane').style.display = 'block';
                const scoreText = document.getElementById('quizSummaryText');
                const detailedReport = document.getElementById('quizSummaryDetailedReport');
                
                const total = this.quizSession.questions.length;
                const correctCount = this.quizSession.score;
                
                let isMcqOnly = this.quizSession.questions.every(q => q.question_type === 'mcq');
                
                if (isMcqOnly) {
                    scoreText.innerHTML = `You answered <strong>${correctCount}</strong> out of <strong>${total}</strong> questions correctly!`;
                } else {
                    scoreText.innerHTML = `You have completed all <strong>${total}</strong> questions in this session.`;
                }
                
                detailedReport.innerHTML = this.quizSession.questions.map((q, idx) => {
                    if (q.question_type === 'mcq') {
                        const status = q.userCorrect ? '<span style="color:var(--success)">[Correct]</span>' : '<span style="color:var(--error)">[Incorrect]</span>';
                        return `
                            <div style="margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                                <strong>Q${idx + 1}: ${q.question}</strong><br>
                                Status: ${status}<br>
                                Your Answer: <code>Option ${q.userAnswer || 'None'}</code> | Correct Option: <code>Option ${q.ideal_answer}</code>
                            </div>
                        `;
                    } else {
                        return `
                            <div style="margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px;">
                                <strong>Q${idx + 1}: ${q.question}</strong><br>
                                Your Answer: <blockquote style="margin: 4px 0; padding: 6px 10px; background: rgba(255,255,255,0.02); border-left: 2px solid var(--accent-primary); color: var(--text-primary); font-family: monospace;">${q.userAnswer || 'None'}</blockquote>
                                Ideal Reference Answer: <blockquote style="margin: 4px 0; padding: 6px 10px; background: rgba(255,255,255,0.02); border-left: 2px solid var(--success); color: var(--text-primary); font-family: monospace;">${q.ideal_answer}</blockquote>
                            </div>
                        `;
                    }
                }).join('');
            }
        });

        if (btnRestartQuiz) {
            btnRestartQuiz.addEventListener('click', () => {
                document.getElementById('quizSummaryPane').style.display = 'none';
                document.getElementById('quizSetupPane').style.display = 'block';
            });
        }
    }

    async launchQuiz() {
        const docSelect = document.getElementById('quizDocumentSelect');
        const documentId = docSelect.value;
        const conceptInput = document.getElementById('quizConceptInput');
        const concept = conceptInput.value.trim();
        const numQuestionsSelect = document.getElementById('quizNumQuestionsSelect');
        const numQuestions = parseInt(numQuestionsSelect.value) || 5;
        const typeSelect = document.getElementById('quizTypeSelect');
        const questionType = typeSelect.value;

        if (!documentId && !concept) {
            alert('Please select a Source Document or specify a Concept to test!');
            return;
        }

        const setupPane = document.getElementById('quizSetupPane');
        const activePane = document.getElementById('quizActivePane');

        setupPane.style.display = 'none';
        activePane.style.display = 'block';
        
        document.getElementById('quizActiveConcept').textContent = concept || 'Document Quiz';
        document.getElementById('quizQuestionText').textContent = 'Generating questions calibrated strictly from the textbook...';
        document.getElementById('quizMcqOptions').innerHTML = '';
        document.getElementById('quizSubjectiveAnswer').style.display = 'none';

        try {
            const response = await fetch(`${this.baseURL}/api/v1/tutor/quiz`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    concept: concept || null,
                    document_id: documentId || null,
                    question_type: questionType,
                    num_questions: numQuestions
                }),
                credentials: 'include'
            });

            const result = await response.json();

            if (response.ok && result.success && result.questions && result.questions.length > 0) {
                // Initialize the multi-question quiz session
                this.quizSession = {
                    questions: result.questions.map(q => ({
                        ...q,
                        question_type: questionType,
                        userAnswer: null,
                        userCorrect: false
                    })),
                    currentIndex: 0,
                    score: 0
                };
                
                this.displayQuizQuestion();
            } else {
                alert(`Quiz generation failed: ${result.error || 'Server error'}`);
                activePane.style.display = 'none';
                setupPane.style.display = 'block';
            }
        } catch (error) {
            alert(`Network error generating quiz: ${error.message}`);
            activePane.style.display = 'none';
            setupPane.style.display = 'block';
        }
    }

    displayQuizQuestion() {
        if (!this.quizSession || !this.quizSession.questions) return;
        
        const qIdx = this.quizSession.currentIndex;
        const qTotal = this.quizSession.questions.length;
        const q = this.quizSession.questions[qIdx];
        this.activeQuiz = q;
        
        // Render Stars
        const starsContainer = document.getElementById('quizDifficultyStars');
        starsContainer.innerHTML = '';
        for (let i = 0; i < 5; i++) {
            const star = document.createElement('i');
            star.className = i < q.difficulty ? 'fas fa-star' : 'far fa-star';
            starsContainer.appendChild(star);
        }

        // Render Question text with Markdown support
        const questionHtml = this.formatMarkdown(q.question);
        document.getElementById('quizQuestionText').innerHTML = `
            ${questionHtml}
            <div style="font-size:12px; color:var(--text-secondary); margin-top:12px; font-weight: 500;">
                Question ${qIdx + 1} of ${qTotal} (Difficulty: ${q.difficulty}/5)
            </div>
        `;

        // Render answer fields based on MCQ or subjective/coding
        if (q.question_type === 'mcq') {
            document.getElementById('quizSubjectiveAnswer').style.display = 'none';
            const mcqContainer = document.getElementById('quizMcqOptions');
            mcqContainer.style.display = 'flex';
            
            // Render dynamic MCQ options from backend
            const options = q.options || {
                'A': 'Option A',
                'B': 'Option B',
                'C': 'Option C',
                'D': 'Option D'
            };
            mcqContainer.innerHTML = Object.entries(options).map(([opt, text]) => `
                <div class="mcq-option-card" data-option="${opt}">
                    <div class="mcq-option-letter">${opt}</div>
                    <div class="mcq-option-text">${text}</div>
                </div>
            `).join('');

            this.selectedMcqOption = null;
            const optionCards = mcqContainer.querySelectorAll('.mcq-option-card');
            optionCards.forEach(card => {
                card.addEventListener('click', (e) => {
                    optionCards.forEach(c => c.classList.remove('selected'));
                    e.currentTarget.classList.add('selected');
                    this.selectedMcqOption = e.currentTarget.getAttribute('data-option');
                });
            });
        } else {
            document.getElementById('quizMcqOptions').style.display = 'none';
            const answerEditor = document.getElementById('quizSubjectiveAnswer');
            answerEditor.style.display = 'block';
            answerEditor.value = '';
            this.selectedMcqOption = null;
        }
    }

    submitQuizAnswer() {
        if (!this.activeQuiz || !this.quizSession) return;

        let studentAnswer = '';
        if (this.activeQuiz.question_type === 'mcq') {
            if (!this.selectedMcqOption) {
                alert('Please select an option first!');
                return;
            }
            studentAnswer = this.selectedMcqOption;
        } else {
            studentAnswer = document.getElementById('quizSubjectiveAnswer').value.trim();
            if (!studentAnswer) {
                alert('Please type in your answer first!');
                return;
            }
        }

        const activePane = document.getElementById('quizActivePane');
        const evalCard = document.getElementById('quizEvaluationCard');

        activePane.style.display = 'none';
        evalCard.style.display = 'block';

        // Save student answer
        const currentQ = this.quizSession.questions[this.quizSession.currentIndex];
        currentQ.userAnswer = studentAnswer;

        // Perform local evaluation (NO backend API call to evaluate)
        const isMcq = (this.activeQuiz.question_type === 'mcq');
        const idealAnswer = this.activeQuiz.ideal_answer || '';
        
        let isCorrect = false;
        let feedback = '';

        if (isMcq) {
            isCorrect = (studentAnswer.toUpperCase() === idealAnswer.toUpperCase());
            currentQ.userCorrect = isCorrect;
            
            if (isCorrect) {
                this.quizSession.score++;
                feedback = `🎉 **Correct!** You selected **Option ${studentAnswer}** which is correct.`;
            } else {
                feedback = `❌ **Incorrect.** You selected **Option ${studentAnswer}**. The correct option is **Option ${idealAnswer}**.`;
            }
        } else {
            // Subjective / Coding questions: Show ideal answer comparison
            feedback = `📝 **Response recorded.** Compare your response with the ideal reference answer:\n\n**Ideal Answer:**\n${idealAnswer}\n\n**Milestones:**\n${(this.activeQuiz.rubric?.milestones || []).map(m => `- ${m}`).join('\n')}`;
        }

        // Render Score badge in UI
        const scoreCircle = document.getElementById('evalScoreCircle');
        const statusBadge = document.getElementById('evalStatusBadge');
        const feedbackTitle = document.getElementById('evalFeedbackTitle');
        
        if (isMcq) {
            scoreCircle.textContent = isCorrect ? '100%' : '0%';
            scoreCircle.className = isCorrect ? 'evaluation-score-circle success' : 'evaluation-score-circle danger';
            statusBadge.textContent = isCorrect ? 'Correct' : 'Incorrect';
            statusBadge.className = 'concept-badge';
            statusBadge.style.borderColor = isCorrect ? 'var(--success)' : 'var(--error)';
            statusBadge.style.color = isCorrect ? 'var(--success)' : 'var(--error)';
            feedbackTitle.textContent = isCorrect ? 'Correct Answer!' : 'Incorrect Answer';
        } else {
            scoreCircle.textContent = 'Done';
            scoreCircle.className = 'evaluation-score-circle success';
            statusBadge.textContent = 'Completed';
            statusBadge.className = 'concept-badge';
            statusBadge.style.borderColor = 'var(--accent-primary)';
            statusBadge.style.color = 'var(--accent-primary)';
            feedbackTitle.textContent = 'Reference Comparison';
        }

        // Hide mastery delta and misconceptions since they are local checks
        document.getElementById('evalMasteryDelta').textContent = '';
        document.getElementById('evalFeedbackText').innerHTML = this.formatMarkdown(feedback);
        document.getElementById('evalMisconceptionsPanel').style.display = 'none';

        // Update button text for Next button
        const btnNext = document.getElementById('btnNextQuizQuestion');
        if (this.quizSession.currentIndex < this.quizSession.questions.length - 1) {
            btnNext.innerHTML = '<i class="fas fa-arrow-right"></i> Next Question';
        } else {
            btnNext.innerHTML = '<i class="fas fa-check-circle"></i> Finish & See Results';
        }
    }

    // =========================================================================
    // MASTERY DASHBOARD LOADER
    // =========================================================================
    async loadMasteryDashboard() {
        console.log('loadMasteryDashboard called');
        const grid = document.getElementById('masteryGridContainer');
        console.log('Mastery grid container element:', grid);
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;"><div class="spinner"></div><p>Fetching student learning profile...</p></div>';

        try {
            console.log('Fetching student mastery from API...');
            const response = await fetch(`${this.baseURL}/api/v1/profile/mastery`, {
                credentials: 'include'
            });
            console.log('Mastery API response status:', response.status);
            const data = await response.json();
            console.log('Mastery response json:', data);

            if (response.ok && data.success) {
                this.renderMasteryDashboard(data.mastery);
            } else {
                console.warn('Failed to retrieve mastery data or data.success is false');
                grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1;"><p>Failed to retrieve mastery data.</p></div>';
            }
        } catch (error) {
            console.error('Error loading mastery dashboard:', error);
            grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><p>Error connecting: ${error.message}</p></div>`;
        }
    }

    renderMasteryDashboard(masteryList) {
        console.log('renderMasteryDashboard called with list:', masteryList);
        const grid = document.getElementById('masteryGridContainer');
        console.log('Render target grid:', grid);

        if (!masteryList || masteryList.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1;">
                    <i class="fas fa-award"></i>
                    <p>No concepts tested yet. Complete calibrated quizzes to generate your mastery profile.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = masteryList.map(item => {
            const scorePercent = Math.round(item.mastery_score * 100);
            
            // Status determination
            let statusClass = 'weak';
            let statusLabel = 'Needs Review';
            if (item.mastery_score >= 0.70) {
                statusClass = 'strong';
                statusLabel = 'Strong';
            } else if (item.mastery_score >= 0.40) {
                statusClass = 'progress';
                statusLabel = 'In Progress';
            }

            const formattedDate = item.last_tested_at 
                ? new Date(item.last_tested_at).toLocaleDateString() 
                : 'Never';

            return `
                <div class="mastery-card fade-in">
                    <div class="mastery-card-header">
                        <span class="mastery-concept-name">${item.concept_name}</span>
                        <span class="mastery-status-badge ${statusClass}">${statusLabel}</span>
                    </div>
                    <div>
                        <div class="mastery-stat-row">
                            <span>Concept Mastery Score</span>
                            <strong style="color:var(--text-primary);">${scorePercent}%</strong>
                        </div>
                        <div class="mastery-progress-wrapper" style="margin-bottom:14px;">
                            <div class="mastery-progress-bar" style="width: ${scorePercent}%;"></div>
                        </div>
                        <div class="mastery-stat-row" style="color:var(--text-muted); font-size:11px;">
                            <span>Tested: ${item.times_tested || 0} times</span>
                            <span>Last active: ${formattedDate}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // =========================================================================
    // TEXT FORMATTERS (MARKDOWN / CITATIONS)
    // =========================================================================
    formatMarkdown(text) {
        if (!text) return '';
        let html = this.escapeHtml(text);

        // Code blocks: ```language ... ```
        html = html.replace(/```(?:[a-zA-Z0-9]+)?\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Bold: **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Headings: ### title
        html = html.replace(/### (.*?)\n/g, '<h4 style="color:var(--text-primary); margin-top:16px; margin-bottom:8px;">$1</h4>');
        html = html.replace(/## (.*?)\n/g, '<h3 style="color:var(--text-primary); margin-top:20px; margin-bottom:10px;">$1</h3>');
        html = html.replace(/# (.*?)\n/g, '<h2 style="color:var(--text-primary); margin-top:24px; margin-bottom:12px;">$1</h2>');

        // Lists: * item or - item
        html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li style="margin-left:20px; margin-top:4px;">$1</li>');

        // Citations: [textbook.pdf (Page 12)]
        html = html.replace(/\[([^\]]+\.pdf\s+\(Page\s+\d+\))\]/g, '<span class="citation-badge"><i class="fas fa-bookmark"></i> $1</span>');

        // New lines
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Instantiate global app reference
window.addEventListener('DOMContentLoaded', () => {
    window.tutorApp = new AITutorApp();
});
