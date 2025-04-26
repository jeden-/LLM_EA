"""
Testy jednostkowe dla komponentów UI dashboardu.

Ten moduł zawiera testy sprawdzające poprawność działania komponentów UI
i routingu aplikacji Flask.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
import json

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Dashboard.dashboard import app
from Database.database import DatabaseHandler
from tests.test_base_template import BASE_TEMPLATE


class TestDashboard(unittest.TestCase):
    """Testy dla komponentów dashboardu Flask."""

    def setUp(self):
        """Konfiguracja środowiska testowego przed każdym testem."""
        # Konfiguracja klienta testowego Flask
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Wyłączenie ochrony CSRF dla testów
        self.client = app.test_client()
        
        # Mockowanie bazy danych
        self.mock_db_patcher = patch('Dashboard.dashboard.db_handler')
        self.mock_db = self.mock_db_patcher.start()
        
        # Mockowanie szablonów
        self.mock_template_patcher = patch('flask.templating._render')
        self.mock_render = self.mock_template_patcher.start()
        self.mock_render.return_value = "Zmockowany szablon"
        
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        self.mock_db_patcher.stop()
        self.mock_template_patcher.stop()
    
    def test_home_page(self):
        """Test dostępu do strony głównej."""
        # Mockowanie get_trade_ideas
        self.mock_db.get_trade_ideas.return_value = []
        
        # Wykonanie zapytania
        response = self.client.get('/home')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
        
    def test_statistics_page(self):
        """Test dostępu do strony statystyk."""
        # Mockowanie get_trades
        self.mock_db.get_trades.return_value = []
        
        # Wykonanie zapytania
        response = self.client.get('/statistics')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
    
    def test_market_analysis_page(self):
        """Test dostępu do strony analiz rynkowych."""
        # Mockowanie get_analyses
        self.mock_db.get_analyses.return_value = []
        
        # Wykonanie zapytania
        response = self.client.get('/market_analysis')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
    
    def test_trade_ideas_page(self):
        """Test dostępu do strony pomysłów handlowych."""
        # Mockowanie get_trade_ideas_paginated i get_trade_ideas_stats
        self.mock_db.get_trade_ideas_paginated.return_value = (0, [])
        self.mock_db.get_trade_ideas_stats.return_value = {
            'total': 0,
            'pending': 0,
            'executed': 0,
            'expired': 0,
            'rejected': 0
        }
        
        # Wykonanie zapytania
        response = self.client.get('/trade_ideas')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
    
    def test_trade_idea_details_page_not_found(self):
        """Test dostępu do nieistniejącego pomysłu handlowego."""
        # Mockowanie get_trade_idea
        self.mock_db.get_trade_idea.return_value = None
        
        # Wykonanie zapytania do nieistniejącego ID
        response = self.client.get('/trade_idea_details/9999')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 302)  # Przekierowanie
        
    def test_trade_idea_details_page_valid(self):
        """Test dostępu do istniejącego pomysłu handlowego."""
        # Dane testowe
        test_idea = {
            'id': 1,
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'risk_reward_ratio': 2.0,
            'status': 'PENDING',
            'created_at': datetime.now().isoformat(),
            'valid_until': (datetime.now() + timedelta(days=1)).isoformat(),
            'technical_analysis': 'Test analiza techniczna',
            'fundamental_analysis': 'Test analiza fundamentalna',
            'risk_analysis': 'Test analiza ryzyka',
            'notes': 'Test notatki',
            'chart_image': None,
            'timeframe': 'H1',
            'strategy': 'Test strategia',
            'source': 'LLM',
            'risk_percentage': 1.0
        }
        
        # Mockowanie
        self.mock_db.get_trade_idea.return_value = test_idea
        self.mock_db.get_trades_by_idea_id.return_value = []
        self.mock_db.get_trade_idea_comments.return_value = []
        
        # Wykonanie zapytania
        response = self.client.get('/trade_idea_details/1')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
    
    @patch('Dashboard.dashboard.calculate_equity_curve')
    def test_api_equity_chart(self, mock_calculate_equity_curve):
        """Test API zwracającego dane dla wykresu equity."""
        # Mockowanie
        self.mock_db.get_trades.return_value = [
            {
                'id': 1,
                'entry_time': (datetime.now() - timedelta(days=5)).isoformat(),
                'exit_time': (datetime.now() - timedelta(days=4)).isoformat(),
                'profit_loss': 100.0
            },
            {
                'id': 2,
                'entry_time': (datetime.now() - timedelta(days=3)).isoformat(),
                'exit_time': (datetime.now() - timedelta(days=2)).isoformat(),
                'profit_loss': -50.0
            }
        ]
        
        # Mockowanie funkcji calculate_equity_curve
        equity_data = [
            {'date': '2023-01-01T00:00:00', 'equity': 1100},
            {'date': '2023-01-02T00:00:00', 'equity': 1050}
        ]
        mock_calculate_equity_curve.return_value = equity_data
        
        # Wykonanie zapytania
        response = self.client.get('/api/equity_chart')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        self.assertIn('date', data[0])
        self.assertIn('equity', data[0])
        self.assertEqual(data[0]['equity'], 1100)
        
    def test_add_trade_idea_form(self):
        """Test formularza dodawania pomysłu handlowego."""
        # Wykonanie zapytania GET
        response = self.client.get('/add_trade_idea')
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
        
    @patch('Dashboard.dashboard.uuid.uuid4')
    def test_add_trade_idea_submission(self, mock_uuid):
        """Test wysyłania formularza dodawania pomysłu handlowego."""
        # Mockowanie UUID
        mock_uuid.return_value = MagicMock(hex='test-uuid')
        
        # Mockowanie add_trade_idea
        self.mock_db.add_trade_idea.return_value = 1
        
        # Dane formularza
        form_data = {
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry_price': '1.1000',
            'stop_loss': '1.0950',
            'take_profit': '1.1100',
            'risk_percentage': '1.0',
            'valid_until': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'timeframe': 'H1',
            'strategy': 'Test strategia',
            'source': 'Manual',
            'technical_analysis': 'Test analiza techniczna'
        }
        
        # Wykonanie zapytania POST z pominięciem obsługi szablonów
        with patch('Dashboard.dashboard.render_template') as mock_render:
            mock_render.return_value = ""
            response = self.client.post('/add_trade_idea', data=form_data, follow_redirects=True)
        
        # Weryfikacja
        self.assertEqual(response.status_code, 200)
        self.mock_db.add_trade_idea.assert_called_once()


if __name__ == '__main__':
    unittest.main() 