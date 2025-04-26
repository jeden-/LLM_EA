# Stos Technologiczny - System Handlowy LLM dla MT5

## Przegląd

Poniższy dokument definiuje stos technologiczny wybrany do implementacji Systemu Handlowego LLM dla MT5. Wybór technologii uwzględnia specyficzne wymagania systemu, w tym konieczność lokalnego przetwarzania, integracji z MetaTrader 5, oraz autonomicznego działania 24/7.

## Główne komponenty technologiczne

### 1. Język programowania i środowisko

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| Python | 3.10+ | Bogaty ekosystem bibliotek do ML, analizy danych, a także obsługa MT5. Stabilność LTS. |
| Poetry | 1.5+ | Zarządzanie zależnościami i środowiskiem wirtualnym. |
| Docker | 24.0+ | Konteneryzacja komponentów dla łatwiejszego zarządzania i restartów. |

### 2. Lokalny Model LLM

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| Grok | 0.1.20+ | Efektywne uruchamianie modeli LLM lokalnie. |
| LangChain | 0.1.0+ | Framework do integracji LLM z pozostałymi komponentami. |

### 3. Komunikacja z MetaTrader 5

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| MetaTrader5 Python package | Najnowsza | Oficjalna biblioteka do komunikacji z MT5. |
| MQL5 | - | Język do tworzenia Expert Advisors (EA) dla MT5. |
| ZeroMQ | 4.3+ | Biblioteka do komunikacji między procesami (EA i Python). |

### 4. Baza danych

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| SQLite | 3.40+ | Lekka, bezserwerowa baza danych, idealna do lokalnego zastosowania. |
| SQLAlchemy | 2.0+ | ORM do łatwiejszej integracji z Pythonem. |
| Alembic | 1.10+ | Narzędzie do zarządzania migracjami bazy danych. |

### 5. Komunikacja między komponentami

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| FastAPI | 0.100+ | Szybki framework API dla komunikacji wewnętrznej i dashboardu. |
| PyZMQ | 25.1+ | Biblioteka Python do komunikacji ZeroMQ. |
| Pydantic | 2.0+ | Walidacja danych i serializacja. |

### 6. Monitorowanie i logowanie

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| Loguru | 0.7+ | Zaawansowane logowanie z obsługą różnych poziomów i formatów. |
| Prometheus | 2.45+ | Metryki i monitorowanie działania systemu. |
| Grafana | 10.0+ | Wizualizacja metryk i tworzenie dashboardów. |

### 7. Interfejs użytkownika

| Technologia | Wersja | Uzasadnienie |
|-------------|--------|--------------|
| Streamlit | 1.25+ | Prosta, szybka tworzenie interfejsów webowych dla danych. |
| Plotly | 5.15+ | Interaktywne wykresy i wizualizacje. |

## Architektura techniczna

### 1. Struktura komponentów

```
├── MT5_Connector/               # Moduł komunikacji z MT5
│   ├── mt5_client.py           # Klient Python do MT5 API
│   └── data_processor.py       # Przetwarzanie surowych danych
│
├── Expert_Advisor/              # Kod EA dla MT5
│   ├── LLM_Trader.mq5          # Główny plik EA
│   └── zmq_bridge.mqh          # Obsługa komunikacji ZeroMQ
│
├── LLM_Engine/                  # Silnik analizy LLM
│   ├── grok_client.py          # Klient do Grok
│   ├── prompt_builder.py       # Przygotowanie promptów
│   └── decision_maker.py       # Interpretacja odpowiedzi LLM
│
├── Agent_Manager/               # Agent zarządzający
│   ├── coordinator.py          # Koordynacja komponentów
│   ├── risk_manager.py         # Zarządzanie ryzykiem
│   └── order_processor.py      # Przetwarzanie zleceń
│
├── Database/                    # Warstwa bazy danych
│   ├── models.py               # Modele SQLAlchemy
│   ├── migrations/             # Migracje Alembic
│   └── repository.py           # Warstwa dostępu do danych
│
├── Dashboard/                   # Interfejs użytkownika
│   ├── app.py                  # Aplikacja Streamlit
│   └── visualizations.py       # Komponenty wizualizacji
│
├── Common/                      # Współdzielone komponenty
│   ├── config.py               # Konfiguracja
│   ├── logging_setup.py        # Konfiguracja logowania
│   └── schemas.py              # Schematy Pydantic
```

