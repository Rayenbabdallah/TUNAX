"""
Email notification utilities for TUNAX system.
Sends emails via Flask-Mail for important events.
"""

from flask import current_app
from flask_mail import Message
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_email(recipient_email: str, subject: str, body_text: str, body_html: str = None):
    """
    Send an email via Flask-Mail.
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject line
        body_text: Plain text body
        body_html: Optional HTML body
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body_text,
            html=body_html
        )
        current_app.mail.send(msg)
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False


def send_tax_declaration_confirmation(user_email: str, user_name: str, tax_id: str, 
                                      property_address: str, tax_amount: float):
    """Send confirmation email when tax is declared."""
    subject = "Déclaration fiscale enregistrée - TUNAX"
    
    body_text = f"""
Bonjour {user_name},

Votre déclaration fiscale a été enregistrée avec succès.

Détails:
- ID Déclaration: {tax_id}
- Adresse: {property_address}
- Montant: {tax_amount:.2f} DT
- Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Accédez à votre compte pour consulter le statut et effectuer le paiement.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Votre déclaration fiscale a été enregistrée avec succès.</p>
        <h3>Détails:</h3>
        <ul>
            <li><strong>ID Déclaration:</strong> {tax_id}</li>
            <li><strong>Adresse:</strong> {property_address}</li>
            <li><strong>Montant:</strong> {tax_amount:.2f} DT</li>
            <li><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        <p>Accédez à votre compte pour consulter le statut et effectuer le paiement.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)


def send_payment_confirmation(user_email: str, user_name: str, payment_id: str,
                             amount: float, tax_id: str, reference_number: str):
    """Send confirmation email when payment is recorded."""
    subject = "Paiement confirmé - TUNAX"
    
    body_text = f"""
Bonjour {user_name},

Votre paiement a été confirmé avec succès.

Détails du paiement:
- ID Paiement: {payment_id}
- Montant: {amount:.2f} DT
- Déclaration: {tax_id}
- Numéro de référence: {reference_number}
- Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Un reçu est disponible sur votre compte.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Votre paiement a été confirmé avec succès.</p>
        <h3>Détails du paiement:</h3>
        <ul>
            <li><strong>ID Paiement:</strong> {payment_id}</li>
            <li><strong>Montant:</strong> {amount:.2f} DT</li>
            <li><strong>Déclaration:</strong> {tax_id}</li>
            <li><strong>Numéro de référence:</strong> {reference_number}</li>
            <li><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        <p>Un reçu est disponible sur votre compte.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)


def send_permit_decision_notification(user_email: str, user_name: str, permit_id: str,
                                     status: str, reason: str = None):
    """Send email when permit decision is made."""
    status_fr = "Approuvé" if status == "approved" else "Rejeté" if status == "rejected" else status
    
    subject = f"Décision de permis - {status_fr} - TUNAX"
    
    reason_text = f"\nMotif: {reason}" if reason else ""
    reason_html = f"<p><strong>Motif:</strong> {reason}</p>" if reason else ""
    
    body_text = f"""
Bonjour {user_name},

Votre demande de permis a été examinée.

Détails:
- ID Permis: {permit_id}
- Statut: {status_fr}
- Date de décision: {datetime.now().strftime('%d/%m/%Y %H:%M')}{reason_text}

Accédez à votre compte pour consulter les détails complets.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Votre demande de permis a été examinée.</p>
        <h3>Détails:</h3>
        <ul>
            <li><strong>ID Permis:</strong> {permit_id}</li>
            <li><strong>Statut:</strong> {status_fr}</li>
            <li><strong>Date de décision:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        {reason_html}
        <p>Accédez à votre compte pour consulter les détails complets.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)


def send_dispute_resolution_notification(user_email: str, user_name: str, dispute_id: str,
                                        resolution_status: str, notes: str = None):
    """Send email when dispute is resolved."""
    status_fr = "Approuvée" if resolution_status == "approved" else "Rejetée" if resolution_status == "rejected" else resolution_status
    
    subject = f"Recours sur contestation - {status_fr} - TUNAX"
    
    notes_html = f"<p><strong>Remarques:</strong> {notes}</p>" if notes else ""
    
    body_text = f"""
Bonjour {user_name},

Votre contestation a été examinée par l'administration.

Détails:
- ID Contestation: {dispute_id}
- Résolution: {status_fr}
- Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Accédez à votre compte pour consulter le détail de la décision.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Votre contestation a été examinée par l'administration.</p>
        <h3>Détails:</h3>
        <ul>
            <li><strong>ID Contestation:</strong> {dispute_id}</li>
            <li><strong>Résolution:</strong> {status_fr}</li>
            <li><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        {notes_html}
        <p>Accédez à votre compte pour consulter le détail de la décision.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)


def send_payment_reminder(user_email: str, user_name: str, tax_id: str,
                         amount_due: float, due_date: str):
    """Send reminder email for upcoming payment deadline."""
    subject = "Rappel - Paiement en attente - TUNAX"
    
    body_text = f"""
Bonjour {user_name},

Vous avez un paiement en attente pour votre déclaration fiscale.

Détails:
- ID Déclaration: {tax_id}
- Montant dû: {amount_due:.2f} DT
- Date d'échéance: {due_date}

Veuillez effectuer le paiement avant la date d'échéance pour éviter les pénalités.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Vous avez un paiement en attente pour votre déclaration fiscale.</p>
        <h3>Détails:</h3>
        <ul>
            <li><strong>ID Déclaration:</strong> {tax_id}</li>
            <li><strong>Montant dû:</strong> {amount_due:.2f} DT</li>
            <li><strong>Date d'échéance:</strong> {due_date}</li>
        </ul>
        <p>Veuillez effectuer le paiement avant la date d'échéance pour éviter les pénalités.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)


def send_penalty_notification(user_email: str, user_name: str, tax_id: str,
                             penalty_amount: float, reason: str):
    """Send notification email when penalty is applied."""
    subject = "Notification - Pénalité appliquée - TUNAX"
    
    body_text = f"""
Bonjour {user_name},

Une pénalité a été appliquée à votre déclaration fiscale.

Détails:
- ID Déclaration: {tax_id}
- Montant de pénalité: {penalty_amount:.2f} DT
- Motif: {reason}
- Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Le montant total à payer a été augmenté. Consultez votre compte pour voir le nouveau montant.

Cordialement,
Système TUNAX
"""
    
    body_html = f"""
<html>
    <body>
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>Une pénalité a été appliquée à votre déclaration fiscale.</p>
        <h3>Détails:</h3>
        <ul>
            <li><strong>ID Déclaration:</strong> {tax_id}</li>
            <li><strong>Montant de pénalité:</strong> {penalty_amount:.2f} DT</li>
            <li><strong>Motif:</strong> {reason}</li>
            <li><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
        </ul>
        <p>Le montant total à payer a été augmenté. Consultez votre compte pour voir le nouveau montant.</p>
        <p>Cordialement,<br><strong>Système TUNAX</strong></p>
    </body>
</html>
"""
    
    return send_email(user_email, subject, body_text, body_html)
