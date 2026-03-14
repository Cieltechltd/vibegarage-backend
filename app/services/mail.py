import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.templates.welcome import get_welcome_html

def send_welcome_email(user_email: str, user_name: str):
    sender_email = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

   
    message = MIMEMultipart("alternative")
    message["Subject"] = "Welcome to the Vibe Garage family 🎸"
    message["From"] = f"Utee Jacob <{sender_email}>"
    message["To"] = user_email

    
    html_content = get_welcome_html(user_name)
    message.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, user_email, message.as_string())
        print(f"Welcome email sent to {user_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")