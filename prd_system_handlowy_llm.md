# PRD - System Handlowy LLM dla MT5

## Informacje o projekcie

**Nazwa projektu:** System Handlowy LLM dla MT5
**Wersja dokumentu:** 1.0
**Data utworzenia:** 2024-09-08
**Autor:** Mariusz

## Cel projektu

Stworzenie autonomicznego systemu handlowego dla platform MT5, wykorzystującego lokalny model LLM (Ollama z Deepseek) do podejmowania decyzji inwestycyjnych na podstawie strategii opisanej w dokumencie "metoda_master.md". System ma umożliwić automatyczne zawieranie transakcji na rynku Forex bez konieczności ręcznej interwencji.

## Wymagania funkcjonalne

### 1. Moduł pozyskiwania danych rynkowych

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| F1.1 | System musi pobierać aktualne dane rynkowe z MT5 dla określonych par walutowych | Wysoki |
| F1.2 | System musi obliczać wskaźniki techniczne: 50 SMA, ATR, VWAP | Wysoki |
| F1.3 | System musi identyfikować podstawowe formacje świecowe | Średni |
| F1.4 | System musi przygotowywać dane w formacie zrozumiałym dla modelu LLM | Wysoki |
| F1.5 | System musi aktualizować dane w czasie rzeczywistym | Wysoki |

### 2. Moduł analizy i podejmowania decyzji (LLM)

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| F2.1 | System musi wykorzystywać lokalny model LLM (Ollama) do analizy danych | Wysoki |
| F2.2 | System musi implementować logikę decyzyjną opartą na "metoda_master.md" | Wysoki |
| F2.3 | System musi rozpoznawać trzy główne setupy: Trend Reverter, VWAP Bouncer, Small Account Range Rider | Wysoki |
| F2.4 | System musi podejmować decyzje ENTER/WAIT/EXIT | Wysoki |
| F2.5 | System musi określać poziomy stop-loss i take-profit dla każdej transakcji | Wysoki |
| F2.6 | System musi dostarczać uzasadnienie każdej decyzji | Średni |

### 3. Moduł wykonawczy (EA)

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| F3.1 | System musi zawierać Expert Advisor (EA) dla MT5 | Wysoki |
| F3.2 | EA musi realizować transakcje na podstawie poleceń z modułu zarządzającego | Wysoki |
| F3.3 | EA musi obsługiwać operacje BUY/SELL na parach walutowych | Wysoki |
| F3.4 | EA musi ustawiać stop-loss i take-profit dla każdej transakcji | Wysoki |
| F3.5 | EA musi zwracać potwierdzenie realizacji transakcji | Wysoki |
| F3.6 | EA musi umożliwiać modyfikację istniejących pozycji | Średni |
| F3.7 | EA musi zamykać pozycje na polecenie modułu zarządzającego | Wysoki |

### 4. Moduł zarządzający

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| F4.1 | System musi koordynować przepływ danych między wszystkimi komponentami | Wysoki |
| F4.2 | System musi weryfikować decyzje LLM pod kątem zasad zarządzania ryzykiem | Wysoki |
| F4.3 | System musi formatować polecenia dla EA | Wysoki |
| F4.4 | System musi obsługiwać komunikację z EA | Wysoki |
| F4.5 | System musi monitorować otwarte pozycje | Wysoki |
| F4.6 | System musi zapisywać dane o transakcjach do bazy danych | Średni |
| F4.7 | System musi umożliwiać restart poszczególnych komponentów w przypadku awarii | Niski |

### 5. Moduł monitorowania i raportowania

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| F5.1 | System musi zapisywać historię wszystkich transakcji | Wysoki |
| F5.2 | System musi generować podstawowe statystyki efektywności | Średni |
| F5.3 | System musi prezentować wyniki handlu na prostym dashboardzie | Niski |
| F5.4 | System musi generować alerty o kluczowych zdarzeniach | Średni |
| F5.5 | System musi umożliwiać przeglądanie decyzji podjętych przez LLM | Niski |

## Wymagania niefunkcjonalne

