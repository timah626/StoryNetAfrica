// static/js/otp.js

function loadOTPComponent(loginCard) {
    // Fetch the otp.html file
    fetch("{{ url_for('static', filename='components/otp.html') }}")
        .then(response => response.text())
        .then(html => {
            // Insert the OTP HTML into the login card
            loginCard.innerHTML = html;

            // Add event listeners after loading
            document.querySelector('.btn-verify').addEventListener('click', verifyOTP);
            document.querySelector('.btn-back').addEventListener('click', backToLogin);
            document.querySelector('.resend-link').addEventListener('click', resendOTP);
        });
}

function verifyOTP() {
    const otp = document.querySelector('.otp-input').value;
    if(otp.length === 6) {
        alert('OTP Verified!');
        // Send to backend here
    } else {
        alert('Please enter a 6-digit OTP');
    }
}

function backToLogin() {
    location.reload();
}

function resendOTP(e) {
    e.preventDefault();
    alert('OTP resent to your email');
}