### 2. Przepływ danych

```
MT5 → MT5_Connector → Agent_Manager → LLM_Engine → Agent_Manager → MT5_Connector → EA → MT5
   ↑                       ↑                                        ↓
   └─────────────────────Database──────────────────────────────Dashboard
```

### 3. Komunikacja między komponentami

- **REST API** (FastAPI): Do komunikacji między agentami, dashboardem i bazą danych
- **ZeroMQ**: Do komunikacji między Python a EA w MT5
- **SQLAlchemy**: Do komunikacji z bazą danych

## Wymagania instalacyjne

### Wymagania systemowe

- System operacyjny: Windows 10/11 64-bit lub Linux (Ubuntu 22.04+)
- CPU: minimum 4 rdzenie, 8 zalecane
- RAM: minimum 16GB, 32GB zalecane dla większych modeli LLM
- Dysk: minimum 50GB wolnej przestrzeni (SSD)
- GPU: Opcjonalnie NVIDIA z min. 8GB VRAM dla przyspieszenia LLM

### Zależności zewnętrzne

- MetaTrader 5 (zainstalowany i skonfigurowany)
- Grok (zainstalowany i skonfigurowany)
- Docker Desktop lub Docker Engine + Docker Compose
- Git

## Strategia deploymentu

1. **Środowisko developerskie**:
   - Uruchomienie poprzez Poetry i skrypty deweloperskie
   - Lokalny SQLite jako baza danych
   - Konfiguracja poprzez zmienne środowiskowe lub pliki .env

2. **Środowisko testowe**:
   - Konteneryzacja przez Docker Compose
   - Testowe konto MT5
   - SQLite jako baza danych

3. **Środowisko produkcyjne**:
   - Konteneryzacja przez Docker Compose
   - Rzeczywiste konto MT5
   - SQLite jako baza danych
   - Automatyczne kopie zapasowe
   - Monitoring przez Prometheus + Grafana

## Uzasadnienie wyboru technologii

1. **Python jako główny język**:
   - Bogaty ekosystem dla AI/ML i analizy danych
   - Oficjalne wsparcie dla MT5
   - Łatwa integracja z różnymi komponentami

2. **Grok**:
   - Lokalne uruchamianie LLM bez zewnętrznych API
   - Doskonały balans między wydajnością a precyzją dla zadań analitycznych
   - Możliwość działania offline

3. **SQLite**:
   - Bezserwerowa baza danych idealna dla lokalnej instalacji
   - Prosta konfiguracja i zarządzanie
   - Wystarczająca wydajność dla przewidywanej ilości danych

4. **ZeroMQ dla komunikacji z EA**:
   - Lekka biblioteka do efektywnej komunikacji międzyprocesowej
   - Obsługa różnych wzorców komunikacji (request-reply, pub-sub)
   - Wsparcie dla MQL5

5. **Docker dla konteneryzacji**:
   - Izolacja komponentów
   - Łatwe zarządzanie uruchamianiem/restartami
   - Ustandaryzowane środowisko

## Alternatywy rozważane

### Baza danych
- **MongoDB**: Rozważana jako alternatywa dla SQLite ze względu na elastyczny model danych
- **PostgreSQL**: Rozważana jako pełna relacyjna baza danych
- Wybrano SQLite ze względu na prostotę, lokalne działanie i brak konieczności dodatkowej instalacji

### LLM
- **LM Studio**: Alternatywa dla Grok
- **Llama 3 70B**: Alternatywa dla Grok
- Wybrano Grok ze względu na prostszą integrację i dobre wyniki na zadaniach analitycznych

### Komunikacja
- **Socket.io**: Alternatywa dla ZeroMQ
- **gRPC**: Alternatywa dla REST API
- Wybrano kombinację ZeroMQ + REST API dla balansu między wydajnością a łatwością implementacji 