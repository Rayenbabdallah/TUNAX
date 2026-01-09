"""Data validation utilities"""
import re
from datetime import datetime

class Validators:
    """Common validators for Tunisian tax system"""
    
    @staticmethod
    def validate_cin(cin):
        """Validate Tunisian National ID (CIN)"""
        # Simple validation - actual CIN has specific format
        return bool(re.match(r'^\d{8}$', cin.strip()))
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone):
        """Validate Tunisian phone number"""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\+\(\)]', '', phone)
        # Tunisian numbers: 8 digits, may start with +216
        return bool(re.match(r'^(\+216)?[0-9]{8}$', cleaned))
    
    @staticmethod
    def validate_surface(surface):
        """Validate surface area"""
        try:
            s = float(surface)
            return s > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_price(price):
        """Validate price/amount"""
        try:
            p = float(price)
            return p >= 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_address(street, city):
        """Basic address validation"""
        return bool(street and len(street) >= 3 and city and len(city) >= 2)
    
    @staticmethod
    def validate_year(year):
        """Validate tax year"""
        try:
            y = int(year)
            current_year = datetime.now().year
            return 2000 <= y <= current_year + 1
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_password(password):
        """
        Validate password strength
        Minimum: 8 chars, 1 uppercase, 1 number
        """
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"
    
    @staticmethod
    def validate_business_registration(reg_number):
        """Validate Tunisian business registration number"""
        # Simple format check
        return bool(re.match(r'^[A-Z0-9]{6,20}$', reg_number.strip()))

class ErrorMessages:
    """Standardized error messages"""
    
    INVALID_EMAIL = "Invalid email format"
    INVALID_PHONE = "Invalid phone number format"
    INVALID_CIN = "Invalid national ID (CIN) format"
    INVALID_ADDRESS = "Invalid address - street and city required"
    INVALID_SURFACE = "Invalid surface - must be positive number"
    INVALID_PRICE = "Invalid price - must be non-negative number"
    INVALID_YEAR = "Invalid year - must be between 2000 and current year + 1"
    INVALID_PASSWORD = "Password does not meet security requirements"
    INVALID_REGISTRATION = "Invalid business registration number"
    STREET_NOT_FOUND = "Street not found in external API - try nearest known street or provide GPS coordinates"
    DUPLICATE_EMAIL = "Email already registered"
    DUPLICATE_USERNAME = "Username already taken"
    DUPLICATE_CIN = "CIN already registered"
    INVALID_CREDENTIALS = "Invalid username or password"
    TOKEN_EXPIRED = "Token has expired"
    INVALID_TOKEN = "Invalid or malformed token"
    UNAUTHORIZED = "Unauthorized - check your permissions"
    ACCESS_DENIED = "Access denied - insufficient permissions"
    NOT_FOUND = "Resource not found"
    UNPAID_TAXES = "Cannot process request - outstanding taxes must be paid first"
