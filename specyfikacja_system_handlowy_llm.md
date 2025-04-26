# Specyfikacja Systemu Handlowego LLM dla MT5

## 1. Architektura systemu

### 1.1 Komponenty główne
- **Lokalny model LLM (Ollama - Deepseek)**
  - Analizuje dane rynkowe
  - Podejmuje decyzje handlowe na podstawie metoda_master.md
  - Dostarcza uzasadnienie decyzji

- **Agent zarządzający**
  - Koordynuje przepływ danych między komponentami
  - Zarządza cyklem pracy systemu
  - Monitoruje działanie systemu

- **Moduł wykonawczy EA (Expert Advisor)**
  - Uruchomiony bezpośrednio w MT5
  - Odpowiada za realizację transakcji (BUY/SELL)
  - Pobiera dane rynkowe z MT5

### 1.2 Komponenty pomocnicze
- **Moduł pozyskiwania danych rynkowych**
  - Pobiera aktualne dane z MT5 (ceny, wskaźniki, ATR, VWAP)
  - Formatuje dane do analizy przez LLM
  - Monitoruje rynek pod kątem spełnienia warunków wejścia

- **Baza danych/pamięć**
  - Przechowuje historię transakcji
  - Zapisuje analizy i decyzje LLM
  - Umożliwia analizę skuteczności strategii

- **Interfejs platformy handlowej**
  - Komunikuje się z MT5 poprzez dostępne API
  - Przekazuje polecenia do EA
  - Pobiera informacje o statusie transakcji

## 2. Szczegółowy przepływ pracy

### 2.1 Pozyskiwanie danych
1. Pobranie aktualnych danych rynkowych z MT5 dla wybranych par walutowych
2. Obliczenie wskaźników technicznych potrzebnych dla metody Master:
   - 50-dniowa prosta średnia ruchoma (50 SMA)
   - Average True Range (ATR)
   - VWAP (Volume Weighted Average Price)
3. Identyfikacja formacji świecowych i potencjalnych setupów handlowych
4. Przygotowanie danych w formie zrozumiałej dla LLM

### 2.2 Analiza i decyzje
1. Przekazanie przygotowanych danych do lokalnego modelu LLM
2. LLM analizuje dane zgodnie z metodyką z metoda_master.md:
   - Określenie głównego trendu (pozycja względem 50 SMA)
   - Analiza dziennego zakresu (ATR)
   - Identyfikacja potencjalnych setupów (Trend Reverter, VWAP Bouncer, Small Account Range Rider)
3. LLM podejmuje decyzję:
   - ENTER (BUY/SELL) z określeniem poziomu stop-loss i take-profit
   - WAIT (brak spełnienia warunków wejścia)
   - EXIT (warunki do zamknięcia istniejącej pozycji)
4. LLM uzasadnia swoją decyzję, odnosząc się do konkretnych elementów strategii

### 2.3 Realizacja transakcji
1. Agent zarządzający otrzymuje decyzję od LLM
2. Weryfikuje decyzję pod kątem zasad zarządzania ryzykiem
3. Formatuje polecenie dla EA
4. Przekazuje polecenie do EA poprzez uzgodniony mechanizm komunikacji
5. EA wykonuje transakcję w MT5
6. Potwierdzenie realizacji transakcji jest zwracane do agenta

### 2.4 Monitorowanie i uczenie się
1. System zapisuje dane o każdej transakcji do bazy danych
2. Monitoruje otwarte pozycje pod kątem warunków wyjścia
3. Okresowo analizuje skuteczność strategii
4. Dostosowuje parametry handlu na podstawie wyników

## 3. Specyfikacja techniczna

### 3.1 Stos technologiczny
- **Backend**: Python 3.10+
- **Model LLM**: Ollama z modelem Deepseek
- **Komunikacja z MT5**: MetaTrader5 Python Package + własny EA
- **Baza danych**: SQLite lub MongoDB (lokalna)
- **Komunikacja między komponentami**: REST API lub WebSocket

### 3.2 Protokół komunikacji z EA
1. Format komunikatów JSON z następującymi polami:
   ```json
   {
     "action": "OPEN_POSITION",
     "symbol": "EURUSD",
     "order_type": "BUY",
     "lot_size": 0.01,
     "stop_loss_pips": 20,
     "take_profit_pips": 40,
     "magic_number": 12345,
     "comment": "VWAP_Bouncer_Setup"
   }
   ```

