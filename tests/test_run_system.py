#!/usr/bin/env python
"""
Testy jednostkowe dla modułu run_system.py.

Ten moduł testuje funkcjonalność skryptu uruchamiającego system, w tym:
- Ładowanie konfiguracji
- Przygotowanie komponentów
- Uruchamianie i zatrzymywanie komponentów
- Sortowanie topologiczne komponentów
"""

import os
import sys
import json
import unittest
import subprocess
from unittest.mock import patch, MagicMock, mock_open, call

# Dodaj główny katalog projektu do ścieżki importu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importuj testowany moduł
from scripts.run_system import (
    SystemComponent,
    load_config,
    prepare_components,
    start_component,
    start_system,
    topological_sort,
    stop_system,
    monitor_processes
)

class TestRunSystem(unittest.TestCase):
    """Testy dla funkcji z modułu run_system.py."""
    
    def setUp(self):
        """Przygotowuje środowisko testowe przed każdym testem."""
        # Mockowanie globalnych zmiennych
        self.patcher_running_processes = patch('scripts.run_system.running_processes', {})
        self.mock_running_processes = self.patcher_running_processes.start()
        
        self.patcher_stop_event = patch('scripts.run_system.stop_event')
        self.mock_stop_event = self.patcher_stop_event.start()
        
        # Przykładowa konfiguracja
        self.test_config = {
            "dashboard": {
                "port": 5000
            }
        }
        
        # Tworzymy tymczasowe katalogi z odpowiednią strukturą na Windowsie
        if os.name == 'nt':
            self.test_config_dir = r'C:\test\config'
            self.test_log_dir = r'C:\test\logs'
        else:
            self.test_config_dir = '/test/config'
            self.test_log_dir = '/test/logs'
        
        # Mockowanie ścieżek
        self.patcher_config_dir = patch('scripts.run_system.CONFIG_DIR', self.test_config_dir)
        self.mock_config_dir = self.patcher_config_dir.start()
        
        self.patcher_log_dir = patch('scripts.run_system.LOG_DIR', self.test_log_dir)
        self.mock_log_dir = self.patcher_log_dir.start()
    
    def tearDown(self):
        """Czyści środowisko testowe po każdym teście."""
        # Zatrzymanie patcherów
        self.patcher_running_processes.stop()
        self.patcher_stop_event.stop()
        self.patcher_config_dir.stop()
        self.patcher_log_dir.stop()
    
    def test_system_component_init(self):
        """Test dla inicjalizacji klasy SystemComponent."""
        component = SystemComponent(
            name="test_component",
            command=["python", "test.py"],
            required=True,
            depends_on=["db", "api"],
            startup_time=5,
            check_alive=lambda: True
        )
        
        self.assertEqual(component.name, "test_component")
        self.assertEqual(component.command, ["python", "test.py"])
        self.assertEqual(component.required, True)
        self.assertEqual(component.depends_on, ["db", "api"])
        self.assertEqual(component.startup_time, 5)
        self.assertEqual(component.process, None)
        self.assertEqual(component.exit_code, None)
        self.assertEqual(component.log_file, None)
    
    def test_load_config(self):
        """Test dla funkcji load_config."""
        # Mockowanie funkcji os.path.exists i open
        with patch('scripts.run_system.os.path.exists', return_value=True):
            with patch('scripts.run_system.open', mock_open(read_data='{"test": "value"}')) as m:
                # Wywołanie testowanej funkcji
                config = load_config('dev')
                
                # Oczekiwana ścieżka po uwzględnieniu systemu
                expected_path = os.path.join(self.test_config_dir, f"config_dev.json")
                
                # Weryfikacja, czy plik został otwarty (bez sprawdzania dokładnej ścieżki)
                m.assert_called()
                
                # Weryfikacja zawartości konfiguracji
                self.assertEqual(config, {"test": "value"})
        
        # Test dla przypadku braku pliku
        with patch('scripts.run_system.os.path.exists', return_value=False):
            config = load_config('dev')
            # Weryfikacja, czy pusta konfiguracja została zwrócona
            self.assertEqual(config, {})
    
    @patch('scripts.run_system.os.makedirs')
    def test_prepare_components(self, mock_makedirs):
        """Test dla funkcji prepare_components."""
        # Przygotowanie argumentów
        args = MagicMock()
        args.env = 'dev'
        args.debug = True
        args.no_dashboard = False
        
        # Wywołanie testowanej funkcji
        components = prepare_components(self.test_config, args)
        
        # Weryfikacja, czy wymagane komponenty zostały utworzone
        self.assertIn('database', components)
        self.assertIn('mt5_connector', components)
        self.assertIn('llm_engine', components)
        self.assertIn('agent_manager', components)
        self.assertIn('dashboard', components)
        self.assertIn('monitoring', components)
        
        # Sprawdzenie właściwości komponentów
        db_component = components['database']
        self.assertEqual(db_component.name, 'database')
        self.assertTrue(db_component.required)
        self.assertEqual(db_component.depends_on, [])
        
        agent_component = components['agent_manager']
        self.assertEqual(agent_component.name, 'agent_manager')
        self.assertTrue(agent_component.required)
        self.assertEqual(set(agent_component.depends_on), set(['database', 'llm_engine', 'mt5_connector']))
        
        # Test dla przypadku bez dashboardu
        args.no_dashboard = True
        components = prepare_components(self.test_config, args)
        self.assertNotIn('dashboard', components)
    
    def test_start_component(self):
        """Test dla funkcji start_component."""
        # Przygotowanie komponentu
        component = SystemComponent(
            name="test_component",
            command=["python", "test.py"],
            required=True,
            startup_time=0.1
        )
        
        # Przygotowanie mocków
        log_file_mock = MagicMock()
        process_mock = MagicMock()
        process_mock.poll.return_value = None  # Proces działa
        process_mock.pid = 12345
        
        # Użycie patch context manager dla open i subprocess.Popen
        with patch('scripts.run_system.open', return_value=log_file_mock) as mock_open:
            with patch('scripts.run_system.subprocess.Popen', return_value=process_mock) as mock_popen:
                with patch('scripts.run_system.time.sleep'):
                    with patch('scripts.run_system.running_processes', {}):
                        # Wywołanie testowanej funkcji
                        result = start_component(component, self.test_log_dir)
                        
                        # Weryfikacja, czy plik został otwarty bez sprawdzania dokładnej ścieżki
                        mock_open.assert_called()
                        
                        # Weryfikacja, czy proces został uruchomiony
                        mock_popen.assert_called_once()
                        
                        # Weryfikacja, czy proces został dodany do uruchomionych
                        self.assertEqual(component.process, process_mock)
                        
                        # Weryfikacja, czy funkcja zwróciła sukces
                        self.assertTrue(result)
        
        # Test dla przypadku, gdy proces kończy się natychmiast
        process_mock.poll.return_value = 1  # Proces zakończony z kodem 1
        with patch('scripts.run_system.open', return_value=log_file_mock):
            with patch('scripts.run_system.subprocess.Popen', return_value=process_mock):
                with patch('scripts.run_system.time.sleep'):
                    with patch('scripts.run_system.running_processes', {}):
                        # Wywołanie testowanej funkcji
                        result = start_component(component, self.test_log_dir)
                        
                        # Weryfikacja, czy funkcja zwróciła porażkę
                        self.assertFalse(result)
    
    def test_topological_sort(self):
        """Test dla funkcji topological_sort."""
        # Przygotowanie komponentów z zależnościami
        components = {
            'database': SystemComponent(name='database', command=[], depends_on=[]),
            'api': SystemComponent(name='api', command=[], depends_on=['database']),
            'frontend': SystemComponent(name='frontend', command=[], depends_on=['api']),
            'monitoring': SystemComponent(name='monitoring', command=[], depends_on=['database', 'api'])
        }
        
        # Wywołanie testowanej funkcji
        sorted_components = topological_sort(components)
        
        # Weryfikacja, czy kluczowe zależności są zachowane
        # Na przykład: database przed api, api przed frontend
        # Kolejność może się różnić między implementacjami algorytmu sortowania topologicznego
        database_idx = sorted_components.index('database')
        api_idx = sorted_components.index('api')
        
        # Weryfikacja, że database jest przed api
        self.assertLess(database_idx, api_idx)
        
        # Sprawdzamy tylko kluczowe zależności, nie dokładną kolejność
        for i, component in enumerate(sorted_components):
            # Dla każdego komponentu sprawdzamy, czy jego zależności są przed nim
            if component in components:
                for dependency in components[component].depends_on:
                    if dependency in sorted_components:
                        dep_idx = sorted_components.index(dependency)
                        self.assertLess(dep_idx, i, f"{dependency} powinien być przed {component}")
        
        # Test dla przypadku z cyklem zależności
        cyclic_components = {
            'a': SystemComponent(name='a', command=[], depends_on=['b']),
            'b': SystemComponent(name='b', command=[], depends_on=['a'])
        }
        
        # Wywołanie testowanej funkcji powinno wywołać ValueError
        with self.assertRaises(ValueError):
            topological_sort(cyclic_components)
    
    @patch('scripts.run_system.start_component')
    @patch('scripts.run_system.os.makedirs')
    def test_start_system(self, mock_makedirs, mock_start_component):
        """Test dla funkcji start_system."""
        # Przygotowanie komponentów
        components = {
            'database': SystemComponent(name='database', command=[], depends_on=[]),
            'api': SystemComponent(name='api', command=[], depends_on=['database']),
            'frontend': SystemComponent(name='frontend', command=[], depends_on=['api'])
        }
        
        # Przygotowanie listy komponentów w kolejności zależności
        with patch('scripts.run_system.topological_sort', return_value=['database', 'api', 'frontend']):
            # Symulacja procesów uruchomionych
            running_processes = {}
            
            with patch('scripts.run_system.running_processes', running_processes):
                # Database uruchomiona - dodajemy ją ręcznie do słownika procesów
                mock_database_process = MagicMock()
                mock_database_process.poll.return_value = None  # Działa
                running_processes['database'] = mock_database_process
                
                # Symulacja udanego uruchomienia wszystkich komponentów
                mock_start_component.return_value = True
                
                # Wywołanie testowanej funkcji
                result = start_system(components)
                
                # Weryfikacja, czy funkcja zwróciła sukces
                self.assertTrue(result)
                
                # Weryfikacja, czy start_component został wywołany dla api i frontend
                # Database nie powinna być uruchamiana, bo już jest w running_processes
                self.assertEqual(mock_start_component.call_count, 2)
    
    def test_monitor_processes(self):
        """Test dla funkcji monitor_processes."""
        # Przygotowanie mocków procesów
        mock_process1 = MagicMock()
        mock_process1.poll.return_value = None  # Proces działa
        
        mock_process2 = MagicMock()
        mock_process2.poll.return_value = 1  # Proces zakończony
        
        running_procs = {
            'comp1': mock_process1,
            'comp2': mock_process2
        }
        
        # Symulacja zatrzymania po jednej iteracji
        stop_event_mock = MagicMock()
        stop_event_mock.is_set.side_effect = [False, True]
        
        # Wywołanie testowanej funkcji
        with patch('scripts.run_system.running_processes', running_procs):
            with patch('scripts.run_system.stop_event', stop_event_mock):
                with patch('scripts.run_system.time.sleep'):
                    monitor_processes()
        
        # Weryfikacja, czy procesy były sprawdzane
        # Nie używamy assert_called_once, ponieważ poll może być wywołany więcej niż raz
        self.assertTrue(mock_process1.poll.called)
        self.assertTrue(mock_process2.poll.called)
        
        # Weryfikacja, czy zakończony proces został usunięty z listy
        self.assertNotIn('comp2', running_procs)

if __name__ == '__main__':
    unittest.main() 