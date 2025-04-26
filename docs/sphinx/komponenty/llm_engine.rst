##########
LLM Engine
##########

LLM Engine to kluczowy komponent systemu LLM Trading, odpowiedzialny za analizę danych rynkowych z wykorzystaniem modeli językowych (LLM). Jego zadaniem jest interpretacja danych, identyfikacja potencjalnych setupów handlowych zgodnie z Metodą Master i generowanie konkretnych decyzji handlowych.

Funkcje
=======

* Analiza danych rynkowych z wykorzystaniem modeli językowych
* Identyfikacja setupów handlowych zgodnych z Metodą Master
* Generowanie decyzji handlowych (ENTER/WAIT/EXIT)
* Uzasadnianie podjętych decyzji
* Zarządzanie cache dla modeli LLM
* Obliczanie wskaźników technicznych

Struktura modułu
===============

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

Główne klasy i ich rola
======================

LLMEngine
--------

Główna klasa zarządzająca całym procesem analizy danych i podejmowania decyzji.

**Odpowiedzialności:**

* Inicjalizacja i konfiguracja komponentów silnika
* Koordynacja procesu analizy danych
* Zarządzanie cyklem życia modelu LLM
* Obsługa błędów i wyjątków

LLMClient
--------

Abstrakcyjna klasa bazowa dla różnych klientów modeli LLM. Implementacje obejmują klientów dla konkretnych modeli (np. GrokClient).

**Odpowiedzialności:**

* Komunikacja z modelem LLM
* Wysyłanie promptów i odbieranie odpowiedzi
* Obsługa limitów zapytań API
* Zarządzanie kontekstem rozmowy

PromptBuilder
-----------

Klasa odpowiedzialna za konstruowanie promptów dla modeli LLM na podstawie danych rynkowych.

**Odpowiedzialności:**

* Tworzenie skutecznych promptów dla modelu LLM
* Formatowanie danych rynkowych do formatu tekstowego
* Wykorzystanie szablonów z PromptTemplates
* Dostosowywanie promptów do konkretnych setupów handlowych

ResponseParser
------------

Klasa przetwarzająca odpowiedzi z modelu LLM na konkretne decyzje handlowe.

**Odpowiedzialności:**

* Parsowanie tekstu odpowiedzi
* Ekstrakcja decyzji handlowej (ENTER/WAIT/EXIT)
* Ekstrakcja parametrów transakcji (kierunek, stop-loss, take-profit)
* Ekstrakcja uzasadnienia decyzji

MarketAnalyzer
------------

Klasa analizująca dane rynkowe pod kątem potencjalnych setupów handlowych.

**Odpowiedzialności:**

* Analiza formacji świecowych
* Identyfikacja setupów zgodnych z Metodą Master
* Przygotowanie danych do analizy przez LLM
* Wstępna filtracja sytuacji rynkowych

TechnicalIndicators i AdvancedIndicators
--------------------------------------

Klasy implementujące podstawowe i zaawansowane wskaźniki techniczne.

**Odpowiedzialności:**

* Obliczanie wskaźników technicznych (SMA, EMA, ATR, VWAP itp.)
* Dostarczanie danych do analizy
* Optymalizacja obliczeń wskaźników

CacheManager
----------

Klasa zarządzająca cache'owaniem odpowiedzi modelu LLM.

**Odpowiedzialności:**

* Przechowywanie wyników analizy
* Optymalizacja wykorzystania modelu LLM
* Redukcja kosztów używania API

Uruchamianie
===========

LLM Engine można uruchomić jako samodzielną usługę:

.. code-block:: bash

   python -m LLM_Engine.run_engine --env dev

Parametry:

* ``--env`` - środowisko [dev|test|prod], domyślnie ``dev``
* ``--debug`` - uruchomienie w trybie debugowania

Konfiguracja
===========

Konfiguracja LLM Engine znajduje się w pliku konfiguracyjnym środowiska (``config/config_*.json``). Główne parametry konfiguracyjne:

.. code-block:: json

   {
     "llm_engine": {
       "model": "deepseek",
       "ollama_url": "http://localhost:11434/v1/chat/completions",
       "cache_enabled": true,
       "cache_dir": "cache/llm",
       "max_tokens": 2048,
       "timeout": 30,
       "analysis_interval": 300,
       "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
       "timeframes": ["M15", "H1", "H4"]
     }
   }

Kluczowe parametry:

