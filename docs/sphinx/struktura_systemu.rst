#################
Struktura systemu
#################

Ten dokument opisuje strukturę projektu, wzajemne zależności komponentów oraz sposób organizacji plików i folderów w systemie handlowym LLM Trading.

Główna struktura katalogów
==========================

.. code-block:: none

   LLM_EA/
     ├── Agent_Manager/        # Moduł zarządzania strategiami i agentami
     ├── Common/               # Wspólne klasy i funkcje używane w wielu modułach
     ├── Dashboard/            # Interfejs webowy do monitorowania systemu
     ├── Database/             # Moduł obsługi bazy danych
     ├── Expert_Advisor/       # Kody dla MT5 Expert Advisors
     ├── LLM_Engine/           # Silnik modeli językowych do analizy rynku
     ├── MT5_Connector/        # Łącznik z platformą MetaTrader 5
     ├── config/               # Pliki konfiguracyjne
     ├── docs/                 # Dokumentacja projektu
     ├── logs/                 # Logi aplikacji
     ├── scripts/              # Skrypty pomocnicze i uruchomieniowe
     └── tests/                # Testy jednostkowe i integracyjne

Komponenty systemu i ich struktura
==================================

Agent_Manager
-------------

.. code-block:: none

   Agent_Manager/
     ├── __init__.py
     ├── agent_manager.py       # Główna klasa zarządzająca agentami
     ├── coordinator.py         # Koordynator strategii i sygnałów
     ├── order_processor.py     # Przetwarzanie zleceń handlowych
     ├── risk_manager.py        # Zarządzanie ryzykiem
     ├── run_manager.py         # Skrypt uruchamiający komponent jako usługę
     └── strategy_manager.py    # Zarządzanie strategiami handlowymi

Dashboard
---------

.. code-block:: none

   Dashboard/
     ├── __init__.py
     ├── dashboard.py           # Implementacja aplikacji Flask 
     ├── run_dashboard.py       # Skrypt uruchamiający komponent jako usługę
     ├── static/                # Pliki statyczne (CSS, JS, obrazy)
     │   ├── charts/
     │   ├── css/
     │   ├── img/
     │   └── js/
     └── templates/             # Szablony HTML

Database
--------

.. code-block:: none

   Database/
     ├── __init__.py
     ├── database.py            # Główna klasa obsługi bazy danych
     └── run_database.py        # Skrypt uruchamiający komponent jako usługę

LLM_Engine
----------

.. code-block:: none

   LLM_Engine/
     ├── __init__.py
     ├── advanced_indicators.py         # Zaawansowane wskaźniki techniczne
     ├── cache_manager.py               # Zarządzanie cache dla modeli LLM
     ├── config.py                      # Konfiguracja silnika LLM
     ├── grok_client.py                 # Klient API dla modelu Grok
     ├── llm_client.py                  # Abstrakcyjny klient dla modeli LLM
     ├── llm_engine.py                  # Główna klasa silnika LLM
     ├── llm_interface.py               # Interfejs komunikacji z modelami LLM
     ├── market_analysis.py             # Analiza rynku
     ├── market_analyzer.py             # Analizator danych rynkowych
     ├── market_data.py                 # Klasy do obsługi danych rynkowych
     ├── prompt_builder.py              # Budowanie promptów dla modeli
     ├── prompt_templates.py            # Szablony promptów
     ├── response_parser.py             # Parsowanie odpowiedzi z modeli
     ├── run_engine.py                  # Skrypt uruchamiający komponent jako usługę
     ├── technical_indicators.py        # Podstawowe wskaźniki techniczne
     └── utils.py                       # Funkcje pomocnicze

MT5_Connector
-------------

.. code-block:: none

   MT5_Connector/
     ├── __init__.py
     ├── candlestick_patterns.py        # Wykrywanie formacji świecowych
     ├── connector.py                   # Główna klasa łącznika z MT5
     ├── data_formatter.py              # Formatowanie danych z MT5
     ├── indicators.py                  # Implementacja wskaźników technicznych
     ├── mt5_client.py                  # Klient komunikacji z MT5
     ├── run_connector.py               # Skrypt uruchamiający komponent jako usługę
     └── README.md                      # Dokumentacja modułu

scripts
-------

.. code-block:: none

   scripts/
     ├── demo_llm_engine.py             # Demonstracja silnika LLM
     ├── generate_test_data.py          # Generowanie danych testowych
     ├── monitor_system.py              # Monitorowanie stanu systemu
     ├── monitoring.py                  # Skrypt monitorowania jako usługa
     ├── mt5_connector_example.py       # Przykład użycia konektora MT5
     ├── run_agent.py                   # Uruchamianie pojedynczego agenta
     ├── run_analysis.py                # Uruchamianie analizy rynku
     ├── run_system.py                  # Główny skrypt uruchamiający wszystkie komponenty
     ├── setup.sh                       # Skrypt konfiguracji systemu (Linux/Mac)
     ├── setup_database.py              # Inicjalizacja bazy danych
     ├── setup_environment.py           # Konfiguracja środowiska
     ├── show_analysis.py               # Wyświetlanie wyników analizy
     ├── start_system.py                # Alternatywny skrypt uruchamiający komponenty
     └── validate_llm_performance.py    # Walidacja wydajności modeli LLM

Uruchamianie komponentów
========================

Sposoby uruchamiania
--------------------

System może być uruchamiany na dwa główne sposoby:

**Skrypt główny** - Uruchamia wszystkie komponenty w odpowiedniej kolejności:

.. code-block:: bash

   python -m scripts.run_system [--env dev|test|prod] [--debug] [--components component1 component2 ...]

**Komponenty pojedynczo** - Każdy komponent może być uruchomiony jako osobna usługa:

.. code-block:: bash

   python -m Agent_Manager.run_manager [--env dev|test|prod] [--debug]
   python -m Dashboard.run_dashboard [--env dev|test|prod] [--port PORT] [--debug]
   python -m MT5_Connector.run_connector [--env dev|test|prod] [--debug]
   python -m LLM_Engine.run_engine [--env dev|test|prod] [--debug]
   python -m Database.run_database [--env dev|test|prod] [--debug]

Zależności między komponentami
------------------------------

1. **Database** - Podstawowy komponent, od którego zależą pozostałe
2. **MT5_Connector** i **LLM_Engine** - Zależą od Database
3. **Agent_Manager** - Zależy od Database, MT5_Connector i LLM_Engine
4. **Dashboard** - Zależy od Database
5. **Monitoring** - Niezależny (monitoruje pozostałe komponenty)

Pliki konfiguracyjne
===================

System używa następujących plików konfiguracyjnych:

1. ``config/config_dev.json`` - Konfiguracja dla środowiska deweloperskiego
2. ``config/config_test.json`` - Konfiguracja dla środowiska testowego
3. ``config/config_prod.json`` - Konfiguracja dla środowiska produkcyjnego

Uwagi dotyczące uruchomienia
===========================

1. Przed uruchomieniem systemu należy upewnić się, że wszystkie zależności są zainstalowane:

   .. code-block:: bash

      pip install -e .

   lub:

   .. code-block:: bash

      poetry install

2. Zalecane jest utworzenie odpowiednich katalogów dla logów i danych:

   .. code-block:: bash

      python -m scripts.setup_environment --env dev

3. Inicjalizacja bazy danych (jeśli nie istnieje):

   .. code-block:: bash

      python -m scripts.setup_database --init 