2. Odpowiedź EA:
   ```json
   {
     "status": "SUCCESS",
     "ticket": 123456789,
     "symbol": "EURUSD",
     "order_type": "BUY",
     "open_price": 1.0876,
     "lot_size": 0.01,
     "stop_loss": 1.0856,
     "take_profit": 1.0916,
     "open_time": "2023-04-15T10:35:22Z"
   }
   ```

### 3.3 Format danych dla LLM
1. Kontekst rynkowy:
   ```
   Symbol: EURUSD
   Aktualny kurs: 1.0876
   Trend główny (50 SMA): Wzrostowy (cena powyżej 50 SMA o 0.0025)
   ATR dzienny: 80 pipsów
   Wykorzystanie ATR: 65% (52 pipsy)
   Pozycja względem VWAP: 15 pipsów poniżej VWAP
   ```

2. Ostatnie świece:
   ```
   Świeca 1: Open: 1.0865, High: 1.0880, Low: 1.0862, Close: 1.0876, Formacja: Pin Bar
   Świeca 2: Open: 1.0872, High: 1.0878, Low: 1.0865, Close: 1.0865, Formacja: Bearish
   Świeca 3: Open: 1.0880, High: 1.0885, Low: 1.0870, Close: 1.0872, Formacja: Doji
   ```

3. Prompt dla modelu LLM:
   ```
   Analizuj poniższe dane rynkowe zgodnie z metodą Master i checklist:
   
   [DANE RYNKOWE]
   
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
   ```

## 4. Zarządzanie ryzykiem i bezpieczeństwo

### 4.1 Zasady zarządzania ryzykiem
- Maksymalne ryzyko na transakcję: 1-2% kapitału
- Automatyczne przesuwanie stop-loss do break-even po osiągnięciu 1:1 (ryzyko:zysk)
- Automatyczne zamykanie 50% pozycji po osiągnięciu 2:1
- Limit 3 kolejnych strat - automatyczna pauza w handlu
- Dzienny limit straty: 5% kapitału

### 4.2 Bezpieczeństwo systemu
- Regularne kopie zapasowe bazy danych
- Monitorowanie stabilności połączenia z MT5
- Mechanizm automatycznego restartu w przypadku awarii
- Logowanie wszystkich operacji i decyzji
- System alertów w przypadku nietypowych zdarzeń

## 5. Interfejsy i monitorowanie

### 5.1 Panel monitorowania
- Web dashboard z kluczowymi metrykami:
  - Aktualne pozycje
  - Historia transakcji
  - Wyniki finansowe
  - Dziennik decyzji LLM
  - Statusy komponentów systemu

### 5.2 Powiadomienia
- Alerty e-mail/SMS przy:
  - Otwarciu/zamknięciu pozycji
  - Osiągnięciu limitu dziennej straty
  - Problemach technicznych
  - Nietypowych zachowaniach rynku

## 6. Testy i wdrażanie

### 6.1 Strategia testowania
- Testy jednostkowe dla każdego komponentu
- Testy integracyjne całego systemu
- Testy na danych historycznych (backtesting)
- Testy na rachunku demo w czasie rzeczywistym
- Stopniowe przejście na rachunek rzeczywisty z minimalnym ryzykiem

### 6.2 Plan wdrożenia
1. Implementacja modułu pozyskiwania danych
2. Implementacja EA dla MT5
3. Integracja modelu LLM
4. Implementacja agenta zarządzającego
5. Testy integracyjne
6. Wdrożenie na rachunku demo (2 tygodnie)
7. Analiza wyników i dostosowanie
8. Wdrożenie na rachunku rzeczywistym z minimalnym lotem

## 7. Harmonogram rozwoju

1. **Faza 1 **:
   - Implementacja modułu pozyskiwania danych
   - Podstawowa struktura EA dla MT5

2. **Faza 2 **:
   - Integracja modelu LLM
   - Implementacja procesu decyzyjnego
   - Podstawowa baza danych

3. **Faza 3 **:
   - Implementacja pełnej komunikacji między komponentami
   - Testy integracyjne

4. **Faza 4 **:
   - Testy na rachunku demo
   - Analiza wyników i optymalizacja

5. **Faza 5 **:
   - Wdrożenie na rachunku rzeczywistym
   - Monitorowanie i dostrajanie 