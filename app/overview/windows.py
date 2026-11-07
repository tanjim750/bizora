from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError


def aware_timestamp(value):
    try:
        result = parse_datetime(value)
    except (ValueError, TypeError):
        result = None
    if result is None or result.tzinfo is None:
        raise ValidationError('Times must be ISO 8601 datetimes with an explicit timezone.')
    return result.astimezone(timezone.utc)


def previous_month(value):
    return value.replace(year=value.year-1, month=12) if value.month == 1 else value.replace(month=value.month-1)


def window(business, config, params, now):
    try:
        zone = ZoneInfo(business.timezone)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValidationError('Business timezone is invalid; correct business configuration.')
    period = params.get('period', config['period'])
    if 'from' in params:
        start, end = params['from'], params['to']
        previous_end, previous_start = start, start-(end-start)
    else:
        end = datetime.combine(now.astimezone(zone).date(), datetime.min.time(), zone)
        if period == 'WEEK':
            end -= timedelta(days=(end.weekday()-config.get('week_start', 0)) % 7)
            start = end-timedelta(days=7)
            previous_start = start-timedelta(days=7)
        elif period == 'MONTH':
            end = end.replace(day=1)
            start = previous_month(end)
            previous_start = previous_month(start)
        elif period in {'ROLLING_7D', 'ROLLING_30D'}:
            days = 7 if period == 'ROLLING_7D' else 30
            start = end-timedelta(days=days)
            previous_start = start-timedelta(days=days)
        else:
            start = end-timedelta(days=1)
            previous_start = start-timedelta(days=1)
        previous_end = start
    if start >= end or end > now or end-start > timedelta(days=366):
        raise ValidationError('Window must be positive, at most 366 days, and end no later than now.')
    return {'start': start.astimezone(timezone.utc), 'end': end.astimezone(timezone.utc),
            'previous_start': previous_start.astimezone(timezone.utc),
            'previous_end': previous_end.astimezone(timezone.utc), 'period': period, 'timezone': business.timezone,
            'bounds': '[start,end)', 'comparison_mode': 'PREVIOUS_EQUAL_DURATION' if 'from' in params else 'PREVIOUS_CALENDAR_PERIOD'}
