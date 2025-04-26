"""
Testy jednostkowe dla funkcji pomocniczych dashboardu.

Ten moduł zawiera testy sprawdzające poprawność działania funkcji pomocniczych
używanych w aplikacji dashboardu.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Dashboard.dashboard import (
    calculate_statistics,
    calculate_equity_curve,
    allowed_file
)


class TestDashboardUtils(unittest.TestCase):
    """Testy dla funkcji pomocniczych dashboardu."""

    def test_allowed_file(self):
        """Test funkcji allowed_file sprawdzającej rozszerzenia plików."""
        # Poprawne rozszerzenia
        self.assertTrue(allowed_file('chart.png'))
        self.assertTrue(allowed_file('chart.jpg'))
        self.assertTrue(allowed_file('chart.jpeg'))
        self.assertTrue(allowed_file('chart.gif'))
        
        # Niepoprawne rozszerzenia
        self.assertFalse(allowed_file('script.js'))
        self.assertFalse(allowed_file('style.css'))
        self.assertFalse(allowed_file('document.pdf'))
        self.assertFalse(allowed_file('data.csv'))
        self.assertFalse(allowed_file('file'))  # Bez rozszerzenia

    def test_calculate_statistics_empty(self):
        """Test funkcji calculate_statistics z pustą listą transakcji."""
        # Testowanie z pustą listą transakcji
        stats = calculate_statistics([])
        
        # Weryfikacja
        self.assertEqual(stats['total_trades'], 0)
        self.assertEqual(stats['winning_trades'], 0)
        self.assertEqual(stats['losing_trades'], 0)
        self.assertEqual(stats['win_rate'], 0)
        self.assertEqual(stats['total_profit'], 0)
        self.assertEqual(stats['total_loss'], 0)
        self.assertEqual(stats['net_profit'], 0)
        self.assertEqual(stats['profit_factor'], 0)
        self.assertEqual(stats['avg_profit'], 0)
        self.assertEqual(stats['avg_loss'], 0)
        self.assertEqual(stats['largest_profit'], 0)
        self.assertEqual(stats['largest_loss'], 0)

    def test_calculate_statistics_with_trades(self):
        """Test funkcji calculate_statistics z listą transakcji."""
        # Testowanie z listą transakcji
        trades = [
            {'profit_loss': 100.0, 'symbol': 'EURUSD', 'volume': 0.1},
            {'profit_loss': -50.0, 'symbol': 'EURUSD', 'volume': 0.1},
            {'profit_loss': 200.0, 'symbol': 'GBPUSD', 'volume': 0.2},
            {'profit_loss': 150.0, 'symbol': 'USDJPY', 'volume': 0.3},
            {'profit_loss': -75.0, 'symbol': 'GBPUSD', 'volume': 0.1}
        ]
        
        stats = calculate_statistics(trades)
        
        # Weryfikacja
        self.assertEqual(stats['total_trades'], 5)
        self.assertEqual(stats['winning_trades'], 3)
        self.assertEqual(stats['losing_trades'], 2)
        self.assertEqual(stats['win_rate'], 60)
        self.assertEqual(stats['total_profit'], 450)
        self.assertEqual(stats['total_loss'], 125)
        self.assertEqual(stats['net_profit'], 325)
        self.assertAlmostEqual(float(stats['profit_factor']), 3.6, places=1)
        self.assertEqual(stats['avg_profit'], 150)
        self.assertEqual(stats['avg_loss'], 62.5)
        self.assertEqual(stats['largest_profit'], 200)
        self.assertEqual(stats['largest_loss'], 75)

    def test_calculate_equity_curve(self):
        """Test funkcji calculate_equity_curve."""
        # Testowanie z listą transakcji
        today = datetime.now()
        trades = [
            {
                'id': 1,
                'entry_time': (today - timedelta(days=5)).isoformat(),
                'close_time': (today - timedelta(days=4)).isoformat(),
                'profit_loss': 100.0
            },
            {
                'id': 2,
                'entry_time': (today - timedelta(days=3)).isoformat(),
                'close_time': (today - timedelta(days=2)).isoformat(),
                'profit_loss': -50.0
            },
            {
                'id': 3,
                'entry_time': (today - timedelta(days=1)).isoformat(),
                'close_time': today.isoformat(),
                'profit_loss': 200.0
            }
        ]
        
        curve = calculate_equity_curve(trades)
        
        # Weryfikacja
        self.assertEqual(len(curve), 3)  # 3 punkty (po jednym na transakcję)
        
        # Sprawdzenie przyrostowych wartości equity
        self.assertEqual(curve[0]['equity'], 1100)  # 1000 + 100
        self.assertEqual(curve[1]['equity'], 1050)  # 1100 - 50
        self.assertEqual(curve[2]['equity'], 1250)  # 1050 + 200
        
        # Sprawdzenie, czy punkty mają daty
        self.assertIn('date', curve[0])
        self.assertIn('date', curve[1])
        self.assertIn('date', curve[2])


if __name__ == '__main__':
    unittest.main() 