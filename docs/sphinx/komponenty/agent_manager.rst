##############
Agent Manager
##############

Agent Manager to centralny moduł zarządzający całym systemem LLM Trading. Działa jako koordynator przepływu danych między wszystkimi komponentami, zarządza strategiami handlowymi i podejmuje ostateczne decyzje dotyczące otwierania i zamykania pozycji.

Funkcje
=======

* Koordynacja przepływu danych między komponentami systemu
* Zarządzanie cyklem pracy systemu
* Monitorowanie działania systemu
* Wdrażanie zasad zarządzania ryzykiem
* Przekształcanie decyzji LLM w konkretne polecenia handlowe
* Monitorowanie otwartych pozycji

Struktura modułu
===============

.. code-block:: none

   Agent_Manager/
     ├── __init__.py
     ├── agent_manager.py       # Główna klasa zarządzająca agentami
     ├── coordinator.py         # Koordynator strategii i sygnałów
     ├── order_processor.py     # Przetwarzanie zleceń handlowych
     ├── risk_manager.py        # Zarządzanie ryzykiem
     ├── run_manager.py         # Skrypt uruchamiający komponent jako usługę
     └── strategy_manager.py    # Zarządzanie strategiami handlowymi

Główne klasy i ich rola
======================

AgentManager
-----------

Główna klasa zarządzająca całym cyklem pracy systemu. Inicjalizuje i koordynuje pracę pozostałych komponentów w module.

**Odpowiedzialności:**

* Inicjalizacja i konfiguracja pozostałych klas modułu
* Zarządzanie cyklem pracy agentów handlowych
* Monitorowanie stanu systemu i reagowanie na awarie
* Logowanie działań systemu

Coordinator
----------

Koordynuje przepływ danych i sygnałów między różnymi komponentami systemu.

**Odpowiedzialności:**

* Pobieranie danych rynkowych z MT5_Connector
* Przekazywanie danych do analizy przez LLM_Engine
* Odbieranie decyzji handlowych z LLM_Engine
* Przekazywanie poleceń handlowych do OrderProcessor
* Synchronizacja działań między komponentami

OrderProcessor
------------

Przetwarza polecenia handlowe generowane przez system i przekształca je w konkretne zlecenia dla platformy MT5.

**Odpowiedzialności:**

* Przekształcanie decyzji handlowych w format zrozumiały dla MT5
* Wysyłanie zleceń do MT5_Connector
* Monitorowanie statusu wysłanych zleceń
* Obsługa potwierdzeń wykonania zleceń

RiskManager
---------

Implementuje zasady zarządzania ryzykiem i weryfikuje wszystkie decyzje handlowe pod kątem zgodności z tymi zasadami.

**Odpowiedzialności:**

* Weryfikacja decyzji handlowych pod kątem zarządzania ryzykiem
* Kalkulacja wielkości pozycji na podstawie kapitału i ryzyka
* Monitorowanie dziennego limitu ryzyka
* Implementacja zasad ochrony kapitału (jak zasada trzech strat)
* Dostosowywanie poziomów stop-loss i take-profit

Uruchamianie
===========

Agent Manager można uruchomić jako samodzielną usługę:

.. code-block:: bash

   python -m Agent_Manager.run_manager --env dev

Parametry:

* ``--env`` - środowisko [dev|test|prod], domyślnie ``dev``
* ``--debug`` - uruchomienie w trybie debugowania

Konfiguracja
===========

Konfiguracja Agent Managera znajduje się w pliku konfiguracyjnym środowiska (``config/config_*.json``). Główne parametry konfiguracyjne:

.. code-block:: json

   {
     "agent_manager": {
       "trading_enabled": true,
       "check_interval": 60,
       "max_retries": 3,
       "retry_delay": 5,
       "risk_management": {
         "default_risk_percentage": 1.0,
         "max_daily_risk_percentage": 5.0,
         "max_positions": 5,
         "losing_streak_limit": 3
       }
     }
   }

Kluczowe parametry:

* ``trading_enabled`` - włączenie/wyłączenie handlu (false dla testów)
* ``check_interval`` - częstotliwość sprawdzania nowych sygnałów (w sekundach)
* ``default_risk_percentage`` - domyślny procent ryzyka na transakcję
* ``max_daily_risk_percentage`` - maksymalny dzienny procent ryzyka
* ``max_positions`` - maksymalna liczba jednocześnie otwartych pozycji
* ``losing_streak_limit`` - limit kolejnych przegranych transakcji

Przepływ pracy
============

1. Inicjalizacja modułu przy starcie systemu
2. Cykliczne wykonywanie następujących kroków:
   
   a. Pobranie aktualnych danych rynkowych
   b. Przekazanie danych do analizy przez LLM_Engine
   c. Odebranie decyzji handlowej
   d. Weryfikacja decyzji przez moduł zarządzania ryzykiem
   e. Przekształcenie decyzji w zlecenie
   f. Wysłanie zlecenia do MT5_Connector
   g. Monitorowanie statusu zlecenia
   h. Aktualizacja bazy danych

3. Równolegle:
   
   a. Monitorowanie otwartych pozycji
   b. Zarządzanie pozycjami (przesuwanie stop-loss, częściowe zamykanie)
   c. Monitorowanie limitów ryzyka
   d. Reakcja na zewnętrzne zdarzenia (np. zamknięcie pozycji na żądanie użytkownika)

Logi
====

Wszystkie działania i błędy Agent Managera są zapisywane w katalogu ``logs/agent_manager/``.

Format logów:

.. code-block:: none

   2023-04-15 10:35:22 - INFO - agent_manager - Inicjalizacja Agent Manager
   2023-04-15 10:35:23 - INFO - coordinator - Połączenie z MT5_Connector ustanowione
   2023-04-15 10:35:24 - INFO - coordinator - Połączenie z LLM_Engine ustanowione
   2023-04-15 10:35:25 - INFO - risk_manager - Załadowano parametry zarządzania ryzykiem
   2023-04-15 10:35:30 - INFO - coordinator - Pobrano dane rynkowe dla EURUSD
   2023-04-15 10:35:32 - INFO - coordinator - Otrzymano decyzję: ENTER BUY EURUSD
   2023-04-15 10:35:33 - INFO - risk_manager - Weryfikacja decyzji: OK
   2023-04-15 10:35:34 - INFO - order_processor - Wysłano zlecenie BUY EURUSD 0.01
   2023-04-15 10:35:35 - INFO - order_processor - Otrzymano potwierdzenie wykonania

Rozwiązywanie problemów
======================

Typowe problemy i ich rozwiązania:

1. **Agent Manager nie może połączyć się z innymi komponentami**
   
   * Sprawdź, czy pozostałe komponenty są uruchomione
   * Sprawdź konfigurację adresów IP i portów
   * Sprawdź logi pozostałych komponentów

2. **Decyzje handlowe są generowane, ale zlecenia nie są wysyłane**
   
   * Sprawdź, czy `trading_enabled` jest ustawione na `true` w konfiguracji
   * Sprawdź logi RiskManagera - możliwe, że decyzje są odrzucane
   * Sprawdź dostępne środki na koncie MT5

3. **Limity ryzyka blokują handel**
   
   * Sprawdź aktualne wykorzystanie dziennego limitu ryzyka
   * Sprawdź liczbę otwartych pozycji
   * Sprawdź, czy nie został osiągnięty limit kolejnych strat 