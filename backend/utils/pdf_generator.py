"""PDF Receipt Generator"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from datetime import datetime
import os

class ReceiptGenerator:
    """Generate PDF receipts for payments"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title_Center',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
        ))
        
        self.styles.add(ParagraphStyle(
            name='Header_Right',
            parent=self.styles['Normal'],
            alignment=TA_RIGHT,
            fontSize=10,
            textColor=colors.HexColor('#7F8C8D'),
        ))
    
    def generate_payment_receipt(self, payment_data):
        """
        Generate payment receipt PDF
        
        Args:
            payment_data: dict with keys:
                - receipt_number
                - payment_id
                - payer_name
                - payer_cin
                - payment_date
                - amount
                - method
                - tax_year
                - property_address
                - commune_name
        
        Returns:
            BytesIO buffer with PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        story = []
        
        # Header
        story.append(Paragraph("RÉPUBLIQUE TUNISIENNE", self.styles['Header_Right']))
        story.append(Paragraph("MINISTÈRE DES AFFAIRES LOCALES", self.styles['Header_Right']))
        story.append(Spacer(1, 0.5*cm))
        
        # Title
        story.append(Paragraph("REÇU DE PAIEMENT", self.styles['Title_Center']))
        story.append(Paragraph(f"N° {payment_data['receipt_number']}", self.styles['Title_Center']))
        story.append(Spacer(1, 1*cm))
        
        # Payment details table
        data = [
            ['Information', 'Détails'],
            ['Date de paiement', payment_data['payment_date'].strftime('%d/%m/%Y %H:%M')],
            ['Payeur', payment_data['payer_name']],
            ['CIN', payment_data.get('payer_cin', 'N/A')],
            ['Commune', payment_data['commune_name']],
            ['Adresse du bien', payment_data.get('property_address', 'N/A')],
            ['Année fiscale', str(payment_data['tax_year'])],
            ['Montant payé', f"{payment_data['amount']:.3f} TND"],
            ['Méthode de paiement', self._format_payment_method(payment_data['method'])],
            ['Référence', f"PAY-{payment_data['payment_id']}"],
        ]
        
        table = Table(data, colWidths=[6*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 2*cm))
        
        # Legal notice
        legal_text = """
        <para fontSize=9 textColor="#7F8C8D">
        Ce reçu atteste du paiement des taxes municipales conformément au Code de la Fiscalité Locale 2025.
        Ce document a valeur légale et doit être conservé comme preuve de paiement.
        </para>
        """
        story.append(Paragraph(legal_text, self.styles['Normal']))
        story.append(Spacer(1, 1*cm))
        
        # Footer
        footer_text = f"""
        <para fontSize=8 textColor="#95A5A6" alignment="center">
        Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}<br/>
        Système de Gestion des Taxes Municipales - TUNAX<br/>
        www.finances.gov.tn
        </para>
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _format_payment_method(self, method):
        """Format payment method for display"""
        methods = {
            'card': 'Carte bancaire',
            'bank_transfer': 'Virement bancaire',
            'check': 'Chèque',
            'cash': 'Espèces'
        }
        return methods.get(method, method)
    
    def generate_attestation(self, attestation_data):
        """
        Generate tax attestation PDF
        
        Args:
            attestation_data: dict with keys:
                - attestation_number
                - issue_date
                - taxpayer_name
                - taxpayer_cin
                - property_address
                - commune_name
                - tax_years (list of years)
                - total_paid
        
        Returns:
            BytesIO buffer with PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        story = []
        
        # Header
        story.append(Paragraph("RÉPUBLIQUE TUNISIENNE", self.styles['Header_Right']))
        story.append(Paragraph("MINISTÈRE DES AFFAIRES LOCALES", self.styles['Header_Right']))
        story.append(Paragraph(f"COMMUNE DE {attestation_data['commune_name'].upper()}", self.styles['Header_Right']))
        story.append(Spacer(1, 0.5*cm))
        
        # Title
        story.append(Paragraph("ATTESTATION DE PAIEMENT", self.styles['Title_Center']))
        story.append(Paragraph(f"N° {attestation_data['attestation_number']}", self.styles['Title_Center']))
        story.append(Spacer(1, 1*cm))
        
        # Attestation text
        years_text = ", ".join(str(y) for y in attestation_data['tax_years'])
        attestation_text = f"""
        <para fontSize=12 leading=18>
        Le soussigné, Receveur Municipal de la Commune de <b>{attestation_data['commune_name']}</b>,
        atteste que <b>{attestation_data['taxpayer_name']}</b> (CIN: {attestation_data.get('taxpayer_cin', 'N/A')}),
        est à jour de ses obligations fiscales concernant le bien situé à:<br/>
        <b>{attestation_data.get('property_address', 'N/A')}</b><br/><br/>
        
        Les taxes municipales ont été acquittées pour les années fiscales: <b>{years_text}</b><br/>
        Montant total payé: <b>{attestation_data['total_paid']:.3f} TND</b><br/><br/>
        
        La présente attestation est délivrée pour servir et valoir ce que de droit.
        </para>
        """
        story.append(Paragraph(attestation_text, self.styles['Normal']))
        story.append(Spacer(1, 2*cm))
        
        # Date and signature
        date_text = f"""
        <para fontSize=11 alignment="right">
        Fait à {attestation_data['commune_name']}, le {attestation_data['issue_date'].strftime('%d/%m/%Y')}<br/><br/>
        <b>Le Receveur Municipal</b><br/>
        (Signature et cachet)
        </para>
        """
        story.append(Paragraph(date_text, self.styles['Normal']))
        story.append(Spacer(1, 2*cm))
        
        # Legal notice
        legal_text = """
        <para fontSize=8 textColor="#7F8C8D">
        Conformément au Code de la Fiscalité Locale 2025, cette attestation certifie que le contribuable
        est en règle avec ses obligations fiscales municipales pour la période indiquée.
        </para>
        """
        story.append(Paragraph(legal_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

# Global instance
receipt_generator = ReceiptGenerator()
