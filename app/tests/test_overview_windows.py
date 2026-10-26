from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from app.overview.windows import window


class CalendarWindowTests(SimpleTestCase):
    def test_daylight_saving_day_and_comparison_use_calendar_boundaries(self):
        result = window(SimpleNamespace(timezone='America/New_York'), {'period': 'DAY'}, {},
                        datetime(2026, 3, 9, 12, tzinfo=timezone.utc))
        self.assertEqual(result['end']-result['start'], timedelta(hours=23))
        self.assertEqual(result['previous_end']-result['previous_start'], timedelta(hours=24))
        self.assertEqual(result['start'].isoformat(), '2026-03-08T05:00:00+00:00')

    def test_months_compare_previous_calendar_month_despite_different_lengths(self):
        result = window(SimpleNamespace(timezone='UTC'), {'period': 'MONTH'}, {},
                        datetime(2026, 3, 15, tzinfo=timezone.utc))
        self.assertEqual(result['end']-result['start'], timedelta(days=28))
        self.assertEqual(result['previous_end']-result['previous_start'], timedelta(days=31))
        self.assertEqual(result['comparison_mode'], 'PREVIOUS_CALENDAR_PERIOD')

    def test_week_is_last_complete_monday_to_monday(self):
        result = window(SimpleNamespace(timezone='Asia/Dhaka'), {'period': 'WEEK'}, {},
                        datetime(2026, 10, 25, 12, tzinfo=timezone.utc))
        self.assertEqual(result['end'].isoformat(), '2026-10-18T18:00:00+00:00')
        self.assertEqual(result['end']-result['start'], timedelta(days=7))
