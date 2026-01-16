# TUNAX Email Notification Configuration

## Overview

The TUNAX system now sends automated email notifications for key events:
- Tax declarations (TIB/TTNB)
- Payment confirmations
- Permit decisions (approved/rejected)
- Dispute resolutions

## Configuration

### Environment Variables

Set these in your `.env` file or Docker environment:

```bash
# SMTP Server Configuration
MAIL_SERVER=smtp.gmail.com           # SMTP server hostname
MAIL_PORT=587                        # SMTP port (587 for TLS, 465 for SSL)
MAIL_USE_TLS=True                    # Enable TLS encryption
MAIL_USERNAME=your-email@gmail.com   # Email account username
MAIL_PASSWORD=your-app-password      # Email account password or app-specific password
MAIL_DEFAULT_SENDER=noreply@tunax.gov.tn  # Sender email address
```

### Using Gmail

1. **Enable "Less secure app access"** or use **App Passwords**:
   - For personal Gmail: [Account Security Settings](https://myaccount.google.com/security)
   - Generate an App Password: [App Passwords](https://myaccount.google.com/apppasswords)

2. **Update .env**:
   ```bash
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=tunax-notifications@gmail.com
   MAIL_PASSWORD=your-16-digit-app-password
   MAIL_DEFAULT_SENDER=noreply@tunax.gov.tn
   ```

### Using Other SMTP Services

**SendGrid:**
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.your-api-key
MAIL_DEFAULT_SENDER=noreply@tunax.gov.tn
```

**AWS SES:**
```bash
MAIL_SERVER=email-smtp.region.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-ses-username
MAIL_PASSWORD=your-ses-password
MAIL_DEFAULT_SENDER=noreply@tunax.gov.tn
```

## Email Events

### 1. Tax Declaration Confirmation
**When:** User declares a property (TIB) or land (TTNB)
**Recipients:** User's registered email
**Content:** Tax ID, address, declared amount, calculation details

**Files Involved:**
- `backend/resources/tib.py` - TIB property declarations
- `backend/resources/ttnb.py` - TTNB land declarations
- `backend/utils/email_notifier.py` - `send_tax_declaration_confirmation()`

### 2. Payment Confirmation
**When:** User makes a tax payment
**Recipients:** User's registered email
**Content:** Payment ID, amount, tax reference, payment date

**Files Involved:**
- `backend/resources/payment.py` - Payment processing
- `backend/utils/email_notifier.py` - `send_payment_confirmation()`

### 3. Permit Decision Notification
**When:** Municipality approves or rejects a permit request
**Recipients:** Permit requester's email
**Content:** Permit ID, decision status, decision reason (if provided)

**Files Involved:**
- `backend/resources/permits.py` - Permit decision endpoint
- `backend/utils/email_notifier.py` - `send_permit_decision_notification()`

### 4. Dispute Resolution Notification
**When:** Administrative officer finalizes dispute resolution
**Recipients:** Claimant's email
**Content:** Dispute ID, resolution status, decision notes (if provided)

**Files Involved:**
- `backend/resources/dispute.py` - Dispute decision endpoint
- `backend/utils/email_notifier.py` - `send_dispute_resolution_notification()`

### 5. Payment Reminder (Optional)
**When:** Scheduled task runs (requires implementation)
**Recipients:** Users with unpaid taxes
**Content:** Due date, amount due, tax declaration ID

**Implementation:** `backend/utils/email_notifier.py` - `send_payment_reminder()`

### 6. Penalty Notification (Optional)
**When:** Late payment penalty applied to tax
**Recipients:** User's registered email
**Content:** Penalty amount, reason, new total due

**Implementation:** `backend/utils/email_notifier.py` - `send_penalty_notification()`

## Implementation Details

### Email Module: `backend/utils/email_notifier.py`

Main function:
```python
send_email(recipient_email: str, subject: str, body_text: str, body_html: str = None) -> bool
```

Specialized functions for each event type:
- `send_tax_declaration_confirmation()`
- `send_payment_confirmation()`
- `send_permit_decision_notification()`
- `send_dispute_resolution_notification()`
- `send_payment_reminder()`
- `send_penalty_notification()`

**Features:**
- French-language email templates
- Plain text + HTML alternative bodies
- Error logging (doesn't block user transactions)
- Graceful fallback if mail service unavailable

### Flask-Mail Integration

Added to `backend/app.py`:
```python
from flask_mail import Mail

# Mail configuration from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@tunax.gov.tn')

mail = Mail(app)
app.mail = mail  # Store for access in utilities
```

## Testing

### Without Real SMTP

For development, emails can be logged instead of sent:

```python
# In backend/utils/email_notifier.py
import logging
logger = logging.getLogger(__name__)

# Emails will be logged to: backend/logs/app.log
```

Check logs:
```bash
docker-compose exec backend tail -f logs/app.log | grep "Email sent"
```

### With Real SMTP

1. Set environment variables in `docker-compose.yml`:
   ```yaml
   environment:
     MAIL_SERVER: smtp.gmail.com
     MAIL_PORT: 587
     MAIL_USE_TLS: "True"
     MAIL_USERNAME: your-email@gmail.com
     MAIL_PASSWORD: your-app-password
     MAIL_DEFAULT_SENDER: noreply@tunax.gov.tn
   ```

2. Restart containers:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

3. Trigger an event (e.g., create a tax declaration)

4. Check user's email inbox

## Troubleshooting

### Emails not sending

**Check logs:**
```bash
docker-compose exec backend tail -f logs/app.log | grep -i mail
```

**Common issues:**
- `SMTPAuthenticationError`: Wrong username/password
- `SMTPNotSupportedError`: TLS not available on port
- `ConnectionRefusedError`: SMTP server unreachable
- Empty `MAIL_USERNAME` or `MAIL_PASSWORD`

### Gmail authentication fails

- **Ensure App Password used**, not regular password
- **Allow "Less secure apps"** if using regular password
- **Check 2FA enabled** for account

### Email formatting issues

Edit templates in `backend/utils/email_notifier.py`:
- `body_text` - Plain text version
- `body_html` - HTML version with formatting

## Database Tracking

Email sends are logged automatically through audit logging:
- Table: `audit_logs`
- Entity: Various (Tax, Payment, Permit, Dispute)
- Action: `create`, `update`
- Includes timestamps and user IDs

## Future Enhancements

1. **Email Templates:** Use Jinja2 for template rendering
2. **Attachments:** Send PDF receipts/attestations directly
3. **Scheduled Reminders:** Celery tasks for payment due date reminders
4. **Unsubscribe:** Add email preference management
5. **Bounce Handling:** Track invalid/bounced email addresses
6. **Rate Limiting:** Prevent duplicate emails in short timeframes
7. **Localization:** Support multiple languages (French, Arabic, English)

## Dependencies

Added to `backend/requirements.txt`:
- `Flask-Mail==0.9.1`

Install:
```bash
pip install Flask-Mail==0.9.1
```

Or in Docker:
```bash
docker-compose exec backend pip install Flask-Mail==0.9.1
```
