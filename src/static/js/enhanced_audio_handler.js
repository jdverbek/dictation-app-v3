/**
 * Enhanced audio recording with proper file handling
 */

class EnhancedAudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordedBlob = null;
        this.isRecording = false;
        this.stream = null;
        this.recordingStartTime = null;
        this.recordingTimer = null;
    }
    
    async startRecording() {
        try {
            console.log('Starting audio recording...');
            
            // Request microphone access with enhanced settings
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100,
                    channelCount: 1
                } 
            });
            
            // Check for WebM support, fallback to other formats
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    mimeType = 'audio/mp4';
                    if (!MediaRecorder.isTypeSupported(mimeType)) {
                        mimeType = 'audio/wav';
                    }
                }
            }
            
            console.log(`Using MIME type: ${mimeType}`);
            
            const options = { mimeType };
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];
            
            // Set up event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    console.log(`Audio chunk received: ${event.data.size} bytes`);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                console.log('Recording stopped, processing audio...');
                this.recordedBlob = new Blob(this.audioChunks, { 
                    type: mimeType 
                });
                this.onRecordingComplete();
            };
            
            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this.showError('Recording error: ' + event.error);
            };
            
            // Start recording with data collection every second
            this.mediaRecorder.start(1000);
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            
            // Start recording timer
            this.startRecordingTimer();
            
            // Update UI
            this.updateRecordingUI(true);
            
            return true;
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showError('Could not start recording: ' + error.message);
            return false;
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            console.log('Stopping recording...');
            
            this.mediaRecorder.stop();
            
            // Stop all tracks
            if (this.stream) {
                this.stream.getTracks().forEach(track => {
                    track.stop();
                    console.log('Audio track stopped');
                });
            }
            
            this.isRecording = false;
            
            // Stop timer
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
            
            // Update UI
            this.updateRecordingUI(false);
        }
    }
    
    startRecordingTimer() {
        const timerElement = document.getElementById('recording-timer');
        if (!timerElement) return;
        
        this.recordingTimer = setInterval(() => {
            const elapsed = Date.now() - this.recordingStartTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        }, 1000);
    }
    
    updateRecordingUI(isRecording) {
        const startBtn = document.getElementById('start-recording');
        const stopBtn = document.getElementById('stop-recording');
        const statusIndicator = document.getElementById('recording-status');
        
        if (startBtn) startBtn.disabled = isRecording;
        if (stopBtn) stopBtn.disabled = !isRecording;
        
        if (statusIndicator) {
            statusIndicator.textContent = isRecording ? '🔴 Recording...' : '⏹️ Ready';
            statusIndicator.className = isRecording ? 'recording-active' : 'recording-ready';
        }
    }
    
    onRecordingComplete() {
        console.log('Processing completed recording...');
        
        // Calculate recording duration
        const duration = Date.now() - this.recordingStartTime;
        const durationSeconds = Math.floor(duration / 1000);
        
        console.log(`Recording duration: ${durationSeconds} seconds`);
        console.log(`Blob size: ${this.recordedBlob.size} bytes`);
        
        // Create download link with timestamp
        const url = URL.createObjectURL(this.recordedBlob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const extension = this.recordedBlob.type.includes('webm') ? 'webm' : 
                         this.recordedBlob.type.includes('mp4') ? 'mp4' : 'wav';
        const filename = `medical_recording_${timestamp}.${extension}`;
        
        // Auto-download
        this.downloadRecording(url, filename);
        
        // Store in session for re-upload
        this.storeRecordingInSession(this.recordedBlob, filename);
        
        // Show upload option
        this.showUploadOption();
        
        // Clean up URL
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    
    downloadRecording(url, filename) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        console.log(`Recording downloaded as: ${filename}`);
        this.showNotification('Recording saved to your device', 'success');
    }
    
    storeRecordingInSession(blob, filename) {
        try {
            // Convert to base64 for session storage
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64 = reader.result;
                const recordingData = {
                    data: base64,
                    filename: filename,
                    timestamp: Date.now(),
                    size: blob.size,
                    type: blob.type
                };
                
                sessionStorage.setItem('lastRecording', JSON.stringify(recordingData));
                console.log('Recording stored in session storage');
            };
            reader.readAsDataURL(blob);
        } catch (error) {
            console.error('Error storing recording in session:', error);
        }
    }
    
    showUploadOption() {
        // Show upload modal
        const modal = document.createElement('div');
        modal.className = 'upload-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>🎤 Recording Complete</h3>
                <p>Your recording has been saved to your device.</p>
                <div class="modal-actions">
                    <button class="btn btn-primary" onclick="audioRecorder.uploadForProcessing()">
                        🚀 Process Recording
                    </button>
                    <button class="btn btn-secondary" onclick="audioRecorder.uploadLater()">
                        📁 Upload Later
                    </button>
                    <button class="btn btn-tertiary" onclick="this.parentElement.parentElement.remove()">
                        ❌ Cancel
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Auto-remove after 30 seconds if no action
        setTimeout(() => {
            if (document.body.contains(modal)) {
                modal.remove();
            }
        }, 30000);
    }
    
    async uploadForProcessing() {
        // Remove any existing modals
        document.querySelectorAll('.upload-modal').forEach(modal => modal.remove());
        
        // Validate patient information
        const patientId = document.getElementById('patient_id')?.value;
        const patientDob = document.getElementById('patient_dob')?.value;
        
        if (!patientId) {
            this.showError('Patient ID is required for processing');
            return;
        }
        
        const formData = new FormData();
        formData.append('audio_file', this.recordedBlob, 'recording.webm');
        formData.append('patient_id', patientId);
        if (patientDob) {
            formData.append('patient_dob', patientDob);
        }
        
        try {
            this.showProcessingModal();
            
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Store job ID for status checking
                sessionStorage.setItem('currentJobId', result.job_id);
                
                // Show processing status
                this.showProcessingStatus(result.job_id);
                
                this.showNotification('Processing started successfully!', 'success');
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.hideProcessingModal();
            this.showError('Upload failed: ' + error.message + '. Your recording has been saved locally.');
        }
    }
    
    uploadLater() {
        // Remove modal
        document.querySelectorAll('.upload-modal').forEach(modal => modal.remove());
        
        this.showNotification('Recording saved. You can upload it later from the file input.', 'info');
        
        // Enable file input for manual upload
        const fileInput = document.getElementById('audio_file');
        if (fileInput) {
            fileInput.style.display = 'block';
        }
    }
    
    showProcessingModal() {
        const modal = document.createElement('div');
        modal.id = 'processing-modal';
        modal.className = 'processing-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>🔄 Processing Recording</h3>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <p class="status-text" id="status-text">Uploading audio...</p>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-secondary" onclick="audioRecorder.continueInBackground()">
                        📱 Continue in Background
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    hideProcessingModal() {
        const modal = document.getElementById('processing-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    showProcessingStatus(jobId) {
        // Update modal with job ID
        const modal = document.getElementById('processing-modal');
        if (modal) {
            const content = modal.querySelector('.modal-content');
            content.innerHTML = `
                <h3>🔄 Processing Recording</h3>
                <p><strong>Job ID:</strong> ${jobId}</p>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <p class="status-text" id="status-text">Starting transcription...</p>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-primary" onclick="window.location.href='/review/${jobId}'">
                        📄 Go to Review Page
                    </button>
                    <button class="btn btn-secondary" onclick="audioRecorder.continueInBackground()">
                        📱 Continue in Background
                    </button>
                </div>
            `;
        }
        
        // Start status polling
        this.pollJobStatus(jobId);
    }
    
    async pollJobStatus(jobId) {
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/job/status/${jobId}`);
                const status = await response.json();
                
                // Update UI
                const statusText = document.getElementById('status-text');
                const progressFill = document.getElementById('progress-fill');
                
                if (statusText) {
                    statusText.textContent = status.message || 'Processing...';
                }
                
                if (progressFill) {
                    const progress = status.progress || 0;
                    progressFill.style.width = `${progress}%`;
                }
                
                if (status.status === 'completed') {
                    // Show completion notification
                    this.showNotification('Processing complete! 🎉', 'success');
                    
                    // Update modal
                    if (statusText) {
                        statusText.textContent = 'Processing completed successfully!';
                    }
                    if (progressFill) {
                        progressFill.style.width = '100%';
                    }
                    
                    // Stop polling
                    return true;
                } else if (status.status === 'failed') {
                    this.showNotification('Processing failed ❌', 'error');
                    if (statusText) {
                        statusText.textContent = 'Processing failed. Please try again.';
                    }
                    return true;
                }
                
                return false;
            } catch (error) {
                console.error('Status check error:', error);
                return false;
            }
        };
        
        // Initial check
        await checkStatus();
        
        // Poll every 2 seconds
        const pollInterval = setInterval(async () => {
            const isDone = await checkStatus();
            if (isDone) {
                clearInterval(pollInterval);
            }
        }, 2000);
        
        // Stop polling after 10 minutes
        setTimeout(() => {
            clearInterval(pollInterval);
        }, 600000);
    }
    
    continueInBackground() {
        this.hideProcessingModal();
        this.showNotification('Processing continues in background. Check back later!', 'info');
    }
    
    showNotification(message, type = 'info') {
        // Remove existing notifications
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(notification)) {
                notification.remove();
            }
        }, 5000);
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    // Method to handle file input uploads
    handleFileUpload(fileInput) {
        const file = fileInput.files[0];
        if (!file) return;
        
        console.log(`File selected: ${file.name}, size: ${file.size} bytes`);
        
        // Validate file type
        const validTypes = ['audio/webm', 'audio/mp4', 'audio/wav', 'audio/mpeg', 'audio/ogg'];
        if (!validTypes.includes(file.type)) {
            this.showError('Please select a valid audio file (WebM, MP4, WAV, MP3, or OGG)');
            return;
        }
        
        // Validate file size (max 50MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showError('File too large. Maximum size is 50MB.');
            return;
        }
        
        // Store the file for upload
        this.recordedBlob = file;
        
        // Show upload option
        this.showUploadOption();
    }
    
    // Method to restore recording from session storage
    restoreFromSession() {
        try {
            const recordingData = sessionStorage.getItem('lastRecording');
            if (!recordingData) return false;
            
            const data = JSON.parse(recordingData);
            
            // Check if recording is recent (within 24 hours)
            const age = Date.now() - data.timestamp;
            if (age > 24 * 60 * 60 * 1000) {
                sessionStorage.removeItem('lastRecording');
                return false;
            }
            
            // Convert base64 back to blob
            fetch(data.data)
                .then(res => res.blob())
                .then(blob => {
                    this.recordedBlob = blob;
                    this.showNotification('Previous recording restored from session', 'info');
                    this.showUploadOption();
                });
            
            return true;
        } catch (error) {
            console.error('Error restoring from session:', error);
            sessionStorage.removeItem('lastRecording');
            return false;
        }
    }
    
    // Initialize the recorder when page loads
    init() {
        console.log('Initializing Enhanced Audio Recorder...');
        
        // Check for previous recording in session
        this.restoreFromSession();
        
        // Set up file input handler
        const fileInput = document.getElementById('audio_file');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e.target);
            });
        }
        
        // Set up recording buttons
        const startBtn = document.getElementById('start-recording');
        const stopBtn = document.getElementById('stop-recording');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startRecording());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopRecording());
        }
        
        console.log('Enhanced Audio Recorder initialized successfully');
    }
}

// Global instance
let audioRecorder;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    audioRecorder = new EnhancedAudioRecorder();
    audioRecorder.init();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedAudioRecorder;
}