### 1. Wydajność

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| NF1.1 | System musi analizować dane i podejmować decyzje w czasie nie dłuższym niż 30 sekund | Wysoki |
| NF1.2 | System musi obsługiwać minimum 5 par walutowych jednocześnie | Średni |
| NF1.3 | System musi działać 24/7 z dostępnością na poziomie 99% | Wysoki |

### 2. Bezpieczeństwo

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| NF2.1 | System musi zapewniać bezpieczne przechowywanie danych transakcyjnych | Wysoki |
| NF2.2 | System musi regularnie tworzyć kopie zapasowe bazy danych | Średni |
| NF2.3 | System nie może przechowywać danych uwierzytelniających w formacie jawnym | Wysoki |

### 3. Niezawodność

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| NF3.1 | System musi automatycznie wznawiać działanie po awarii | Wysoki |
| NF3.2 | System musi logować wszystkie błędy z odpowiednim poziomem szczegółowości | Średni |
| NF3.3 | System musi posiadać mechanizm weryfikacji poprawności danych wejściowych | Wysoki |

### 4. Możliwości rozbudowy

| ID | Wymaganie | Priorytet |
|----|-----------|-----------|
| NF4.1 | System musi być modułowy, umożliwiając łatwą wymianę komponentów | Średni |
| NF4.2 | System musi umożliwiać dodawanie nowych par walutowych bez zmian w kodzie | Niski |
| NF4.3 | System musi umożliwiać modyfikację parametrów strategii handlowej | Średni |

## Środowisko pracy

### Środowisko produkcyjne
- System operacyjny: Windows/Linux
- Aplikacja MetaTrader 5
- Ollama z modelem Deepseek
- Python 3.10+
- Dedykowany komputer działający 24/7

### Środowisko testowe
- Konto demo MT5
- Lokalne środowisko developerskie

## Ograniczenia

- EA może tylko otwierać i zamykać transakcje, ponieważ broker zablokował API dla innych operacji
- System musi działać na lokalnym komputerze (bez chmury)
- Model LLM (Deepseek) musi działać lokalnie poprzez Ollama

## Interfejsy zewnętrzne

### Interfejs MetaTrader 5
- Komunikacja przez oficjalny pakiet Python MetaTrader5
- Protokół WebSocket/REST API do komunikacji z EA

## Scenariusze użycia

### UC1: Automatyczne otwieranie pozycji

1. System pobiera aktualne dane rynkowe
2. System oblicza wskaźniki techniczne
3. LLM analizuje dane i identyfikuje setup handlowy
4. LLM podejmuje decyzję o wejściu na pozycję (ENTER)
5. Agent zarządzający weryfikuje decyzję pod kątem zarządzania ryzykiem
6. Agent formatuje polecenie dla EA
7. EA realizuje transakcję w MT5
8. System otrzymuje potwierdzenie realizacji
9. System zapisuje dane o transakcji do bazy danych

### UC2: Monitorowanie i zamykanie pozycji

1. System monitoruje otwarte pozycje
2. System sprawdza warunki zamknięcia pozycji (cele zysku, stop-loss)
3. LLM analizuje aktualną sytuację rynkową
4. LLM podejmuje decyzję o wyjściu z pozycji (EXIT)
5. Agent zarządzający formatuje polecenie dla EA
6. EA zamyka pozycję w MT5
7. System otrzymuje potwierdzenie zamknięcia
8. System zapisuje dane o zamknięciu do bazy danych

### UC3: Reakcja na awarie

1. System wykrywa awarię jednego z komponentów
2. System loguje informację o błędzie
3. System podejmuje próbę automatycznego restartu komponentu
4. System wysyła powiadomienie o awarii
5. System wznawia normalne działanie po usunięciu problemu

## Metryki sukcesu

- System poprawnie identyfikuje minimum 70% setupów handlowych
- System osiąga pozytywny wynik finansowy w okresie testowym (2 tygodnie)
- System działa stabilnie przez co najmniej 7 dni bez interwencji
- Czas od analizy danych do podjęcia decyzji nie przekracza 30 sekund 