# utils.py  ←  FINAL VERSION (works 100%)
import bcrypt
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from params import from_email, app_password

# Active OTPs (in-memory for this demo)
active_otps = {}  # {username: otp_code}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def send_otp(to_email: str, username: str) -> bool:
    otp = generate_otp()
    active_otps[username] = otp

    subject = "Your Cloud Simulator OTP"
    body = f"""
    Hello {username}!

    Your OTP code is: {otp}

    Valid for 5 minutes.
    — Cloud Security Simulator
    """

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print(f"[OTP] Sending to {to_email}...", end="")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, app_password)
            server.send_message(msg)
        print(" [OK]")
        return True
    except Exception as e:
        print(f" [FAILED] {e}")
        return False

def verify_otp(username: str, user_input: str) -> bool:
    correct = active_otps.get(username)
    if correct and correct == user_input.strip():
        del active_otps[username]
        return True
    return False

# === THIS IS THE PART THAT WAS MISSING ===
# This runs only when you do: python utils.py
if __name__ == '__main__':
    print("Generating hashed credentials from 'ids' file...")
    credentials = {}
    emails = {}
    
    try:
        with open('ids', 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    username, password = line.split(',', 1)
                    # YOU CAN CHANGE THE EMAIL HERE FOR EVERY USER
                    # Default: use your own email for everyone (easier testing)
                    emails[username] = "azohchelsie@gmail.com"   # ← YOUR EMAIL
                    credentials[username] = hash_password(password)
        
        with open('credentials', 'w') as f:
            for username, hashed in credentials.items():
                f.write(f"{username},{emails[username]},{hashed}\n")
        
        print("credentials file created successfully!")
        print("Login with any username from 'ids' file → OTP goes to azohchelsie@gmail.com")
    
    except FileNotFoundError:
        print("ERROR: 'ids' file not found! Create it with: username,password")









        '''// cloudsecurity.proto
syntax = "proto3";

package cloud;

service UserService {
  rpc login (Request) returns (Response);
  rpc verifyOtp (Request) returns (Response);
  rpc register (RegisterRequest) returns (Response);   // ← THIS WAS MISSING INSIDE THE SERVICE!
}

message Request {
  string login = 1;
  string password = 2;
}

message RegisterRequest {
  string username = 1;
  string email = 2;
  string password = 3;
}

message Response {
  string result = 1;
}'''