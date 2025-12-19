# core/utils.py
"""Utility functions for analytics and tracking"""

import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from user_agents import parse as parse_user_agent
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_ip_location(ip_address):
    """
    Get geolocation data for an IP address.
    Uses ip-api.com (free, 45 requests per minute)
    """
    from .models import IPLocation

    # Check cache first
    try:
        cached = IPLocation.objects.get(ip_address=ip_address)
        # Cache for 30 days
        if cached.cached_at > timezone.now() - timedelta(days=30):
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
    except IPLocation.DoesNotExist:
        pass

    # Skip local/private IPs
    if ip_address in ['127.0.0.1', 'localhost', '::1'] or ip_address.startswith(('10.', '192.168.', '172.')):
        return {
            'country': 'Local',
            'country_code': 'LO',
            'city': 'Local',
            'region': '',
            'latitude': None,
            'longitude': None,
            'timezone': '',
            'isp': 'Local Network',
            'is_vpn': False,
            'is_proxy': False,
        }

    try:
        # Use ip-api.com (free tier)
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}?fields=status,message,country,countryCode,region,regionName,city,lat,lon,timezone,isp,proxy,hosting',
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('status') == 'success':
                location_data = {
                    'country': data.get('country', ''),
                    'country_code': data.get('countryCode', ''),
                    'city': data.get('city', ''),
                    'region': data.get('regionName', ''),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'timezone': data.get('timezone', ''),
                    'isp': data.get('isp', ''),
                    'is_vpn': data.get('hosting', False),
                    'is_proxy': data.get('proxy', False),
                }

                # Cache the result
                IPLocation.objects.update_or_create(
                    ip_address=ip_address,
                    defaults=location_data
                )

                return location_data
    except Exception as e:
        logger.error(f"Error getting IP location for {ip_address}: {e}")

    return {
        'country': 'Unknown',
        'country_code': 'XX',
        'city': '',
        'region': '',
        'latitude': None,
        'longitude': None,
        'timezone': '',
        'isp': '',
        'is_vpn': False,
        'is_proxy': False,
    }


def parse_user_agent_string(user_agent_string):
    """Parse user agent string to extract device, browser, OS info"""
    if not user_agent_string:
        return {
            'device_type': 'unknown',
            'browser': 'unknown',
            'browser_version': '',
            'os': 'unknown',
            'os_version': '',
            'is_bot': False,
        }

    try:
        ua = parse_user_agent(user_agent_string)

        # Determine device type
        if ua.is_mobile:
            device_type = 'mobile'
        elif ua.is_tablet:
            device_type = 'tablet'
        elif ua.is_pc:
            device_type = 'desktop'
        elif ua.is_bot:
            device_type = 'bot'
        else:
            device_type = 'other'

        return {
            'device_type': device_type,
            'browser': ua.browser.family,
            'browser_version': ua.browser.version_string,
            'os': ua.os.family,
            'os_version': ua.os.version_string,
            'is_bot': ua.is_bot,
        }
    except Exception as e:
        logger.error(f"Error parsing user agent: {e}")
        return {
            'device_type': 'unknown',
            'browser': 'unknown',
            'browser_version': '',
            'os': 'unknown',
            'os_version': '',
            'is_bot': False,
        }


def extract_referrer_domain(referrer):
    """Extract domain from referrer URL"""
    if not referrer:
        return 'direct'

    try:
        parsed = urlparse(referrer)
        domain = parsed.netloc or parsed.path
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain or 'direct'
    except:
        return 'direct'


def track_visitor_session(request):
    """Create or update visitor session with full tracking data"""
    from .models import VisitorSession, RealTimeVisitor

    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referrer = request.META.get('HTTP_REFERER', '')

    # Get location data
    location = get_ip_location(ip_address)

    # Parse user agent
    ua_data = parse_user_agent_string(user_agent)

    # Extract UTM parameters
    utm_source = request.GET.get('utm_source', '')
    utm_medium = request.GET.get('utm_medium', '')
    utm_campaign = request.GET.get('utm_campaign', '')

    session_data = {
        'ip_address': ip_address,
        'country': location['country'],
        'country_code': location['country_code'],
        'city': location['city'],
        'region': location['region'],
        'latitude': location['latitude'],
        'longitude': location['longitude'],
        'timezone': location['timezone'],
        'isp': location['isp'],
        'user_agent': user_agent,
        'device_type': ua_data['device_type'],
        'browser': ua_data['browser'],
        'browser_version': ua_data['browser_version'],
        'os': ua_data['os'],
        'os_version': ua_data['os_version'],
        'is_bot': ua_data['is_bot'],
        'referrer': referrer,
        'referrer_domain': extract_referrer_domain(referrer),
    }

    if request.user.is_authenticated:
        session_data['user'] = request.user

    # Create or update visitor session
    session, created = VisitorSession.objects.update_or_create(
        session_key=session_key,
        defaults=session_data
    )

    if created:
        session.landing_page = request.path
        session.utm_source = utm_source
        session.utm_medium = utm_medium
        session.utm_campaign = utm_campaign
        session.save()
    else:
        # Increment page views
        session.page_views += 1
        session.save(update_fields=['page_views', 'last_activity'])

    # Update real-time visitor
    RealTimeVisitor.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': request.user if request.user.is_authenticated else None,
            'ip_address': ip_address,
            'country': location['country'],
            'city': location['city'],
            'current_page': request.path,
            'device_type': ua_data['device_type'],
            'browser': ua_data['browser'],
        }
    )

    return session


