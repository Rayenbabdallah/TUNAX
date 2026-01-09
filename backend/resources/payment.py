"""Payment management routes (flask-smorest)"""
from flask import jsonify
from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required, get_jwt
from utils.jwt_helpers import get_current_user_id
from extensions.db import db
from models.user import User, UserRole
from models.tax import Tax, TaxStatus
from models.payment import Payment, PaymentStatus, PaymentMethod
from models.permit import Permit, PermitStatus
from schemas.tax_permit import PaymentCreateSchema, PaymentSchema, AttestationSchema, PermitStatusSchema
from utils.role_required import citizen_or_business_required, finance_required, municipality_required
from utils.validators import ErrorMessages
from utils.calculator import TaxCalculator
from datetime import datetime, date
import secrets

blp = Blueprint('payment', 'payment', url_prefix='/api/v1/payments')

@blp.post('/pay')
@jwt_required()
@citizen_or_business_required
@blp.arguments(PaymentCreateSchema)
@blp.response(201, PaymentSchema)
def make_payment(data):
    """Make tax payment for property or land tax
    
    Process a tax payment for either TIB (property) or TTNB (land) tax.
    Generates a payment reference number and marks the tax as paid upon successful completion.
    
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - tax_id
            - amount
            - method
          properties:
            tax_id:
              type: integer
              description: ID of the tax to pay
            amount:
              type: number
              format: float
              description: Payment amount in TND
            method:
              type: string
              enum: [card, bank_transfer, cash, e_dinar]
              description: Payment method
    responses:
      201:
        description: Payment processed successfully
        schema:
          type: object
          properties:
            message:
              type: string
            payment_id:
              type: integer
            reference_number:
              type: string
              description: Unique payment reference (REF-XXXXXXXX)
            amount:
              type: number
            status:
              type: string
              description: Payment status (completed)
      400:
        description: Tax already paid
      403:
        description: User does not own the taxed property/land
      404:
        description: Tax not found
    """
    user_id = get_current_user_id()
    
    # Get tax
    tax = Tax.query.get(data['tax_id'])
    
    if not tax:
        return jsonify({'error': ErrorMessages.NOT_FOUND}), 404
    
    # Verify ownership
    if tax.property and tax.property.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    if tax.land and tax.land.owner_id != user_id:
        return jsonify({'error': ErrorMessages.ACCESS_DENIED}), 403
    
    # Check if already paid
    if tax.status == TaxStatus.PAID:
        return jsonify({'error': 'Tax already paid'}), 400

    # Enforce payable window: payments open Jan 1 of (tax_year + 1)
    start_date = date(int(tax.tax_year) + 1, 1, 1)
    today = date.today()
    if today < start_date:
      return jsonify({
        'error': f'Payments for {tax.tax_year} taxes open on {start_date.isoformat()}',
        'payable_from': start_date.isoformat()
      }), 400
    
    # Simulate payment (in real system, use payment gateway)
    payment = Payment(
        user_id=user_id,
        tax_id=tax.id,
        amount=data['amount'],
        method=data['method'],
        status=PaymentStatus.COMPLETED,
        reference_number=f"REF-{secrets.token_hex(8).upper()}"
    )
    
    # Update tax status
    tax.status = TaxStatus.PAID
    
    db.session.add(payment)
    db.session.commit()
    
    from utils.hateoas import HATEOASBuilder
    
    response = {
        'message': 'Payment recorded successfully',
        'payment_id': payment.id,
        'reference_number': payment.reference_number,
        'amount': payment.amount,
      'status': payment.status.value,
      '_links': HATEOASBuilder.add_payment_links(payment)
    }
    
    return jsonify(response), 201

@blp.get('/attestation/<int:user_id>')
@jwt_required()
@finance_required
def get_attestation(user_id):
    """Get or issue payment attestation (non-debt certificate)
    
    Generate a tax payment attestation certifying that a citizen or business has no outstanding
    tax debts. Required for various administrative procedures. Only issued if all taxes are paid.
    
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID of the user requesting attestation
    responses:
      200:
        description: Attestation issued (all taxes paid)
        schema:
          type: object
          properties:
            attestation_number:
              type: string
              description: Unique attestation number (ATT-XXXXXX)
            user_id:
              type: integer
            issued_date:
              type: string
              format: date-time
            status:
              type: string
              description: Payment status (all_taxes_paid)
            message:
              type: string
      400:
        description: Cannot issue attestation (unpaid taxes exist)
        schema:
          type: object
          properties:
            error:
              type: string
            unpaid_count:
              type: integer
              description: Number of unpaid taxes
            total_due:
              type: number
              description: Total amount owed in TND
    """
    # Check if user has unpaid taxes
    taxes = Tax.query.filter(
        Tax.property.has(owner_id=user_id) | Tax.land.has(owner_id=user_id)
    ).all()
    # Refresh penalties for user's unpaid taxes
    any_updates = False
    for t in taxes:
      if t.status != TaxStatus.PAID:
        section = 'TIB' if getattr(t.tax_type, 'name', 'TIB') == 'TIB' else 'TTNB'
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
          tax_amount=t.tax_amount,
          tax_year=t.tax_year,
          section=section
        )
        if (t.penalty_amount or 0.0) != new_penalty or (t.total_amount or 0.0) != (t.tax_amount + new_penalty):
          t.penalty_amount = new_penalty
          t.total_amount = t.tax_amount + new_penalty
          any_updates = True
    if any_updates:
      db.session.commit()

    unpaid = [t for t in taxes if t.status != TaxStatus.PAID]
    
    if unpaid:
        return jsonify({
            'error': ErrorMessages.UNPAID_TAXES,
            'unpaid_count': len(unpaid),
            'total_due': sum(t.total_amount for t in unpaid)
        }), 400
    
    # Generate attestation
    attestation_number = f"ATT-{secrets.token_hex(6).upper()}"
    
    return jsonify({
        'attestation_number': attestation_number,
        'user_id': user_id,
        'issued_date': datetime.utcnow().isoformat(),
        'status': 'all_taxes_paid',
        'message': 'User has paid all tax obligations'
    }), 200

