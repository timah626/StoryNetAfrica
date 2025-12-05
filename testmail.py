import smtplib
from email.mime.text import MIMEText
from params import from_email, app_password

to_email = "azohchelsie@gmail.com"  # Your email
subject = "Test Email"
body = "This is a test email from Python. okay now i'm just confirming this works"

msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = from_email
msg['To'] = to_email

try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(from_email, app_password)
        server.send_message(msg)
    print("Email sent successfully!")
except Exception as e:
    print("Failed to send email:", e)




'''import smtplib
from email.mime.text import MIMEText
from params import from_email, app_password

to_email = "azohchelsie@gmail.com"
subject = "Test Email"
body = "This is a test email from Python."

msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = from_email
msg['To'] = to_email

try:
    print("Connecting to Gmail...")
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=20)
    print("Connected! Logging in...")
    server.login(from_email, app_password)
    print("Logged in! Sending email...")
    server.send_message(msg)
    server.quit()
    print("Email sent successfully!")
except Exception as e:
    print("Failed to send email:", e)'''