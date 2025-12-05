// Login functionality
let resendTimer = 0;

async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const messageBox = document.getElementById('messageBox');
    
    if (!username || !password) {
        showMessage('Please enter username and password', 'error');
        return;
    }
    
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing in...';
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showMessage('OTP sent! Loading verification...', 'success');
            setTimeout(() => {
                showOTPComponent();
            }, 1000);
        } else {
            showMessage(data.error || 'Login failed', 'error');
            loginBtn.disabled = false;
            loginBtn.textContent = 'Sign In';
        }
    } catch (error) {
        showMessage('Network error: ' + error.message, 'error');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
    }
}

function showOTPComponent() {
    const loginCard = document.getElementById('loginCard');
    
    loginCard.innerHTML = `
        <div class="otp-container">
            <div class="otp-icon">✓</div>
            <h2>OTP Sent</h2>
            <p>Check your email for the verification code</p>
            
            <div id="otpMessageBox" style="display:none; padding:12px 15px; margin-bottom:20px; border-radius:8px; font-size:14px; text-align:center;"></div>
            
            <div class="otp-input-group">
                <input type="text" class="otp-input" id="otpInput" placeholder="Enter OTP" maxlength="6" inputmode="numeric">
                <button type="button" class="btn-verify" id="verifyBtn" onclick="handleVerifyOTP()">Verify</button>
            </div>
            <p class="resend-text">Didn't receive? <a href="#" class="resend-link" id="resendLink" onclick="handleResend(event)">Resend OTP</a></p>
            <button type="button" class="btn-back" onclick="handleBackToLogin()">Back to Login</button>
        </div>
    `;
    
    const otpInput = document.getElementById('otpInput');
    otpInput.addEventListener('input', function(e) {
        this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6);
    });

    otpInput.addEventListener('input', function() {
        if (this.value.length === 6) {
            handleVerifyOTP();
        }
    });

    otpInput.focus();
}

async function handleVerifyOTP() {
    const otp = document.getElementById('otpInput').value.trim();
    const verifyBtn = document.getElementById('verifyBtn');
    
    if (!otp || otp.length !== 6) {
        showOTPMessage('Please enter a 6-digit OTP', 'error');
        return;
    }
    
    verifyBtn.disabled = true;
    verifyBtn.textContent = 'Verifying...';
    
    try {
        const response = await fetch('/verify-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                otp: otp
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showOTPMessage('Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            showOTPMessage(data.error || 'Invalid OTP', 'error');
            verifyBtn.disabled = false;
            verifyBtn.textContent = 'Verify';
        }
    } catch (error) {
        showOTPMessage('Network error: ' + error.message, 'error');
        verifyBtn.disabled = false;
        verifyBtn.textContent = 'Verify';
    }
}

async function handleResend(event) {
    event.preventDefault();
    
    if (resendTimer > 0) {
        showOTPMessage(`Please wait ${resendTimer}s before resending`, 'error');
        return;
    }
    
    const resendLink = document.getElementById('resendLink');
    resendLink.style.pointerEvents = 'none';
    resendLink.style.opacity = '0.5';
    
    try {
        const response = await fetch('/resend-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showOTPMessage('OTP resent to your email', 'success');
            startResendTimer();
        } else {
            showOTPMessage(data.error || 'Failed to resend OTP', 'error');
            resendLink.style.pointerEvents = 'auto';
            resendLink.style.opacity = '1';
        }
    } catch (error) {
        showOTPMessage('Network error: ' + error.message, 'error');
        resendLink.style.pointerEvents = 'auto';
        resendLink.style.opacity = '1';
    }
}

function startResendTimer() {
    resendTimer = 60;
    const resendLink = document.getElementById('resendLink');
    
    const interval = setInterval(() => {
        resendTimer--;
        resendLink.textContent = `Resend OTP (${resendTimer}s)`;
        
        if (resendTimer === 0) {
            clearInterval(interval);
            resendLink.textContent = 'Resend OTP';
            resendLink.style.pointerEvents = 'auto';
            resendLink.style.opacity = '1';
        }
    }, 1000);
}

function handleBackToLogin() {
    if (confirm('Go back to login?')) {
        location.reload();
    }
}

function showMessage(message, type) {
    const messageBox = document.getElementById('messageBox');
    messageBox.textContent = message;
    messageBox.style.display = 'block';
    
    if (type === 'error') {
        messageBox.style.background = '#fee';
        messageBox.style.color = '#c33';
        messageBox.style.border = '1px solid #fcc';
    } else {
        messageBox.style.background = '#efe';
        messageBox.style.color = '#3c3';
        messageBox.style.border = '1px solid #cfc';
    }
}

function showOTPMessage(message, type) {
    const messageBox = document.getElementById('otpMessageBox');
    if (!messageBox) return;
    
    messageBox.textContent = message;
    messageBox.style.display = 'block';
    
    if (type === 'error') {
        messageBox.style.background = '#fee';
        messageBox.style.color = '#c33';
        messageBox.style.border = '1px solid #fcc';
    } else {
        messageBox.style.background = '#efe';
        messageBox.style.color = '#3c3';
        messageBox.style.border = '1px solid #cfc';
    }
}