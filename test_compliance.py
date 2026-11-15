# -*- coding: utf-8 -*-
"""
Unit tests for Tacho Studio EU 561/2006 & AETR compliance calculation rules.
Run with: pytest
"""
import datetime as dt
import unittest
from main import CardData, Analysis, build_utc_intervals


def make_card_with_days(days_spec):
    """Helper to construct a synthetic CardData instance without hardware."""
    c = CardData()
    c.name = "Test Driver"
    c.number = "TEST000000000001"
    c.gen = 2
    days = []
    for date_obj, dist, changes in days_spec:
        ch_list = [
            dict(slot=0, crew=0, ins=True, act=act, minute=minute)
            for minute, act in changes
        ]
        days.append(dict(date=dt.datetime.combine(date_obj, dt.time()), dist=dist, changes=ch_list))
    c.days = days
    c.intervals = build_utc_intervals(days)
    return c


class TestTachoCompliance(unittest.TestCase):
    def test_daily_driving_under_9h_no_violation(self):
        # 8 hours driving (480 min) + rest -> compliant
        d1 = dt.date(2026, 11, 2)
        card = make_card_with_days([
            (d1, 520, [
                (0, 0),      # 00:00 - 06:00 Rest
                (360, 3),    # 06:00 - 10:00 Drive (4h)
                (600, 0),    # 10:00 - 10:45 Break (45m)
                (645, 3),    # 10:45 - 14:45 Drive (4h)
                (885, 0),    # 14:45 - 24:00 Rest
            ])
        ])
        an = Analysis(card, tzmode='utc')
        violations = [v for v in an.V if v['level'] == 'Prekršaj']
        self.assertEqual(len(violations), 0)
        self.assertEqual(an.day(d1)['drive'], 480)

    def test_daily_driving_over_10h_violation(self):
        # 10h 30m driving (630 min) -> must trigger daily driving infringement
        d1 = dt.date(2026, 11, 3)
        card = make_card_with_days([
            (d1, 710, [
                (0, 0),
                (300, 3),    # 05:00 - 09:30 Drive (4h30m)
                (570, 0),    # 09:30 - 10:15 Break (45m)
                (615, 3),    # 10:15 - 14:45 Drive (4h30m)
                (885, 0),    # 14:45 - 15:30 Break (45m)
                (930, 3),    # 15:30 - 17:00 Drive (1h30m) -> Total 10h30m
                (1020, 0),   # 17:00 - 24:00 Rest
            ])
        ])
        an = Analysis(card, tzmode='utc')
        daily_viols = [v for v in an.V if v['level'] == 'Prekršaj' and v['type'] == 'Dnevno upravljanje']
        self.assertEqual(len(daily_viols), 1)

    def test_continuous_driving_over_4h30_violation(self):
        # 5 hours continuous driving without 45m break -> infringement
        d1 = dt.date(2026, 11, 4)
        card = make_card_with_days([
            (d1, 380, [
                (0, 0),
                (480, 3),    # 08:00 - 13:00 Drive (5h continuous)
                (780, 0),    # 13:00 - 24:00 Rest
            ])
        ])
        an = Analysis(card, tzmode='utc')
        cont_viols = [v for v in an.V if v['type'] == 'Neprekidno upravljanje']
        self.assertEqual(len(cont_viols), 1)


if __name__ == '__main__':
    unittest.main()
