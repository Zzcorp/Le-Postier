# core/utils.py - Enhanced analytics utilities

import ipaddress
import logging
import threading

import requests
from django.utils import timezone
from user_agents import parse as parse_user_agent

logger = logging.getLogger(__name__)

# IPs currently being resolved in a background thread (avoid thread storms)
_geo_inflight = set()
_geo_inflight_lock = threading.Lock()

_LOCAL_LOCATION = {
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

_EMPTY_LOCATION = {
    'country': '',
    'country_code': '',
    'city': '',
    'region': '',
    'latitude': None,
    'longitude': None,
    'timezone': '',
    'isp': '',
    'is_vpn': False,
    'is_proxy': False,
}


def _validated_ip(candidate):
    """Return the candidate if it is a syntactically valid IP, else None."""
    if not candidate:
        return None
    candidate = candidate.strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def get_client_ip(request):
    """
    Get the client IP address from the request.

    X-Forwarded-For is client-spoofable (nginx APPENDS the real address to
    whatever the client sent), so: prefer X-Real-IP (set by our nginx from
    $remote_addr), else the LAST X-Forwarded-For entry (the proxy-appended
    one), else REMOTE_ADDR. Every candidate is validated so inet DB columns
    never receive garbage like 'unknown'.
    """
    real_ip = _validated_ip(request.META.get('HTTP_X_REAL_IP'))
    if real_ip:
        return real_ip

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        last_hop = _validated_ip(x_forwarded_for.split(',')[-1])
        if last_hop:
            return last_hop

    return _validated_ip(request.META.get('REMOTE_ADDR'))


def _location_dict_from_cache(cached):
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


def get_location_from_ip(ip_address):
    """
    Cache-only, synchronous location lookup. NEVER performs an external
    HTTP call: on an IPLocation cache miss it returns an empty location and
    fires a daemon thread (fetch_and_cache_location) that resolves and caches
    the IP for subsequent requests.
    """
    from .models import IPLocation

    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return dict(_LOCAL_LOCATION)

    try:
        cached = IPLocation.objects.filter(ip_address=ip_address).first()
    except Exception as e:
        logger.warning(f"IP cache lookup error: {e}")
        cached = None

    if cached:
        data = _location_dict_from_cache(cached)
        # Stale entry: serve it but refresh in the background
        if (timezone.now() - cached.cached_at).days >= 7:
            _spawn_geo_refresh(ip_address)
        return data

    _spawn_geo_refresh(ip_address)
    return dict(_EMPTY_LOCATION)


def _spawn_geo_refresh(ip_address):
    """Start a daemon thread resolving ip_address unless one is already running."""
    with _geo_inflight_lock:
        if ip_address in _geo_inflight:
            return
        _geo_inflight.add(ip_address)

    thread = threading.Thread(
        target=_geo_refresh_worker, args=(ip_address,), daemon=True,
        name=f'geo-{ip_address}',
    )
    thread.start()


def _geo_refresh_worker(ip_address):
    from django.db import connection
    try:
        fetch_and_cache_location(ip_address)
    except Exception as e:
        logger.warning(f"Background IP lookup failed for {ip_address}: {e}")
    finally:
        try:
            connection.close()
        except Exception:
            pass
        with _geo_inflight_lock:
            _geo_inflight.discard(ip_address)


def fetch_and_cache_location(ip_address):
    """
    Blocking external geolocation lookup (ip-api.com, fallback ipapi.co) that
    upserts the IPLocation cache. This is the daemon-thread target; only call
    it synchronously from contexts where blocking is acceptable (admin tools,
    management commands).
    """
    from .models import IPLocation

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
                'cached_at': timezone.now(),
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