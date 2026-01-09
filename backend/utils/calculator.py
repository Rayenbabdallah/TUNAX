"""Tax calculation according to Code de la Fiscalité Locale 2025"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

import yaml


class TaxCalculator:
    """Calculate TIB and TTNB based on Tunisian law using configurable tables."""

    _cfg: Dict[str, Any] | None = None

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        if cls._cfg is not None:
            return cls._cfg
        # Try to load YAML, fallback to embedded defaults
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))  # backend/
            cfg_path = os.path.join(base_dir, 'resources', 'tariffs_2025.yaml')
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cls._cfg = yaml.safe_load(f) or {}
        except Exception:
            cls._cfg = {}
        # Defaults if missing
        cls._cfg.setdefault('TIB', {})
        cls._cfg['TIB'].setdefault('surface_categories', [
            {'min': 0, 'max': 50, 'label': 'A', 'multiplier': 1.00},
            {'min': 50, 'max': 100, 'label': 'B', 'multiplier': 1.25},
            {'min': 100, 'max': 200, 'label': 'C', 'multiplier': 1.50},
            {'min': 200, 'max': 9.0e9, 'label': 'D', 'multiplier': 1.75},
        ])
        cls._cfg['TIB'].setdefault('service_rates', [
            {'min_services': 0, 'rate_percent': 8},
            {'min_services': 2, 'rate_percent': 10},
            {'min_services': 3, 'rate_percent': 12},
            {'min_services': 4, 'rate_percent': 14},
        ])
        cls._cfg['TIB'].setdefault('rounding', {'currency_decimals': 3})
        cls._cfg['TIB'].setdefault('exemptions', [])

        cls._cfg.setdefault('TTNB', {})
        cls._cfg['TTNB'].setdefault('base_rate_percent', 0.3)
        cls._cfg['TTNB'].setdefault('rounding', {'currency_decimals': 3})
        cls._cfg['TTNB'].setdefault('exemptions', [])
        return cls._cfg

    @classmethod
    def _round(cls, amount: float, section: str) -> float:
        cfg = cls._load_config()
        decimals = int(cfg.get(section, {}).get('rounding', {}).get('currency_decimals', 3))
        return round(float(amount), decimals)

    @classmethod
    def _get_surface_multiplier(cls, surface_m2: float) -> float:
        cfg = cls._load_config()
        for bracket in cfg['TIB']['surface_categories']:
            if bracket['min'] <= surface_m2 < bracket['max']:
                return float(bracket['multiplier'])
        # Fallback to highest
        return float(cfg['TIB']['surface_categories'][-1]['multiplier'])

    @classmethod
    def _get_service_rate(cls, num_services: int) -> float:
        cfg = cls._load_config()
        # pick the highest threshold <= num_services
        applicable = 0
        for band in cfg['TIB']['service_rates']:
            if num_services >= int(band['min_services']):
                applicable = float(band['rate_percent'])
        return applicable / 100.0

    @staticmethod
    def _years_since(year: Optional[int]) -> Optional[int]:
        if not year:
            return None
        try:
            return max(0, datetime.utcnow().year - int(year))
        except Exception:
            return None

    @classmethod
    def _match_exemption(cls, kind: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cfg = cls._load_config()
        rules = cfg.get(kind, {}).get('exemptions', [])
        for rule in rules:
            cond = rule.get('conditions', {})
            ok = True
            # affectation check (for TIB)
            if 'affectation_in' in cond:
                affectation = (context.get('affectation') or '').lower()
                allowed = [str(x).lower() for x in cond['affectation_in']]
                ok = ok and (affectation in allowed)
            # land_type check (for TTNB)
            if 'land_type_in' in cond:
                land_type = (context.get('land_type') or '').lower()
                allowed = [str(x).lower() for x in cond['land_type_in']]
                ok = ok and (land_type in allowed)
            # exemption reason check
            if 'exemption_reason_in' in cond:
                reason = (context.get('exemption_reason') or '').lower()
                allowed = [str(x).lower() for x in cond['exemption_reason_in']]
                ok = ok and (reason in allowed)
            # max age since construction
            if 'max_age_years' in cond:
                years = cls._years_since(context.get('construction_year'))
                if years is None or years > int(cond['max_age_years']):
                    ok = False
            if ok:
                return rule
        return None

    @classmethod
    def calculate_tib(cls, property_obj):
        """
        Calculate TIB (Taxe sur les Immeubles Bâtis) per Code de la Fiscalité Locale 2025
        LEGALLY CORRECT implementation using municipality's reference prices and service counts
        
        Formula:
        1. Assiette TIB = 0.02 × (Reference price per m² × Covered surface)
        2. TIB = Assiette × Service rate (8%, 10%, 12%)
        
        Args:
            property_obj: Property instance
        
        Returns:
            dict with: base_amount, rate_percent, tax_amount, total_amount, category, services_count
        """
        
        # Check exemption flag
        if getattr(property_obj, 'is_exempt', False):
            return {
                'base_amount': 0.0,
                'rate_percent': 0.0,
                'tax_amount': 0.0,
                'total_amount': 0.0,
                'exemption_reason': getattr(property_obj, 'exemption_reason', None)
            }
        
        # Step 1: Determine TIB category from covered surface
        surface = float(property_obj.surface_couverte)
        if surface <= 100:
            category = 1
        elif surface <= 200:
            category = 2
        elif surface <= 400:
            category = 3
        else:
            category = 4
        
        # Step 2: Get reference price per m² for this municipality
        ref_price_per_m2 = getattr(property_obj, 'reference_price_per_m2', None)
        if not ref_price_per_m2:
            return {'error': f'Reference price per m² required for category {category}'}
        
        # Step 3: Calculate Assiette (base) - LEGALLY CORRECT per Article 4
        # Assiette = 2% × (reference_price_per_m² × covered_surface)
        assiette = 0.02 * (float(ref_price_per_m2) * surface)
        
        # Step 4: Count available services in municipality/locality
        from models import MunicipalServiceConfig
        base_query = MunicipalServiceConfig.query.filter_by(
            commune_id=property_obj.commune_id,
            is_available=True
        )
        locality_name = (getattr(property_obj, 'delegation', None) or '').strip()
        services_count = 0
        if locality_name:
            locality_services = base_query.filter(
                MunicipalServiceConfig.locality_name.ilike(locality_name)
            ).count()
            services_count = locality_services
        if services_count == 0:
            services_count = base_query.filter(
                MunicipalServiceConfig.locality_name.is_(None)
            ).count()
        
        # Step 5: Determine service rate - LEGALLY CORRECT per Article 5
        # NOT a surcharge, but the actual tax rate
        if services_count <= 2:
            service_rate = 0.08  # 8% for 1-2 services
        elif services_count <= 4:
            service_rate = 0.10  # 10% for 3-4 services
        elif services_count <= 6:
            service_rate = 0.12  # 12% for more than 4 services (5-6)
        else:
            service_rate = 0.14  # 14% for more than 4 + additional services (7+)
        
        # Step 6: Calculate final TIB - LEGALLY CORRECT
        # TIB = Assiette × Service rate (NOT Assiette × (1 + rate))
        tib_amount = assiette * service_rate
        
        return {
            'base_amount': cls._round(assiette, 'TIB'),
            'rate_percent': service_rate * 100,
            'tax_amount': cls._round(tib_amount, 'TIB'),
            'total_amount': cls._round(tib_amount, 'TIB'),
            'category': category,
            'services_count': services_count
        }

    @classmethod
    def calculate_ttnb(cls, land_obj):
        """
        Calculate TTNB (Taxe sur les Terrains Non Bâtis) per Code de la Fiscalité Locale 2025
        LEGALLY CORRECT implementation using urban zoning tariffs from Décret 2017-396
        
        Formula:
        TTNB = Surface area (m²) × Zoning tariff (TND/m²)
        
        Official tariffs (immutable by law):
        - haute_densite (high-density): 1.200 TND/m²
        - densite_moyenne (medium-density): 0.800 TND/m²
        - faible_densite (low-density): 0.400 TND/m²
        - peripherique (peripheral/non-urban): 0.200 TND/m²
        
        Args:
            land_obj: Land instance with required urban_zone
        
        Returns:
            dict with: base_amount, rate_percent, tax_amount, total_amount, zone, tariff_per_m2
        """
        
        # Check exemption flag
        if getattr(land_obj, 'is_exempt', False):
            return {
                'base_amount': 0.0,
                'rate_percent': 0.0,
                'tax_amount': 0.0,
                'total_amount': 0.0,
                'exemption_reason': getattr(land_obj, 'exemption_reason', None)
            }
        
        # Step 1: REQUIRED - Urban zone classification must be provided
        urban_zone = getattr(land_obj, 'urban_zone', None)
        if not urban_zone:
            return {
                'error': 'Urban zone classification required',
                'valid_zones': ['haute_densite', 'densite_moyenne', 'faible_densite', 'peripherique'],
                'message': 'TTNB cannot be calculated without urban zone classification per Décret 2017-396'
            }
        
        # Step 2: Official zoning tariffs from Décret gouvernemental n°2017-396 du 28 mars 2017
        ZONE_TARIFFS = {
            'haute_densite': 1.200,       # TND/m² (High-density urban zone)
            'densite_moyenne': 0.800,    # TND/m² (Medium-density zone)
            'faible_densite': 0.400,     # TND/m² (Low-density zone)
            'peripherique': 0.200        # TND/m² (Peripheral / non-urban zone)
        }
        
        tariff = ZONE_TARIFFS.get(urban_zone.lower())
        if not tariff:
            return {
                'error': f'Invalid urban zone: {urban_zone}',
                'valid_zones': list(ZONE_TARIFFS.keys())
            }
        
        # Step 3: Calculate TTNB - LEGALLY CORRECT per Article 33
        # TTNB = Surface area × Zoning tariff (NOT percentage-based)
        surface = float(getattr(land_obj, 'surface', 0))
        if surface <= 0:
            return {'error': 'Land surface must be greater than 0'}
        
        ttnb_amount = surface * tariff
        
        return {
            'base_amount': cls._round(ttnb_amount, 'TTNB'),
            'rate_percent': 0.0,  # Not percentage-based
            'tax_amount': cls._round(ttnb_amount, 'TTNB'),
            'total_amount': cls._round(ttnb_amount, 'TTNB'),
            'zone': urban_zone,
            'tariff_per_m2': tariff,
            'surface_m2': surface
        }

    @classmethod
    def calculate_penalty(cls, tax_amount: float, penalty_type: str, days_late: int = 0) -> float:
        """Deprecated: Use compute_late_payment_penalty_for_year for late payments.

        Retains only late_declaration fixed-rate behavior for backwards compatibility.
        """
        if penalty_type == 'late_declaration':
            return cls._round(tax_amount * 0.10, 'TIB')
        elif penalty_type == 'late_payment':
            # Backwards-compatible fallback: 1.25% per month based on days provided
            months_late = max(0, int(days_late) // 30)
            penalty = tax_amount * (months_late * 0.0125)
            return cls._round(penalty, 'TIB')
        else:
            return 0.0

    @classmethod
    def compute_late_payment_penalty_for_year(
        cls,
        tax_amount: float,
        tax_year: int,
        section: str = 'TIB',
        today: Optional[datetime] = None,
    ) -> float:
        """Compute late payment penalty per policy: 1.25% per month starting Jan 1 of (tax_year + 2).

        Rules provided by product owner:
        - Tax year N is estimated during year N.
        - Payable from Jan 1 of N+1 without penalties.
        - Penalties begin Jan 1 of N+2 at 1.25% per month on principal.

        Args:
            tax_amount: Principal tax amount (excluding penalties).
            tax_year: Year of the tax liability.
            section: Rounding section ('TIB' or 'TTNB').
            today: Optional override of current date/time (UTC). Defaults to now.

        Returns:
            Rounded penalty amount accrued to date.
        """
        if not tax_year:
            return 0.0
        if today is None:
            today = datetime.utcnow()
        # Penalty start: Jan 1 of (tax_year + 2)
        start_year = int(tax_year) + 2
        start = datetime(start_year, 1, 1)
        if today < start:
            return 0.0
        # Compute full months elapsed from start to today (no partial month rounding up)
        months_elapsed = (today.year - start.year) * 12 + (today.month - start.month)
        months_elapsed = max(0, months_elapsed)
        penalty = float(tax_amount) * 0.0125 * months_elapsed
        return cls._round(penalty, section)
