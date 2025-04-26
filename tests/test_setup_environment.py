#!/usr/bin/env python
"""
Testy jednostkowe dla modułu setup_environment.py.

Ten moduł testuje funkcjonalność skryptu konfigurującego środowisko, w tym:
- Tworzenie katalogów
- Konfigurowanie pliku .env
- Tworzenie plików konfiguracyjnych
- Weryfikację konfiguracji
"""

import os
import sys
import json
import shutil
import unittest
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# Dodaj główny katalog projektu do ścieżki importu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importuj testowany moduł
from scripts.setup_environment import (
    is_windows,
    is_linux,
    create_necessary_dirs,
    setup_env_file,
    create_config_files,
    verify_configuration,
    ENVIRONMENT_CONFIGS
)

class TestSetupEnvironment(unittest.TestCase):
    """Testy dla funkcji z modułu setup_environment.py."""
    
    def setUp(self):
        """Przygotowuje środowisko testowe przed każdym testem."""
        # Utworzenie tymczasowego katalogu na dane testowe
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_project_dir = self.temp_dir.name
        
        # Podmiana ścieżki projektu na tymczasową
        self.patcher_project_dir = patch('scripts.setup_environment.project_dir', self.test_project_dir)
        self.mock_project_dir = self.patcher_project_dir.start()
        
        # Utworzenie tymczasowych ścieżek dla plików konfiguracyjnych
        self.test_config_dir = os.path.join(self.test_project_dir, 'config')
        self.test_log_dir = os.path.join(self.test_project_dir, 'logs')
        self.test_env_file = os.path.join(self.test_project_dir, '.env')
        
        # Patcher dla CONFIG_DIR
        self.patcher_config_dir = patch('scripts.setup_environment.CONFIG_DIR', self.test_config_dir)
        self.mock_config_dir = self.patcher_config_dir.start()
        
        # Patcher dla LOG_DIR
        self.patcher_log_dir = patch('scripts.setup_environment.LOG_DIR', self.test_log_dir)
        self.mock_log_dir = self.patcher_log_dir.start()
        
        # Patcher dla ENV_FILE
        self.patcher_env_file = patch('scripts.setup_environment.ENV_FILE', self.test_env_file)
        self.mock_env_file = self.patcher_env_file.start()
        
        # Patcher dla NECESSARY_DIRS
        self.necessary_dirs = [
            self.test_config_dir,
            self.test_log_dir,
            os.path.join(self.test_log_dir, 'monitoring'),
            os.path.join(self.test_project_dir, 'cache'),
        ]
        self.patcher_necessary_dirs = patch('scripts.setup_environment.NECESSARY_DIRS', self.necessary_dirs)
        self.mock_necessary_dirs = self.patcher_necessary_dirs.start()
    
    def tearDown(self):
        """Czyści środowisko testowe po każdym teście."""
        # Zatrzymanie patcherów
        self.patcher_project_dir.stop()
        self.patcher_config_dir.stop()
        self.patcher_log_dir.stop()
        self.patcher_env_file.stop()
        self.patcher_necessary_dirs.stop()
        
        # Usunięcie tymczasowego katalogu
        self.temp_dir.cleanup()
    
    def test_is_windows_linux(self):
        """Test dla funkcji is_windows i is_linux."""
        with patch('scripts.setup_environment.platform.system', return_value='Windows'):
            self.assertTrue(is_windows())
            self.assertFalse(is_linux())
        
        with patch('scripts.setup_environment.platform.system', return_value='Linux'):
            self.assertFalse(is_windows())
            self.assertTrue(is_linux())
    
    def test_create_necessary_dirs(self):
        """Test dla funkcji create_necessary_dirs."""
        # Wywołanie testowanej funkcji
        create_necessary_dirs()
        
        # Sprawdzenie, czy katalogi zostały utworzone
        for directory in self.necessary_dirs:
            self.assertTrue(os.path.exists(directory))
            self.assertTrue(os.path.isdir(directory))
    
    @patch('scripts.setup_environment.open', new_callable=mock_open)
    def test_setup_env_file_new(self, mock_file_open):
        """Test dla funkcji setup_env_file gdy nie ma istniejącego pliku .env."""
        # Symulacja braku pliku .env
        with patch('scripts.setup_environment.os.path.exists', return_value=False):
            setup_env_file('dev')
        
        # Sprawdzenie czy plik został otwarty do zapisu
        mock_file_open.assert_called_once_with(self.test_env_file, 'w')
        
        # Sprawdzenie zawartości zapisanego pliku
        handle = mock_file_open()
        written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
        
        # Upewnij się, że kluczowe zmienne są ustawione
        self.assertIn('ENVIRONMENT=dev', written_content)
        self.assertIn('LOG_LEVEL=DEBUG', written_content)
        self.assertIn('DEBUG=True', written_content)
        self.assertIn('USE_MOCK_DATA=True', written_content)
    
    @patch('builtins.open', new_callable=mock_open, read_data="""
    # Istniejący plik .env
    ENVIRONMENT=prod
    LOG_LEVEL=WARNING
    DEBUG=False
    MT5_SERVER=real.broker.com:443
    API_KEY=real_api_key_xyz
    CUSTOM_VAR=custom_value
    """)
    def test_setup_env_file_existing(self, mock_open_file):
        """Test dla funkcji setup_env_file gdy istnieje plik .env."""
        # Symulacja istnienia pliku .env
        with patch('scripts.setup_environment.os.path.exists', return_value=True):
            # Wywołanie testowanej funkcji
            setup_env_file('prod')
        
        # Sprawdzenie, czy plik został otwarty do odczytu a następnie do zapisu
        mock_open_file.assert_any_call(self.test_env_file, 'r')
        mock_open_file.assert_any_call(self.test_env_file, 'w')
        
        # Sprawdzenie, czy wszystkie operacje zapisu zawierają kluczowe zmienne
        # Tutaj nie możemy sprawdzić bezpośrednio zawartości pliku, więc sprawdzamy
        # czy liczba operacji zapisu jest odpowiednia
        self.assertGreaterEqual(mock_open_file().write.call_count, 3)
    
    @patch('scripts.setup_environment.json.dump')
    @patch('scripts.setup_environment.open', new_callable=mock_open)
    @patch('scripts.setup_environment.os.symlink')
    def test_create_config_files_linux(self, mock_symlink, mock_file_open, mock_json_dump):
        """Test dla funkcji create_config_files na systemie Linux."""
        # Symulacja systemu Linux
        with patch('scripts.setup_environment.is_windows', return_value=False):
            with patch('scripts.setup_environment.is_linux', return_value=True):
                # Symulacja usunięcia istniejącego pliku konfiguracyjnego
                with patch('scripts.setup_environment.os.path.exists', return_value=True):
                    with patch('scripts.setup_environment.os.remove'):
                        # Wywołanie testowanej funkcji
                        create_config_files('dev')
        
        # Weryfikacja, czy plik został otwarty do zapisu
        config_file = os.path.join(self.test_config_dir, 'config_dev.json')
        mock_file_open.assert_called_with(config_file, 'w')
        
        # Weryfikacja, czy dane zostały zapisane (json.dump wywołane)
        mock_json_dump.assert_called_once()
        
        # Sprawdzenie pierwszego argumentu dump - konfiguracja
        config = mock_json_dump.call_args[0][0]
        self.assertEqual(config["environment"], "dev")
        self.assertEqual(config["logging"]["level"], "DEBUG")
        self.assertTrue(config["dashboard"]["debug"])
        
        # Weryfikacja, czy link symboliczny został utworzony
        active_config = os.path.join(self.test_config_dir, 'config.json')
        mock_symlink.assert_called_with(config_file, active_config)
    
    @patch('scripts.setup_environment.json.dump')
    @patch('scripts.setup_environment.open', new_callable=mock_open)
    @patch('scripts.setup_environment.shutil.copy2')
    def test_create_config_files_windows(self, mock_copy2, mock_file_open, mock_json_dump):
        """Test dla funkcji create_config_files na systemie Windows."""
        # Symulacja systemu Windows
        with patch('scripts.setup_environment.is_windows', return_value=True):
            with patch('scripts.setup_environment.is_linux', return_value=False):
                # Wywołanie testowanej funkcji
                create_config_files('test')
        
        # Weryfikacja, czy plik został otwarty do zapisu
        config_file = os.path.join(self.test_config_dir, 'config_test.json')
        mock_file_open.assert_called_with(config_file, 'w')
        
        # Weryfikacja, czy dane zostały zapisane (json.dump wywołane)
        mock_json_dump.assert_called_once()
        
        # Sprawdzenie pierwszego argumentu dump - konfiguracja
        config = mock_json_dump.call_args[0][0]
        self.assertEqual(config["environment"], "test")
        self.assertEqual(config["logging"]["level"], "INFO")
        self.assertFalse(config["dashboard"]["debug"])
        
        # Weryfikacja, czy plik został skopiowany (na Windowsie)
        active_config = os.path.join(self.test_config_dir, 'config.json')
        mock_copy2.assert_called_with(config_file, active_config)
    
    @patch('scripts.setup_environment.os.path.exists')
    def test_verify_configuration_ok(self, mock_exists):
        """Test dla funkcji verify_configuration gdy wszystko jest OK."""
        # Symulacja istnienia wszystkich plików i katalogów
        mock_exists.return_value = True
        
        # Symulacja załadowanych modułów
        with patch.dict('sys.modules', {
            'pandas': MagicMock(),
            'numpy': MagicMock(),
            'requests': MagicMock(),
            'flask': MagicMock(),
            'zmq': MagicMock(),
            'dotenv': MagicMock(),
            'dotenv.load_dotenv': MagicMock()
        }):
            # Wywołanie testowanej funkcji
            issues = verify_configuration()
        
        # Sprawdzenie, czy nie ma problemów
        self.assertEqual(len(issues), 0)
    
    @patch('scripts.setup_environment.os.path.exists')
    def test_verify_configuration_issues(self, mock_exists):
        """Test dla funkcji verify_configuration gdy są problemy."""
        # Symulacja braku pliku .env i konfiguracyjnego
        def mock_path_exists(path):
            if path.endswith('.env') or path.endswith('config.json'):
                return False
            return True
        
        mock_exists.side_effect = mock_path_exists
        
        # Symulacja brakujących modułów
        orig_import = __import__
        
        def mock_import(name, *args, **kwargs):
            if name in ['zmq']:
                raise ImportError(f"No module named {name}")
            return orig_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # Wywołanie testowanej funkcji
            issues = verify_configuration()
        
        # Sprawdzenie, czy wykryto problemy
        self.assertGreaterEqual(len(issues), 2)
        self.assertTrue(any('Brak pliku .env' in x for x in issues))
        self.assertTrue(any('Brak pliku konfiguracyjnego' in x for x in issues))

if __name__ == '__main__':
    unittest.main() 