* ``model`` - nazwa modelu LLM używanego do analizy
* ``ollama_url`` - URL API Ollama
* ``cache_enabled`` - włączenie/wyłączenie cachowania
* ``max_tokens`` - maksymalna liczba tokenów dla odpowiedzi
* ``analysis_interval`` - interwał analizy w sekundach
* ``symbols`` - lista analizowanych par walutowych
* ``timeframes`` - lista analizowanych ram czasowych

Przepływ pracy
============

1. Inicjalizacja silnika LLM przy starcie systemu
2. Cykliczne wykonywanie analizy dla każdej pary symbol/timeframe:
   
   a. Pobranie aktualnych danych rynkowych
   b. Obliczenie wskaźników technicznych (SMA, ATR, VWAP)
   c. Wstępna analiza danych przez MarketAnalyzer
   d. Budowa promptu przez PromptBuilder
   e. Wysłanie promptu do modelu LLM
   f. Odebranie i przetworzenie odpowiedzi
   g. Przekształcenie odpowiedzi na konkretną decyzję handlową
   h. Przekazanie decyzji do Agent_Manager

Szablony promptów
===============

LLM Engine używa specjalnie zaprojektowanych szablonów promptów, które znajdują się w pliku ``prompt_templates.py``. Każdy szablon jest dostosowany do konkretnego typu analizy i zawiera instrukcje dla modelu LLM.

Przykładowy szablon promptu:

.. code-block:: python

   MARKET_ANALYSIS_TEMPLATE = """
   Analizuj poniższe dane rynkowe zgodnie z metodą Master i checklist:
   
   [DANE RYNKOWE]
   {market_data}
   
   Oceń czy warunki do wejścia na pozycję są spełnione dla któregokolwiek z trzech setupów:
   1. Trend Reverter
   2. VWAP Bouncer
   3. Small Account Range Rider
   
   Jeśli tak, określ:
   - Rodzaj setupu
   - Kierunek transakcji (BUY/SELL)
   - Poziom stop-loss (w pipsach)
   - Poziom take-profit (w pipsach)
   - Uzasadnienie decyzji
   
   Jeśli nie, wyjaśnij dlaczego warunki nie są spełnione.
   """

Parsowanie odpowiedzi
===================

Odpowiedzi z modelu LLM są przetwarzane przez ResponseParser, który ekstrahuje kluczowe informacje:

* Decyzja: ENTER/WAIT/EXIT
* Kierunek: BUY/SELL
* Symbol: np. EURUSD
* Setup: nazwę wykorzystanego setupu
* Stop-loss: wartość w pipsach
* Take-profit: wartość w pipsach
* Uzasadnienie: tekstowe uzasadnienie decyzji

Przykład sparsowanej odpowiedzi:

.. code-block:: json

   {
     "decision": "ENTER",
     "direction": "BUY",
     "symbol": "EURUSD",
     "setup": "VWAP Bouncer",
     "stop_loss_pips": 15,
     "take_profit_pips": 30,
     "reasoning": "Cena powróciła do VWAP po wcześniejszym odbiciu, tworząc formację Pin Bar. Główny trend jest wzrostowy (cena powyżej 50 SMA)."
   }

Rozwiązywanie problemów
======================

Typowe problemy i ich rozwiązania:

1. **Zbyt długi czas odpowiedzi modelu LLM**
   
   * Sprawdź parametr ``timeout`` w konfiguracji
   * Rozważ zmniejszenie wartości ``max_tokens``
   * Sprawdź, czy Ollama działa poprawnie
   * Rozważ włączenie cache'owania

2. **Niepoprawne decyzje handlowe**
   
   * Sprawdź szablon promptu
   * Sprawdź logi, aby zobaczyć dokładną treść promptu
   * Rozważ dostosowanie szablonu do konkretnego rynku

3. **Brak odpowiedzi lub błędy**
   
   * Sprawdź, czy model LLM jest dostępny
   * Sprawdź logi w ``logs/llm_engine/``
   * Sprawdź połączenie z Ollama

Integracja z innymi komponentami
==============================

LLM Engine integruje się z następującymi komponentami:

* **MT5_Connector** - źródło danych rynkowych
* **Agent_Manager** - odbiorca decyzji handlowych
* **Database** - przechowywanie historii analiz

API komponentu
============

LLM Engine udostępnia następujące główne metody API:

* ``analyze_market(symbol, timeframe)`` - analizuje rynek dla danego symbolu i ramy czasowej
* ``get_decision(symbol, timeframe)`` - zwraca najnowszą decyzję dla danego symbolu
* ``get_analysis_history(symbol, timeframe, limit)`` - zwraca historię analiz 