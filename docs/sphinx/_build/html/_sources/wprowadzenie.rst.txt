################
Wprowadzenie
################

Czym jest LLM Trading System?
=============================

System LLM Trading to zaawansowana platforma handlowa wykorzystująca modele językowe (LLM) do analizy rynku Forex i generowania sygnałów handlowych. Jest to innowacyjne podejście do automatyzacji procesu inwestycyjnego, które łączy moc sztucznej inteligencji z tradycyjną analizą techniczną i fundamentalną.

System został zaprojektowany z myślą o:

* Automatyzacji podejmowania decyzji handlowych
* Eliminacji czynnika emocjonalnego z procesu handlowego
* Wykorzystaniu zaawansowanych modeli AI do identyfikacji okazji rynkowych
* Integracji z platformą MetaTrader 5 w celu bezpośredniego wykonywania transakcji
* Umożliwieniu handlu 24/7 bez stałej ingerencji człowieka

Podstawowe założenia
===================

1. **Autonomiczność** - system działa niezależnie, samodzielnie analizując rynek i podejmując decyzje handlowe
2. **Integralność** - wszystkie komponenty systemu współpracują ze sobą, tworząc spójny ekosystem handlowy
3. **Bazowanie na Metodzie Master** - implementacja trzech głównych setupów handlowych dostosowanych do małych kont
4. **Zarządzanie ryzykiem** - konserwatywne podejście z limitami ryzyka na pojedynczą transakcję i dzień handlowy
5. **Ciągłe uczenie się** - system gromadzi dane o transakcjach w celu przyszłej optymalizacji strategii

Kluczowe funkcjonalności
=======================

Analiza rynku przy użyciu LLM
-----------------------------

System wykorzystuje lokalne modele językowe (Ollama z Deepseek) do analizy danych rynkowych i podejmowania decyzji handlowych. Model analizuje:

* Dane cenowe i formacje świecowe
* Wskaźniki techniczne (50 SMA, ATR, VWAP)
* Pozycję ceny w kontekście dziennego zakresu
* Potencjalne setup'y handlowe zgodne z Metodą Master

Automatyczne zarządzanie transakcjami
------------------------------------

* Automatyczne otwieranie i zamykanie pozycji
* Kalkulacja wielkości pozycji na podstawie zarządzania ryzykiem
* Ustawianie poziomów stop-loss i take-profit
* Śledzenie otwartych pozycji i monitorowanie ich wyników

Dashboard monitorujący
--------------------

* Wizualizacja aktualnych i historycznych transakcji
* Analiza skuteczności strategii
* Monitorowanie kluczowych metryk wydajności
* Alerty o ważnych zdarzeniach systemowych

Architektura systemu
===================

System składa się z pięciu głównych komponentów:

1. **Agent_Manager** - centralny koordynator całego systemu
2. **LLM_Engine** - silnik analizy wykorzystujący modele językowe
3. **MT5_Connector** - łącznik z platformą MetaTrader 5
4. **Database** - warstwa przechowywania danych
5. **Dashboard** - interfejs użytkownika do monitorowania systemu

Każdy z tych komponentów jest odpowiedzialny za określoną część funkcjonalności systemu i może działać jako niezależna usługa.

Przepływ danych
--------------

.. code-block:: none

    +---------------+     +---------------+     +---------------+
    | MT5_Connector |---->| LLM_Engine    |---->| Agent_Manager |
    | (dane rynkowe)|     | (analiza)     |     | (decyzje)     |
    +---------------+     +---------------+     +---------------+
           ^                                           |
           |                                           v
    +---------------+                          +---------------+
    | Expert Advisor|<-------------------------| MT5_Connector |
    | (wykonanie)   |                          | (zlecenia)    |
    +---------------+                          +---------------+
           |
           v
    +---------------+     +---------------+
    | Database      |---->| Dashboard     |
    | (historia)    |     | (monitoring)  |
    +---------------+     +---------------+

Strategie handlowe
=================

System implementuje trzy główne strategie opisane w Metodzie Master:

1. **Trend Reverter** - wykorzystuje krótkoterminowe odwrócenia w kierunku głównego trendu
2. **VWAP Bouncer** - bazuje na odbiciach od VWAP zgodnie z głównym trendem
3. **Small Account Range Rider** - wykorzystuje dzienne zakresy cenowe

Szczegółowy opis każdej z tych strategii znajduje się w sekcji :doc:`metoda_master`.

Zarządzanie ryzykiem
===================

System implementuje konserwatywne zasady zarządzania ryzykiem:

* Maksymalne ryzyko 1-2% kapitału na pojedynczą transakcję
* Maksymalne ryzyko dzienne na poziomie 5% kapitału
* Automatyczne przesuwanie stop-loss do break-even po osiągnięciu określonego zysku
* Częściowe zamykanie pozycji po osiągnięciu ustalonych poziomów zysku
* Automatyczne wstrzymanie handlu po serii strat

Dla kogo jest ten system?
=======================

System LLM Trading jest przeznaczony dla:

* **Traderów indywidualnych** - którzy chcą zautomatyzować swój proces handlowy
* **Małych inwestorów** - z ograniczonym kapitałem, którzy chcą efektywnie zarządzać ryzykiem
* **Entuzjastów AI** - zainteresowanych praktycznym zastosowaniem modeli językowych w handlu
* **Programistów** - chcących zrozumieć architekturę systemów handlowych opartych na AI

Pierwsze kroki
=============

Aby rozpocząć pracę z systemem, zalecamy:

1. Zapoznanie się z dokumentacją instalacyjną: :doc:`instalacja`
2. Zrozumienie struktury systemu: :doc:`struktura_systemu`
3. Poznanie Metody Master: :doc:`metoda_master`
4. Skonfigurowanie systemu: :doc:`konfiguracja`
5. Uruchomienie systemu: :doc:`uruchamianie` 