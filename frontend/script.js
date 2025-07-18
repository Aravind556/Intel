/**
 * AI Tutor Frontend Application
 * Enhanced with authentication support
 */

class AITutorApp {
    constructor() {
        this.baseURL = window.location.origin;
        this.systemStatus = 'unknown';
        this.uploadedFiles = [];
        this.availableDocuments = [];
        this.selectedDocumentId = null;
        
        // Authentication - now session-based
        this.user = null;
        
        this.initializeApp();
    }

    async initializeApp() {
        console.log('🚀 Initializing AI Tutor App...');
        
        // Check authentication status
        await this.checkAuthState();
        
        // Initialize event listeners
        this.initializeEventListeners();
        
        // Check system status
        await this.checkSystemStatus();
        
        // Load available documents
        await this.loadPDFList();
        
        console.log('✅ AI Tutor App initialized successfully');
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
                }
            }
        } catch (error) {
            console.log('No active session');
            this.user = null;
        }
        
        this.updateAuthUI();
    }

    updateAuthUI() {
        const userInfo = document.getElementById('userInfo');
        const authButtons = document.getElementById('authButtons');
        const userName = document.getElementById('userName');
        
        if (this.user) {
            userName.textContent = `Welcome, ${this.user.name}`;
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
                credentials: 'include' // Include session cookie
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.user = null;
            this.updateAuthUI();
            this.showSuccess('Logged out successfully');
        }
    }

    initializeEventListeners() {
        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }
        
        // Call the existing setup method
        this.setupEventListeners();
    }

    init() {
        this.setupEventListeners();
        this.checkSystemHealth();
        this.loadSystemStats();
        this.loadPDFList();
    }

    setupEventListeners() {
        // Question input and buttons
        const questionInput = document.getElementById('questionInput');
        const askBtn = document.getElementById('askBtn');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const retryBtn = document.getElementById('retryBtn');

        // Example buttons
        const exampleBtns = document.querySelectorAll('.example-btn');
        
        // Info panel toggle
        const togglePanel = document.getElementById('togglePanel');
        const infoPanel = document.getElementById('infoPanel');

        // PDF Upload elements
        const uploadArea = document.getElementById('uploadArea');
        const pdfFileInput = document.getElementById('pdfFileInput');
        const browseBtn = document.getElementById('browseBtn');
        const uploadForm = document.getElementById('uploadForm');
        const uploadBtn = document.getElementById('uploadBtn');
        const cancelUploadBtn = document.getElementById('cancelUploadBtn');

        // Event listeners
        askBtn.addEventListener('click', () => this.askQuestion());
        analyzeBtn.addEventListener('click', () => this.analyzeQuestion());
        retryBtn.addEventListener('click', () => this.askQuestion());
        
        exampleBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const question = e.currentTarget.dataset.question;
                questionInput.value = question;
                this.askQuestion();
            });
        });

        // PDF Upload event listeners
        browseBtn.addEventListener('click', () => pdfFileInput.click());
        uploadArea.addEventListener('click', () => pdfFileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFileSelection(e.dataTransfer.files);
        });
        
        pdfFileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
        });
        
        uploadBtn.addEventListener('click', () => this.uploadPDF());
        cancelUploadBtn.addEventListener('click', () => this.cancelUpload());

        // Enter key to ask question
        questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                this.askQuestion();
            }
        });

        // Info panel toggle
        togglePanel.addEventListener('click', () => {
            infoPanel.classList.toggle('open');
            const icon = togglePanel.querySelector('i');
            if (infoPanel.classList.contains('open')) {
                icon.className = 'fas fa-chevron-left';
            } else {
                icon.className = 'fas fa-chevron-right';
            }
        });

        // Auto-resize textarea
        questionInput.addEventListener('input', () => {
            questionInput.style.height = 'auto';
            questionInput.style.height = questionInput.scrollHeight + 'px';
        });
    }

    async checkSystemHealth() {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        try {
            statusIndicator.className = 'fas fa-circle status-indicator checking';
            statusText.textContent = 'Checking system...';
            
            const response = await fetch(`${this.baseURL}/health`);
            const data = await response.json();
            
            if (response.ok && data.status === 'healthy') {
                statusIndicator.className = 'fas fa-circle status-indicator online';
                statusText.textContent = 'System Online';
            } else {
                throw new Error('System unhealthy');
            }
        } catch (error) {
            console.error('Health check failed:', error);
            statusIndicator.className = 'fas fa-circle status-indicator offline';
            statusText.textContent = 'System Offline';
        }
    }

    async checkSystemStatus() {
        try {
            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
            
            const response = await fetch(`${this.baseURL}/health`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            const data = await response.json();
            
            if (response.ok && data.status === 'healthy') {
                this.systemStatus = 'online';
                console.log('✅ System status: Online');
            } else {
                this.systemStatus = 'degraded';
                console.log('⚠️ System status: Degraded');
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('⏰ System check timed out');
            } else {
                console.log('❌ System check error:', error);
            }
            this.systemStatus = 'offline';
            console.log('❌ System status: Offline');
        }
    }

    async loadSystemStats() {
        try {
            const response = await fetch(`${this.baseURL}/api/v1/stats`);
            const data = await response.json();
            
            if (response.ok) {
                const stats = data.processing_stats;
                document.getElementById('totalPdfs').textContent = stats.total_pdfs || 0;
                document.getElementById('processedPdfs').textContent = stats.processed_pdfs || 0;
                document.getElementById('totalChunks').textContent = stats.total_chunks || 0;
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async analyzeQuestion() {
        const questionInput = document.getElementById('questionInput');
        const question = questionInput.value.trim();
        
        if (!question) {
            this.showError('Please enter a question first.');
            return;
        }

        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.showLoading('Analyzing your question...');
        this.hideAllSections();

        try {
            const response = await fetch(`${this.baseURL}/api/v1/analyze/${encodeURIComponent(question)}`);
            const data = await response.json();
            
            if (response.ok) {
                this.displayAnalysis(data);
            } else {
                throw new Error(data.detail || 'Analysis failed');
            }
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.isProcessing = false;
            this.hideLoading();
        }
    }

    async askQuestion() {
        const questionInput = document.getElementById('questionInput');
        const pdfSelector = document.getElementById('pdfSelector');
        const question = questionInput.value.trim();
        const selectedPDF = pdfSelector ? pdfSelector.value : null;
        
        if (!question) {
            this.showError('Please enter a question first.');
            return;
        }

        if (this.isProcessing) return;
        
        this.isProcessing = true;
        
        // Show loading message based on whether a specific PDF is selected
        const loadingMessage = selectedPDF 
            ? 'Searching in selected document...' 
            : 'Processing your question...';
        this.showLoading(loadingMessage);
        this.hideAllSections();

        const processingSteps = selectedPDF 
            ? [
                'Analyzing question...',
                'Searching selected document...',
                'Extracting relevant content...',
                'Generating response...'
            ]
            : [
                'Analyzing question...',
                'Searching knowledge base...',
                'Generating response...',
                'Formatting answer...'
            ];

        this.showProcessingSteps(processingSteps);

        try {
            const requestBody = {
                question: question,
                user_id: null // Using default user for now
            };
            
            // Add document_id if a specific PDF is selected
            if (selectedPDF) {
                requestBody.document_id = selectedPDF;
            }

            const response = await fetch(`${this.baseURL}/api/v1/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            
            if (response.ok) {
                this.currentSession = data.session_id;
                this.displayAnswer(data, selectedPDF);
            } else {
                throw new Error(data.detail || 'Failed to process question');
            }
        } catch (error) {
            console.error('Question processing failed:', error);
            this.showError(`Failed to process question: ${error.message}`);
        } finally {
            this.isProcessing = false;
            this.hideLoading();
        }
    }

    showLoading(message) {
        const loadingSection = document.getElementById('loadingSection');
        const loadingText = document.getElementById('loadingText');
        
        loadingText.textContent = message;
        loadingSection.style.display = 'block';
        loadingSection.classList.add('fade-in');
    }

    hideLoading() {
        const loadingSection = document.getElementById('loadingSection');
        loadingSection.style.display = 'none';
    }

    showProcessingSteps(steps) {
        const processingSteps = document.getElementById('processingSteps');
        processingSteps.innerHTML = '';
        
        steps.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = 'processing-step';
            stepElement.innerHTML = `<i class="fas fa-circle"></i> ${step}`;
            processingSteps.appendChild(stepElement);
            
            // Simulate step progression
            setTimeout(() => {
                stepElement.classList.add('active');
                setTimeout(() => {
                    stepElement.classList.remove('active');
                    stepElement.classList.add('completed');
                    stepElement.querySelector('i').className = 'fas fa-check';
                }, 1000 + index * 500);
            }, index * 1000);
        });
    }

    displayAnalysis(data) {
        const analysisSection = document.getElementById('analysisSection');
        const analysisGrid = document.getElementById('analysisGrid');
        
        const analysis = data.analysis;
        
        analysisGrid.innerHTML = `
            <div class="analysis-item">
                <span class="analysis-label">Question Type</span>
                <span class="analysis-value">${analysis.question_type}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Difficulty Level</span>
                <span class="analysis-value">${analysis.difficulty}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Subject</span>
                <span class="analysis-value">${analysis.subject || 'Not detected'}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Intent</span>
                <span class="analysis-value">${analysis.intent}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Requires Calculation</span>
                <span class="analysis-value">${analysis.requires_calculation ? 'Yes' : 'No'}</span>
            </div>
            <div class="analysis-item">
                <span class="analysis-label">Keywords</span>
                <div class="analysis-value list">
                    ${analysis.keywords.slice(0, 5).map(keyword => 
                        `<span class="keyword-tag">${keyword}</span>`
                    ).join('')}
                </div>
            </div>
        `;
        
        analysisSection.style.display = 'block';
        analysisSection.classList.add('fade-in');
    }

    displayAnswer(data, selectedPDF = null) {
        const answerSection = document.getElementById('answerSection');
        const quickAnswer = document.getElementById('quickAnswer');
        const detailedExplanation = document.getElementById('detailedExplanation');
        const confidenceScore = document.getElementById('confidenceScore');
        const sourcesSection = document.getElementById('sourcesSection');
        const sourcesList = document.getElementById('sourcesList');
        const nextSteps = document.getElementById('nextSteps');
        const relatedQuestions = document.getElementById('relatedQuestions');
        const practiceSuggestions = document.getElementById('practiceSuggestions');

        // Display confidence score
        const confidence = Math.round((data.metadata.confidence_score || 0) * 100);
        confidenceScore.textContent = confidence;
        
        const confidenceBadge = document.getElementById('confidenceBadge');
        if (confidence >= 80) {
            confidenceBadge.style.background = 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)';
        } else if (confidence >= 60) {
            confidenceBadge.style.background = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
        } else {
            confidenceBadge.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        }

        // Display quick answer with document context
        if (data.answer.quick_answer) {
            const contextInfo = selectedPDF 
                ? '<div class="document-context"><i class="fas fa-file-pdf"></i> Searched in selected document</div>'
                : '<div class="document-context"><i class="fas fa-globe"></i> Searched all documents</div>';
            
            quickAnswer.innerHTML = `
                <h4><i class="fas fa-zap"></i> Quick Answer</h4>
                ${contextInfo}
                <p>${data.answer.quick_answer}</p>
            `;
        }

        // Display detailed explanation
        if (data.answer.detailed_explanation) {
            detailedExplanation.innerHTML = `
                <h4><i class="fas fa-info-circle"></i> Detailed Explanation</h4>
                <div>${this.formatText(data.answer.detailed_explanation)}</div>
            `;
        }

        // Display sources if available
        if (data.sources.primary_sources && data.sources.primary_sources.length > 0) {
            sourcesList.innerHTML = data.sources.primary_sources.map(source => `
                <div class="source-item">
                    <div class="source-title">${source.title}</div>
                    <div class="source-details">Page ${source.page} • Relevance: ${Math.round(source.relevance * 100)}%</div>
                </div>
            `).join('');
            sourcesSection.style.display = 'block';
        }

        // Display next steps
        if (data.next_steps.related_questions && data.next_steps.related_questions.length > 0) {
            relatedQuestions.innerHTML = `
                <h5><i class="fas fa-question"></i> Related Questions</h5>
                ${data.next_steps.related_questions.map(q => 
                    `<div class="suggestion-item" onclick="window.tutorClient.askRelatedQuestion('${q}')">${q}</div>`
                ).join('')}
            `;
        }

        if (data.next_steps.practice_suggestions && data.next_steps.practice_suggestions.length > 0) {
            practiceSuggestions.innerHTML = `
                <h5><i class="fas fa-dumbbell"></i> Practice Suggestions</h5>
                ${data.next_steps.practice_suggestions.map(s => 
                    `<div class="suggestion-item">${s}</div>`
                ).join('')}
            `;
        }

        if (data.next_steps.related_questions.length > 0 || data.next_steps.practice_suggestions.length > 0) {
            nextSteps.style.display = 'block';
        }

        answerSection.style.display = 'block';
        answerSection.classList.add('fade-in');
    }

    askRelatedQuestion(question) {
        const questionInput = document.getElementById('questionInput');
        questionInput.value = question;
        this.askQuestion();
    }

    formatText(text) {
        // Simple text formatting - convert line breaks to HTML
        return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    showError(message) {
        const errorSection = document.getElementById('errorSection');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
        errorSection.classList.add('fade-in');
    }

    hideAllSections() {
        const sections = [
            'analysisSection',
            'answerSection', 
            'errorSection'
        ];
        
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            section.style.display = 'none';
            section.classList.remove('fade-in');
        });
    }

    updateButtons(disabled = false) {
        const askBtn = document.getElementById('askBtn');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        askBtn.disabled = disabled;
        analyzeBtn.disabled = disabled;
        
        if (disabled) {
            askBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        } else {
            askBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Ask Question';
        }
    }

    showSuccess(message) {
        const successSection = document.getElementById('successSection');
        const successMessage = document.getElementById('successMessage');
        
        successMessage.textContent = message;
        successSection.style.display = 'block';
        successSection.classList.add('fade-in');
        
        // Auto-hide success message after 3 seconds
        setTimeout(() => {
            successSection.classList.remove('fade-in');
            setTimeout(() => {
                successSection.style.display = 'none';
            }, 300);
        }, 3000);
    }

    // PDF Upload Methods
    handleFileSelection(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        if (!file.type.includes('pdf')) {
            this.showError('Please select a PDF file.');
            return;
        }
        
        if (file.size > 50 * 1024 * 1024) { // 50MB limit
            this.showError('File size too large. Maximum size is 50MB.');
            return;
        }
        
        // Show upload form
        const uploadForm = document.getElementById('uploadForm');
        uploadForm.style.display = 'block';
        
        // Store selected file
        this.selectedFile = file;
        
        // Update upload button text
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.innerHTML = `<i class="fas fa-upload"></i> Upload "${file.name}"`;
    }

    async uploadPDF() {
        if (!this.selectedFile) {
            this.showError('No file selected.');
            return;
        }

        if (this.isProcessing) return;
        
        this.isProcessing = true;
        
        // Show upload progress
        const uploadForm = document.getElementById('uploadForm');
        const uploadProgress = document.getElementById('uploadProgress');
        uploadForm.style.display = 'none';
        uploadProgress.style.display = 'block';
        
        // Get form data
        const subject = document.getElementById('subjectInput').value.trim();
        const description = document.getElementById('descriptionInput').value.trim();
        
        // Create form data
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        if (subject) formData.append('subject', subject);
        if (description) formData.append('description', description);
        
        try {
            // Simulate progress
            this.updateProgress(25, 'Uploading file...');
            
            const response = await fetch(`${this.baseURL}/api/v1/pdfs/upload`, {
                method: 'POST',
                body: formData
            });

            this.updateProgress(50, 'Processing PDF...');
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.updateProgress(75, 'Extracting text...');
                
                // Simulate final processing time
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                this.updateProgress(100, 'Complete!');
                
                setTimeout(() => {
                    this.showSuccess(`PDF processed successfully! ${data.total_chunks || 0} chunks created.`);
                    this.resetUploadForm();
                    this.loadPDFList(); // Refresh PDF list
                }, 500);
                
            } else {
                throw new Error(data.message || data.detail || 'PDF upload failed');
            }
        } catch (error) {
            console.error('PDF upload failed:', error);
            this.showError(`PDF upload failed: ${error.message}`);
            this.resetUploadForm();
        } finally {
            this.isProcessing = false;
        }
    }

    updateProgress(percentage, text) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = text;
    }

    cancelUpload() {
        this.resetUploadForm();
    }

    resetUploadForm() {
        // Hide forms and progress
        const uploadForm = document.getElementById('uploadForm');
        const uploadProgress = document.getElementById('uploadProgress');
        uploadForm.style.display = 'none';
        uploadProgress.style.display = 'none';
        
        // Clear form data
        document.getElementById('subjectInput').value = '';
        document.getElementById('descriptionInput').value = '';
        document.getElementById('pdfFileInput').value = '';
        
        // Reset progress
        this.updateProgress(0, 'Ready to upload...');
        
        // Clear selected file
        this.selectedFile = null;
        
        // Reset upload button
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Process';
    }

    async loadPDFList() {
        console.log('📋 Loading PDF list...');
        try {
            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${this.baseURL}/api/v1/pdfs`, {
                credentials: 'include', // Include session cookie
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            console.log('📋 PDF list response status:', response.status);
            
            const pdfs = await response.json();
            console.log('📋 PDF list data:', pdfs);
            
            this.displayPDFList(pdfs);
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('⏰ PDF list load timed out');
            } else {
                console.error('Failed to load PDF list:', error);
            }
            // Show empty state if loading fails
            this.displayPDFList([]);
        }
    }

    displayPDFList(pdfs) {
        const pdfList = document.getElementById('pdfList');
        const emptyState = document.getElementById('emptyState');
        
        if (!pdfs || pdfs.length === 0) {
            emptyState.style.display = 'block';
            this.populatePDFSelector([]); // Clear selector
            return;
        }
        
        emptyState.style.display = 'none';
        
        // Populate the PDF list display
        pdfList.innerHTML = pdfs.map(pdf => `
            <div class="pdf-item">
                <div class="pdf-info">
                    <i class="fas fa-file-pdf pdf-icon"></i>
                    <div class="pdf-details">
                        <h4>${pdf.original_filename}</h4>
                        <p>
                            ${pdf.subject || 'No subject'} • 
                            ${pdf.total_chunks || 0} chunks • 
                            ${this.formatFileSize(pdf.file_size)}
                        </p>
                    </div>
                </div>
                <div class="pdf-status status-${pdf.processing_status}">
                    ${pdf.processing_status}
                </div>
                <div class="pdf-actions">
                    <button class="delete-btn" onclick="window.tutorClient.deletePDF('${pdf.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
        // Populate the PDF selector dropdown
        this.populatePDFSelector(pdfs);
    }
    
    populatePDFSelector(pdfs) {
        const pdfSelector = document.getElementById('pdfSelector');
        if (!pdfSelector) return;
        
        // Clear existing options except the first one
        pdfSelector.innerHTML = '<option value="">🌐 Search all documents</option>';
        
        // Add processed PDFs to the selector
        const processedPDFs = pdfs.filter(pdf => pdf.processing_status === 'completed');
        
        processedPDFs.forEach(pdf => {
            const option = document.createElement('option');
            option.value = pdf.id;
            option.textContent = `📄 ${pdf.original_filename}`;
            
            // Add chunk count for user info
            if (pdf.total_chunks > 0) {
                option.textContent += ` (${pdf.total_chunks} chunks)`;
            }
            
            pdfSelector.appendChild(option);
        });
        
        // If no processed PDFs, add a disabled option
        if (processedPDFs.length === 0 && pdfs.length > 0) {
            const option = document.createElement('option');
            option.textContent = '⏳ No processed documents yet';
            option.disabled = true;
            pdfSelector.appendChild(option);
        }
    }

    async deletePDF(pdfId) {
        if (!confirm('Are you sure you want to delete this PDF?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.baseURL}/api/v1/pdfs/${pdfId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showSuccess('PDF deleted successfully.');
                this.loadPDFList(); // Refresh list
                this.loadSystemStats(); // Refresh stats
            } else {
                throw new Error('Failed to delete PDF');
            }
        } catch (error) {
            console.error('Delete failed:', error);
            this.showError('Failed to delete PDF.');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ...existing code...
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.tutorClient = new AITutorApp();
    
    // Add some helpful console messages
    console.log('🎓 AI Tutor Frontend Loaded');
    console.log('💡 Tip: Use Ctrl+Enter in the textarea to quickly ask a question');
});

// Handle network errors gracefully
window.addEventListener('online', () => {
    console.log('✅ Network connection restored');
    if (window.tutorClient) {
        window.tutorClient.checkSystemHealth();
    }
});

window.addEventListener('offline', () => {
    console.log('❌ Network connection lost');
});
