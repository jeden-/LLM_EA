"""
Testy jednostkowe dla filtrów szablonów w dashboardzie.

Ten moduł zawiera testy sprawdzające poprawność działania filtrów
używanych w szablonach Jinja2 w aplikacji Flask.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Dashboard.dashboard import (
    status_badge_filter,
    status_label_filter,
    datetime_filter
)


class TestDashboardFilters(unittest.TestCase):
    """Testy dla filtrów szablonów dashboardu."""

    def test_status_badge_filter(self):
        """Test filtra status_badge_filter."""
        # Testowanie różnych statusów
        self.assertEqual(status_badge_filter('PENDING'), 'bg-warning')
        self.assertEqual(status_badge_filter('EXECUTED'), 'bg-success')
        self.assertEqual(status_badge_filter('EXPIRED'), 'bg-secondary')
        self.assertEqual(status_badge_filter('REJECTED'), 'bg-danger')
        self.assertEqual(status_badge_filter('UNKNOWN'), 'bg-info')

    def test_status_label_filter(self):
        """Test filtra status_label_filter."""
        # Testowanie różnych statusów
        self.assertEqual(status_label_filter('PENDING'), 'Oczekujący')
        self.assertEqual(status_label_filter('EXECUTED'), 'Wykonany')
        self.assertEqual(status_label_filter('EXPIRED'), 'Wygasły')
        self.assertEqual(status_label_filter('REJECTED'), 'Odrzucony')
        self.assertEqual(status_label_filter('UNKNOWN'), 'UNKNOWN')

    def test_datetime_filter_with_datetime_object(self):
        """Test filtra datetime_filter z obiektem datetime."""
        # Testowanie z obiektem datetime
        dt = datetime(2023, 5, 15, 14, 30, 0)
        self.assertEqual(datetime_filter(dt), '15-05-2023 14:30')
        self.assertEqual(datetime_filter(dt, '%Y-%m-%d'), '2023-05-15')
        self.assertEqual(datetime_filter(dt, '%H:%M'), '14:30')

    def test_datetime_filter_with_isoformat_string(self):
        """Test filtra datetime_filter z ciągiem w formacie ISO."""
        # Testowanie z ciągiem w formacie ISO
        iso_str = '2023-05-15T14:30:00Z'
        self.assertEqual(datetime_filter(iso_str), '15-05-2023 14:30')
        self.assertEqual(datetime_filter(iso_str, '%Y-%m-%d'), '2023-05-15')
        self.assertEqual(datetime_filter(iso_str, '%H:%M'), '14:30')

    def test_datetime_filter_with_none(self):
        """Test filtra datetime_filter z None."""
        # Testowanie z None
        self.assertEqual(datetime_filter(None), '')


if __name__ == '__main__':
    unittest.main() 