@blp.get('/my-payments')
@jwt_required()
@citizen_or_business_required
def get_my_payments():
    """Get user's payment history
    
    Retrieve complete payment history for the authenticated user,
    including all tax payments with reference numbers and dates.
    
    ---
    responses:
      200:
        description: Payment history retrieved successfully
        schema:
          type: object
          properties:
            user_id:
              type: integer
            payments:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  tax_id:
                    type: integer
                  amount:
                    type: number
                    format: float
                  method:
                    type: string
                    enum: [card, bank_transfer, cash, e_dinar]
                  status:
                    type: string
                  reference_number:
                    type: string
                  payment_date:
                    type: string
                    format: date-time
    """
    user_id = get_current_user_id()
    
    payments = Payment.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'user_id': user_id,
        'payments': [{
            'id': p.id,
            'tax_id': p.tax_id,
            'amount': p.amount,
            'method': p.method.value,
            'status': p.status.value,
            'reference_number': p.reference_number,
            'payment_date': p.payment_date.isoformat() if p.payment_date else None
        } for p in payments]
    }), 200

@blp.get('/receipt/<int:payment_id>')
@jwt_required()
def get_payment_receipt(payment_id):
    """Download PDF receipt for a payment
    
    Generate and download a PDF receipt for a completed payment.
    Users can only download their own receipts unless they are admin/finance.
    
    ---
    parameters:
      - name: payment_id
        in: path
        type: integer
        required: true
        description: ID of the payment
    produces:
      - application/pdf
    responses:
      200:
        description: PDF receipt file
        schema:
          type: file
      403:
        description: Unauthorized access to receipt
      404:
        description: Payment not found
    """
    from flask import send_file
    
    payment = Payment.query.get_or_404(payment_id)
    user_id = get_current_user_id()
    
    # Only allow user to download their own receipt, or admin/finance
    role = get_jwt()['role']
    if payment.user_id != user_id and role not in ['ADMIN', 'FINANCE', 'FINANCE_OFFICER']:
        return jsonify({'error': 'Unauthorized access to receipt'}), 403
    
    # Get related entities
    from models import User
    from models.property import Property
    from models.land import Land
    user = User.query.get(payment.user_id)
    tax = Tax.query.get(payment.tax_id)
    
    # Get property or land for address and commune
    if tax.property_id:
        asset = Property.query.get(tax.property_id)
    else:
        asset = Land.query.get(tax.land_id)
    
    try:
        # Generate PDF
        from utils.pdf_generator import receipt_generator
        
        # Prepare payment data for PDF
        payment_data = {
            'receipt_number': f'REC-{payment.id:06d}',
            'payment_id': payment.id,
            'payer_name': f'{user.first_name} {user.last_name}',
            'payer_cin': user.cin or 'N/A',
            'payment_date': payment.created_at,
            'amount': float(payment.amount),
            'method': payment.method.value,
            'tax_year': tax.tax_year,
            'property_address': f'{asset.street_address}, {asset.city}',
            'commune_name': asset.commune.nom_municipalite_fr
        }
        
        pdf_buffer = receipt_generator.generate_payment_receipt(payment_data)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'receipt_{payment.reference_number}.pdf'
        )
    except Exception as e:
        return jsonify({
            'error': 'PDF generation failed',
            'message': str(e),
            'payment_id': payment_id,
            'reference': payment.reference_number
        }), 500

@blp.get('/check-permit-eligibility/<int:user_id>')
@jwt_required()
def check_permit_eligibility(user_id):
    """Check if user can request building permits (Article 13 compliance)
    
    Verify that a user has no unpaid taxes, which is required before
    requesting any building permits per Article 13.
    
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID of the user to check
    responses:
      200:
        description: Eligibility status returned
        schema:
          type: object
          properties:
            user_id:
              type: integer
            eligible_for_permit:
              type: boolean
              description: Whether user can request permits
            unpaid_taxes:
              type: integer
              description: Number of unpaid taxes
            total_due:
              type: number
              format: float
              description: Total amount owed in TND
    """
    taxes = Tax.query.filter(
        Tax.property.has(owner_id=user_id) | Tax.land.has(owner_id=user_id)
    ).all()
    # Refresh penalties
    any_updates = False
    for t in taxes:
      if t.status != TaxStatus.PAID:
        section = 'TIB' if getattr(t.tax_type, 'name', 'TIB') == 'TIB' else 'TTNB'
        new_penalty = TaxCalculator.compute_late_payment_penalty_for_year(
          tax_amount=t.tax_amount,
          tax_year=t.tax_year,
          section=section
        )
        if (t.penalty_amount or 0.0) != new_penalty or (t.total_amount or 0.0) != (t.tax_amount + new_penalty):
          t.penalty_amount = new_penalty
          t.total_amount = t.tax_amount + new_penalty
          any_updates = True
    if any_updates:
      db.session.commit()

    unpaid = [t for t in taxes if t.status != TaxStatus.PAID]
    
    return jsonify({
        'user_id': user_id,
        'eligible_for_permit': len(unpaid) == 0,
        'unpaid_taxes': len(unpaid),
        'total_due': sum(t.total_amount for t in unpaid) if unpaid else 0
    }), 200
