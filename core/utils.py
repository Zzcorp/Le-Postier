# core/utils.py - Enhanced analytics utilities

import requests
from django.conf import settings
from django.utils import timezone
from user_agents import parse as parse_user_agent
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_location_from_ip(ip_address):
    """
    Get location data from IP address using free IP geolocation API.
    Returns dict with country, city, etc.
    """
    from .models import IPLocation

    # Skip private/local IPs
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return {
            'country': 'Local',
            'country_code': 'LC',
            'city': 'Localhost',
            'region': '',
            'latitude': None,
            'longitude': None,
            'timezone': '',
            'isp': 'Local',
            'is_vpn': False,
            'is_proxy': False,
        }

    # Check cache first
    try:
        cached = IPLocation.objects.filter(ip_address=ip_address).first()
        if cached and (timezone.now() - cached.cached_at).days < 7:
            return {
                'country': cached.country,
                'country_code': cached.country_code,
                'city': cached.city,
                'region': cached.region,
                'latitude': cached.latitude,
                'longitude': cached.longitude,
                'timezone': cached.timezone,
                'isp': cached.isp,
                'is_vpn': cached.is_vpn,
                'is_proxy': cached.is_proxy,
            }
    except Exception as e:
        logger.warning(f"IP cache lookup error: {e}")

    # Try multiple free APIs
    location_data = None

    # Try ip-api.com (free, 45 requests/minute)
    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}?fields=status,country,countryCode,regionName,city,lat,lon,timezone,isp,proxy,hosting',
            timeout=3
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                location_data = {
                    'country': data.get('country', 'Unknown'),
                    'country_code': data.get('countryCode', ''),
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('regionName', ''),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'timezone': data.get('timezone', ''),
                    'isp': data.get('isp', ''),
                    'is_vpn': data.get('hosting', False),
                    'is_proxy': data.get('proxy', False),
                }
    except Exception as e:
        logger.warning(f"ip-api.com lookup failed: {e}")

    # Fallback to ipapi.co
    if not location_data:
        try:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/',
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if not data.get('error'):
                    location_data = {
                        'country': data.get('country_name', 'Unknown'),
                        'country_code': data.get('country_code', ''),
                        'city': data.get('city', 'Unknown'),
                        'region': data.get('region', ''),
                        'latitude': data.get('latitude'),
                        'longitude': data.get('longitude'),
                        'timezone': data.get('timezone', ''),
                        'isp': data.get('org', ''),
                        'is_vpn': False,
                        'is_proxy': False,
                    }
        except Exception as e:
            logger.warning(f"ipapi.co lookup failed: {e}")

    # Default if all APIs fail
    if not location_data:
        location_data = {
            'country': 'Unknown',
            'country_code': '',
            'city': 'Unknown',
            'region': '',
            'latitude': None,
            'longitude': None,
            'timezone': '',
            'isp': '',
            'is_vpn': False,
            'is_proxy': False,
        }

    # Cache the result
    try:
        IPLocation.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'country': location_data['country'],
                'country_code': location_data['country_code'],
                'city': location_data['city'],
                'region': location_data['region'],
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                'timezone': location_data['timezone'],
                'isp': location_data['isp'],
                'is_vpn': location_data['is_vpn'],
                'is_proxy': location_data['is_proxy'],
            }
        )
    except Exception as e:
        logger.warning(f"IP cache save error: {e}")

    return location_data


def parse_user_agent_string(user_agent_string):
    """Parse user agent string to extract device, browser, and OS info"""
    if not user_agent_string:
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'browser_version': '',
            'os': 'Unknown',
            'os_version': '',
            'is_bot': False,
        }

    try:
        ua = parse_user_agent(user_agent_string)

        # Determine device type
        if ua.is_mobile:
            device_type = 'Mobile'
        elif ua.is_tablet:
            device_type = 'Tablet'
        elif ua.is_pc:
            device_type = 'Desktop'
        elif ua.is_bot:
            device_type = 'Bot'
        else:
            device_type = 'Other'

        return {
            'device_type': device_type,
            'browser': ua.browser.family or 'Unknown',
            'browser_version': ua.browser.version_string or '',
            'os': ua.os.family or 'Unknown',
            'os_version': ua.os.version_string or '',
            'is_bot': ua.is_bot,
        }
    except Exception as e:
        logger.warning(f"User agent parse error: {e}")
        return {
            'device_type': 'Unknown',
            'browser': 'Unknown',
            'browser_version': '',
            'os': 'Unknown',
            'os_version': '',
            'is_bot': False,
        }


def get_country_flag_emoji(country_code):
    """Convert country code to flag emoji"""
    if not country_code or len(country_code) != 2:
        return '🌍'

    try:
        # Convert country code to flag emoji
        flag = ''.join(chr(ord(c) + 127397) for c in country_code.upper())
        return flag
    except:
        return '🌍'


def format_duration(seconds):
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"