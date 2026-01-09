"""Geolocation and address validation using free APIs"""
import requests
from urllib.parse import quote

class GeoLocator:
    """Use Nominatim (OpenStreetMap) for free geocoding"""
    
    NOMINATIM_URL = "https://nominatim.openstreetmap.org"
    TIMEOUT = 10
    
    @staticmethod
    def geocode_address(street, city, country="Tunisia"):
        """
        Geocode an address to lat/lon using Nominatim
        Returns tuple: (latitude, longitude) or (None, None) if not found
        """
        try:
            query = f"{street}, {city}, {country}"
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'timeout': GeoLocator.TIMEOUT
            }
            
            headers = {'User-Agent': 'TunisianTaxSystem/1.0'}
            response = requests.get(
                f"{GeoLocator.NOMINATIM_URL}/search",
                params=params,
                headers=headers,
                timeout=GeoLocator.TIMEOUT
            )
            
            if response.status_code == 200 and response.json():
                result = response.json()[0]
                return float(result['lat']), float(result['lon'])
            
            return None, None
        except Exception as e:
            return None, None
    
    @staticmethod
    def reverse_geocode(latitude, longitude):
        """
        Reverse geocode lat/lon to address
        Returns dict with address components
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'timeout': GeoLocator.TIMEOUT
            }
            
            headers = {'User-Agent': 'TunisianTaxSystem/1.0'}
            response = requests.get(
                f"{GeoLocator.NOMINATIM_URL}/reverse",
                params=params,
                headers=headers,
                timeout=GeoLocator.TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'address': result.get('address', {}),
                    'display_name': result.get('display_name', '')
                }
            
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def validate_address(street, city):
        """
        Validate if address exists
        Returns True if found, False otherwise
        """
        lat, lon = GeoLocator.geocode_address(street, city)
        return lat is not None and lon is not None
    
    @staticmethod
    def get_nearby_streets(city, search_term=""):
        """
        Get list of nearby streets in a city (fallback suggestion)
        """
        try:
            # This is a simplified approach using Nominatim
            params = {
                'q': f"{search_term} street, {city}, Tunisia",
                'format': 'json',
                'limit': 10,
                'timeout': GeoLocator.TIMEOUT
            }
            
            headers = {'User-Agent': 'TunisianTaxSystem/1.0'}
            response = requests.get(
                f"{GeoLocator.NOMINATIM_URL}/search",
                params=params,
                headers=headers,
                timeout=GeoLocator.TIMEOUT
            )
            
            if response.status_code == 200:
                results = response.json()
                return [r['display_name'] for r in results]
            
            return []
        except Exception as e:
            return []

class SatelliteImagery:
    """Access free satellite imagery from various sources"""
    
    # OSM Tiles (free, no authentication needed)
    OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    
    # NASA GIBS (free, high-res, updated daily)
    NASA_GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
    # Example layer: MODIS Terra True Color
    NASA_GIBS_LAYER = "MODIS_Terra_CorrectedReflectance_TrueColor"
    NASA_GIBS_TILE_TEMPLATE = (
        "{base}/{layer}/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
    )

    # USGS Landsat: link to EarthExplorer browse search
    USGS_LANDSAT_BROWSE = "https://earthexplorer.usgs.gov/"
    
    @staticmethod
    def get_osm_tile_url(zoom, x, y):
        """Get OSM tile URL for given coordinates"""
        return GeoLocator.OSM_TILE_URL.format(z=zoom, x=x, y=y)
    
    @staticmethod
    def get_static_map(latitude, longitude, zoom=15, width=400, height=400):
        """
        Generate static map URL showing location
        Uses OpenStreetMap static tile rendering
        """
        # Calculate tile position
        import math
        n = 2.0 ** zoom
        xtile = int((longitude + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(math.radians(latitude)) + 1.0 / math.cos(math.radians(latitude))) / math.pi) / 2.0 * n)
        
        return {
            'osm_tile': SatelliteImagery.get_osm_tile_url(zoom, xtile, ytile),
            'latitude': latitude,
            'longitude': longitude,
            'zoom': zoom,
            'map_service': 'OpenStreetMap'
        }
    
    @staticmethod
    def get_satellite_imagery_info(latitude, longitude):
        """Get available satellite imagery info + URLs for location"""
        import datetime
        today = datetime.date.today().isoformat()

        # Derive tile indices for GIBS WMTS (WebMercator)
        zoom = 8
        import math
        n = 2 ** zoom
        x = int((longitude + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(math.radians(latitude)) + 1.0 / math.cos(math.radians(latitude))) / math.pi) / 2.0 * n)

        gibs_tile = SatelliteImagery.NASA_GIBS_TILE_TEMPLATE.format(
            base=SatelliteImagery.NASA_GIBS_BASE,
            layer=SatelliteImagery.NASA_GIBS_LAYER,
            date=today,
            z=zoom,
            x=x,
            y=y,
        )

        return {
            'location': {
                'latitude': latitude,
                'longitude': longitude
            },
            'available_sources': [
                {
                    'name': 'OpenStreetMap',
                    'type': 'terrain/street',
                    'updated': 'real-time',
                    'attribution': 'OSM Contributors'
                },
                {
                    'name': 'NASA GIBS',
                    'type': 'satellite',
                    'updated': 'daily',
                    'resolution': '250m',
                    'wmts_tile': gibs_tile
                },
                {
                    'name': 'USGS Landsat',
                    'type': 'satellite',
                    'updated': 'monthly',
                    'resolution': '30m',
                    'browse': SatelliteImagery.USGS_LANDSAT_BROWSE
                }
            ],
            'map_url': f"https://www.openstreetmap.org/?zoom=15&lat={latitude}&lon={longitude}"
        }
