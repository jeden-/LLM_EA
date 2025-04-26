############
Instalacja
############

Ta instrukcja przeprowadzi Cię przez proces instalacji, konfiguracji i uruchomienia systemu LLM Trader MT5.

Wymagania systemowe
==================

* Python 3.10 lub nowszy
* MetaTrader 5
* Konto w platformie X.AI (dla dostępu do modelu Grok)
* Około 16 GB pamięci RAM (rekomendowane)
* Około 5 GB wolnego miejsca na dysku

Kroki instalacji
===============

1. Pobranie repozytorium
-----------------------

.. code-block:: bash

   git clone https://github.com/twoj-username/llm-trader-mt5.git
   cd llm-trader-mt5

2. Instalacja pakietów i zależności
----------------------------------

Używając Poetry (zalecane)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Instalacja Poetry, jeśli nie jest zainstalowane
   curl -sSL https://install.python-poetry.org | python3 -

   # Instalacja zależności projektu
   poetry install

Używając pip
^^^^^^^^^^^

.. code-block:: bash

   # Stworzenie wirtualnego środowiska
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # lub
   venv\Scripts\activate.bat  # Windows

   # Instalacja zależności
   pip install -r requirements.txt

3. Konfiguracja środowiska
-------------------------

Utwórz plik ``.env`` na podstawie szablonu ``.env.example``:

.. code-block:: bash

   cp .env.example .env

Otwórz plik ``.env`` i wprowadź odpowiednie wartości:

* ``X_API_KEY`` - Twój klucz API X.AI
* ``MT5_USERNAME``, ``MT5_PASSWORD``, ``MT5_SERVER`` - dane logowania do MT5
* ``MT5_PATH`` - ścieżka do instalacji MT5
* Dostosuj pozostałe parametry według potrzeb

4. Instalacja Expert Advisor w MetaTrader 5
-----------------------------------------

1. Otwórz MetaTrader 5
2. Przejdź do "File" > "Open Data Folder"
3. Przejdź do folderu "MQL5/Experts/"
4. Skopiuj pliki z katalogu ``Expert_Advisor`` projektu do tego folderu
5. Skompiluj EA w edytorze MetaEditor

5. Inicjalizacja bazy danych
---------------------------

.. code-block:: bash

   # Użyj automatycznego skryptu inicjalizacji
   poetry run python -m scripts.setup_database

6. Konfiguracja strategii handlowej
---------------------------------

Dostosuj parametry strategii handlowej w pliku ``.env``:

* ``DEFAULT_RISK_PERCENTAGE`` - domyślny procent ryzyka na transakcję
* ``MAX_DAILY_RISK_PERCENTAGE`` - maksymalny dzienny procent ryzyka
* ``MAX_POSITIONS`` - maksymalna liczba otwartych pozycji
* ``TRADING_SYMBOLS`` - lista par walutowych do handlu

Uruchamianie systemu
===================

System składa się z kilku komponentów, które można uruchomić niezależnie:

1. Uruchomienie agenta handlowego
--------------------------------

.. code-block:: bash

   poetry run python -m scripts.run_agent

2. Uruchomienie dashboardu
------------------------

Aby uruchomić dashboardu, wykonaj:

.. code-block:: bash

   poetry run python -m Dashboard.run_dashboard

Domyślnie dashboard zostanie uruchomiony na porcie 5000. Aby zmienić port:

.. code-block:: bash

   poetry run python -m Dashboard.run_dashboard --port 8080

3. Jednorazowa analiza rynku
--------------------------

.. code-block:: bash

   poetry run python -m scripts.run_analysis --symbol EURUSD --timeframe H1

Konfiguracja produkcyjna
=======================

W środowisku produkcyjnym zaleca się:

1. Ustawienie ``TRADING_MODE=LIVE`` w pliku ``.env``
2. Wyłączenie debugowania: ``DEBUG=False`` i ``FLASK_DEBUG=0``
3. Zmianę klucza ``FLASK_SECRET_KEY`` na bezpieczny, losowy ciąg znaków
4. Skonfigurowanie regularnych kopii zapasowych bazy danych

Rozwiązywanie problemów
======================

Problemy z połączeniem z MT5
---------------------------

1. Upewnij się, że MT5 jest uruchomiony
2. Sprawdź, czy EA jest prawidłowo skonfigurowany i załadowany na wykres
3. Sprawdź poprawność danych logowania w pliku ``.env``
4. Sprawdź logi w folderze ``logs/``

Problemy z API Grok
------------------

1. Sprawdź poprawność klucza API
2. Sprawdź, czy masz wystarczający limit zapytań
3. Sprawdź połączenie internetowe

Aktualizacja
==========

Aby zaktualizować system do najnowszej wersji:

.. code-block:: bash

   git pull
   poetry install
   python -m scripts.setup_database --update

Bezpieczeństwo
============

* Zawsze przechowuj plik ``.env`` w bezpiecznym miejscu
* Nie udostępniaj swojego klucza API
* Regularnie twórz kopie zapasowe bazy danych
* Na początku handluj na koncie demo i małymi kwotami 