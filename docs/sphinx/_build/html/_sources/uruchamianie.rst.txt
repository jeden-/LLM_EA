###########
Uruchamianie
###########

W tym rozdziale znajdziesz informacje na temat różnych sposobów uruchamiania systemu LLM Trading.

Wymagania wstępne
================

Przed uruchomieniem systemu upewnij się, że:

1. Wszystkie komponenty zostały poprawnie zainstalowane (patrz: :doc:`instalacja`)
2. Plik ``.env`` został skonfigurowany odpowiednio do Twoich potrzeb
3. MetaTrader 5 jest zainstalowany i skonfigurowany
4. Expert Advisor jest zainstalowany w MetaTrader 5
5. Plik konfiguracyjny dla odpowiedniego środowiska istnieje w katalogu ``config/``

Uruchomienie całego systemu
==========================

Najprostszym sposobem uruchomienia całego systemu jest użycie głównego skryptu:

.. code-block:: bash

   python -m scripts.run_system --env dev

Opcje uruchomienia:

* ``--env`` - środowisko [dev|test|prod], domyślnie ``dev``
* ``--debug`` - uruchomienie w trybie debugowania
* ``--components`` - lista komponentów do uruchomienia, oddzielona spacjami

Przykłady użycia:

.. code-block:: bash

   # Uruchomienie w środowisku deweloperskim
   python -m scripts.run_system --env dev

   # Uruchomienie w trybie debug
   python -m scripts.run_system --env dev --debug

   # Uruchomienie tylko wybranych komponentów
   python -m scripts.run_system --env dev --components database dashboard

Uruchamianie poszczególnych komponentów
======================================

Każdy komponent systemu można uruchomić niezależnie, co jest przydatne podczas prac rozwojowych lub testowania:

Database
--------

.. code-block:: bash

   python -m Database.run_database --env dev

MT5_Connector
------------

.. code-block:: bash

   python -m MT5_Connector.run_connector --env dev

LLM_Engine
---------

.. code-block:: bash

   python -m LLM_Engine.run_engine --env dev

Agent_Manager
-----------

.. code-block:: bash

   python -m Agent_Manager.run_manager --env dev

Dashboard
--------

.. code-block:: bash

   python -m Dashboard.run_dashboard --env dev --port 5000

Opcja ``--port`` pozwala określić port, na którym będzie dostępny dashboard (domyślnie 5000).

Skrypty pomocnicze
==================

Inicjalizacja bazy danych
-------------------------

Przed pierwszym uruchomieniem systemu należy utworzyć strukturę bazy danych:

.. code-block:: bash

   python -m scripts.setup_database --init

Konfiguracja środowiska
-----------------------

Skrypt tworzy niezbędne katalogi i pliki:

.. code-block:: bash

   python -m scripts.setup_environment --env dev

Jednorazowa analiza rynku
------------------------

Możesz uruchomić jednorazową analizę konkretnego instrumentu:

.. code-block:: bash

   python -m scripts.run_analysis --symbol EURUSD --timeframe H1

Możliwe wartości dla parametru ``--timeframe``: M1, M5, M15, M30, H1, H4, D1, W1, MN1.

Monitorowanie systemu
====================

Monitorowanie w czasie rzeczywistym
----------------------------------

Najwygodniejszym sposobem monitorowania systemu jest dashboard webowy, dostępny domyślnie pod adresem:

``http://localhost:5000``

Możesz monitorować:

* Stan poszczególnych komponentów
* Aktualnie otwarte pozycje
* Historię transakcji
* Statystyki skuteczności
* Logi systemowe

Monitorowanie w trybie tekstowym
-------------------------------

Możesz również monitorować działanie systemu poprzez dedykowany skrypt:

.. code-block:: bash

   python -m scripts.monitor_system

Logi systemowe
-------------

Wszystkie logi systemu są zapisywane w katalogu ``logs/``:

* ``logs/agent_manager/`` - logi modułu zarządzającego
* ``logs/dashboard/`` - logi interfejsu webowego
* ``logs/database/`` - logi bazy danych
* ``logs/errors/`` - błędy z całego systemu
* ``logs/llm_engine/`` - logi silnika LLM
* ``logs/monitoring/`` - logi monitorowania
* ``logs/mt5_connector/`` - logi łącznika z MT5
* ``logs/performance/`` - logi wydajności
* ``logs/trades/`` - logi dotyczące transakcji

Zatrzymywanie systemu
====================

Zatrzymanie całego systemu
-------------------------

Aby zatrzymać wszystkie komponenty uruchomione przez ``run_system``:

* Wciśnij ``Ctrl+C`` w terminalu, w którym uruchomiono system
* Lub użyj polecenia: ``python -m scripts.run_system --stop``

Zatrzymanie pojedynczego komponentu
----------------------------------

Jeśli komponent został uruchomiony w osobnym terminalu, możesz go zatrzymać naciskając ``Ctrl+C``.

Automatyczny restart
===================

System posiada mechanizm automatycznego restartu komponentów w przypadku awarii. Jeśli któryś z komponentów zakończy działanie z błędem, zostanie automatycznie ponownie uruchomiony.

Możesz wyłączyć tę funkcję uruchamiając system z parametrem ``--no-auto-restart``:

.. code-block:: bash

   python -m scripts.run_system --env dev --no-auto-restart

Uruchamianie w środowisku produkcyjnym
=====================================

W środowisku produkcyjnym zaleca się:

1. Uruchomienie systemu z parametrem ``--env prod``
2. Użycie narzędzia do zarządzania procesami, takiego jak systemd lub supervisord
3. Monitorowanie stanu systemu za pomocą zewnętrznych narzędzi
4. Skonfigurowanie alertów w przypadku awarii

Przykładowa konfiguracja dla supervisord:

.. code-block:: ini

   [program:llm_trading]
   command=python -m scripts.run_system --env prod
   directory=/path/to/llm-trading
   autostart=true
   autorestart=true
   startretries=3
   stderr_logfile=/var/log/llm_trading.err.log
   stdout_logfile=/var/log/llm_trading.out.log
   user=username

Rozwiązywanie problemów
======================

Najczęstsze problemy przy uruchamianiu:

1. **Problem z połączeniem do MT5**

   * Sprawdź, czy MT5 jest uruchomiony
   * Sprawdź dane logowania w pliku ``.env``
   * Sprawdź logi w ``logs/mt5_connector/``

2. **Problem z modelem LLM**

   * Sprawdź, czy Ollama jest poprawnie zainstalowane
   * Sprawdź, czy model Deepseek jest dostępny
   * Sprawdź logi w ``logs/llm_engine/``

3. **Problem z bazą danych**

   * Sprawdź, czy baza danych została zainicjalizowana
   * Sprawdź uprawnienia do katalogów
   * Sprawdź logi w ``logs/database/``

4. **System się uruchamia, ale nie handluje**

   * Sprawdź, czy Expert Advisor jest załadowany na wykres w MT5
   * Sprawdź, czy w MT5 włączony jest trading algorytmiczny
   * Sprawdź logi w ``logs/agent_manager/`` i ``logs/trades/`` 