def track_page_view(request, page_name=''):
    """Track a page view with full analytics data"""
    from .models import PageView

    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referrer = request.META.get('HTTP_REFERER', '')

    # Get location data
    location = get_ip_location(ip_address)

    # Parse user agent
    ua_data = parse_user_agent_string(user_agent)

    if not request.session.session_key:
        request.session.create()

    PageView.objects.create(
        page_name=page_name or request.path,
        page_url=request.build_absolute_uri(),
        user=request.user if request.user.is_authenticated else None,
        ip_address=ip_address,
        user_agent=user_agent,
        session_key=request.session.session_key,
        referrer=referrer,
        country=location['country'],
        city=location['city'],
        device_type=ua_data['device_type'],
        browser=ua_data['browser'],
        os=ua_data['os'],
    )


def track_postcard_interaction(request, postcard, interaction_type, duration=None):
    """Track a postcard interaction"""
    from .models import PostcardInteraction, VisitorSession

    ip_address = get_client_ip(request)
    location = get_ip_location(ip_address)
    ua_data = parse_user_agent_string(request.META.get('HTTP_USER_AGENT', ''))

    session = None
    if request.session.session_key:
        try:
            session = VisitorSession.objects.get(session_key=request.session.session_key)
        except VisitorSession.DoesNotExist:
            pass

    PostcardInteraction.objects.create(
        postcard=postcard,
        user=request.user if request.user.is_authenticated else None,
        session=session,
        interaction_type=interaction_type,
        ip_address=ip_address,
        duration=duration,
        country=location['country'],
        device_type=ua_data['device_type'],
    )


def cleanup_old_realtime_visitors():
    """Remove visitors inactive for more than 5 minutes"""
    from .models import RealTimeVisitor

    threshold = timezone.now() - timedelta(minutes=5)
    RealTimeVisitor.objects.filter(last_activity__lt=threshold).delete()


def aggregate_daily_analytics(date=None):
    """Aggregate daily analytics data"""
    from .models import (
        DailyAnalytics, PageView, CustomUser, SearchLog,
        PostcardLike, PostcardInteraction, ContactMessage,
        AnimationSuggestion, VisitorSession
    )
    from django.db.models import Count, Avg

    if date is None:
        date = timezone.now().date() - timedelta(days=1)

    start_datetime = timezone.make_aware(datetime.combine(date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(date, datetime.max.time()))

    # Basic metrics
    page_views = PageView.objects.filter(timestamp__date=date)
    sessions = VisitorSession.objects.filter(first_visit__date=date)

    total_visits = sessions.count()
    unique_visitors = sessions.values('ip_address').distinct().count()
    page_views_count = page_views.count()
    new_users = CustomUser.objects.filter(date_joined__date=date).count()
    total_searches = SearchLog.objects.filter(created_at__date=date).count()
    total_likes = PostcardLike.objects.filter(created_at__date=date).count()

    # Postcard metrics
    postcard_views = PostcardInteraction.objects.filter(
        timestamp__date=date,
        interaction_type='view'
    ).count()
    animation_views = PostcardInteraction.objects.filter(
        timestamp__date=date,
        interaction_type='animation_view'
    ).count()
    zooms = PostcardInteraction.objects.filter(
        timestamp__date=date,
        interaction_type='zoom'
    ).count()

    # Messages and suggestions
    messages = ContactMessage.objects.filter(created_at__date=date).count()
    suggestions = AnimationSuggestion.objects.filter(created_at__date=date).count()

    # Device breakdown
    mobile = sessions.filter(device_type='mobile').count()
    tablet = sessions.filter(device_type='tablet').count()
    desktop = sessions.filter(device_type='desktop').count()

    # Calculate bounce rate (sessions with only 1 page view)
    single_page_sessions = sessions.filter(page_views=1).count()
    bounce_rate = (single_page_sessions / total_visits * 100) if total_visits > 0 else 0

    # Average session duration
    avg_duration = sessions.aggregate(avg=Avg('total_time_spent'))['avg'] or 0

    # Top countries
    top_countries = dict(
        sessions.values('country')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('country', 'count')[:10]
    )

    # Top referrers
    top_referrers = dict(
        sessions.exclude(referrer_domain='')
        .exclude(referrer_domain='direct')
        .values('referrer_domain')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('referrer_domain', 'count')[:10]
    )

    # Top pages
    top_pages = dict(
        page_views.values('page_name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('page_name', 'count')[:10]
    )

    # Top searches
    top_searches = dict(
        SearchLog.objects.filter(created_at__date=date)
        .values('keyword')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('keyword', 'count')[:10]
    )

    # Save or update
    DailyAnalytics.objects.update_or_create(
        date=date,
        defaults={
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'page_views': page_views_count,
            'new_users': new_users,
            'total_searches': total_searches,
            'total_likes': total_likes,
            'total_postcards_viewed': postcard_views,
            'total_animations_viewed': animation_views,
            'total_zooms': zooms,
            'total_messages': messages,
            'total_suggestions': suggestions,
            'bounce_rate': bounce_rate,
            'avg_session_duration': int(avg_duration),
            'mobile_visits': mobile,
            'tablet_visits': tablet,
            'desktop_visits': desktop,
            'top_countries': top_countries,
            'top_referrers': top_referrers,
            'top_pages': top_pages,
            'top_searches': top_searches,
        }
    )