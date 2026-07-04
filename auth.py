import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from database import create_verification_token, verify_token

# Email configuration (set these environment variables in production)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'your_email@gmail.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'your_password')

def send_verification_email(user_email, verification_token):
    """Send email verification link to user"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Verify Your Email - Placement Portal'
        msg['From'] = SMTP_USERNAME
        msg['To'] = user_email

        # HTML body
        html = f"""
        <html>
        <body>
            <h2>Welcome to Placement Portal!</h2>
            <p>Please click the link below to verify your email address:</p>
            <a href="http://localhost:5000/verify_email/{verification_token}">Verify Email</a>
            <p>If you didn't register, you can ignore this email.</p>
        </body>
        </html>
        """

        part = MIMEText(html, 'html')
        msg.attach(part)

        # For demo, just print instead of sending
        print(f"Sending verification email to {user_email} with token {verification_token}")
        # Uncomment below for actual email sending
        # server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        # server.starttls()
        # server.login(SMTP_USERNAME, SMTP_PASSWORD)
        # server.sendmail(SMTP_USERNAME, user_email, msg.as_string())
        # server.quit()

        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def create_email_verification_token(user_id):
    """Create and return verification token for email"""
    token = secrets.token_urlsafe(32)
    create_verification_token(user_id, token, 'email')
    return token

def verify_email_token(token):
    """Verify email token and return user_id if valid"""
    return verify_token(token, 'email')

# JWT Functions
import jwt
from datetime import datetime, timedelta
import hashlib

JWT_SECRET = os.getenv('JWT_SECRET', 'your_jwt_secret_key')

def create_jwt_token(user_id, role):
    """Create JWT token for user"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.now()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    # Store token hash in db for invalidation
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    from database import create_session
    create_session(user_id, token_hash)
    return token

def verify_jwt_token(token):
    """Verify JWT token and return payload if valid"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # Check if token is in db
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        from database import validate_session
        user_id = validate_session(token_hash)
        if user_id:
            return payload
    except jwt.ExpiredSignatureError:
        pass
    except jwt.InvalidTokenError:
        pass
    return None

def invalidate_jwt_token(token):
    """Invalidate JWT token"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    from database import invalidate_session
    invalidate_session(token_hash)