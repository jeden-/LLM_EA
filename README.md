# LLM Trader dla MetaTrader 5

System handlowy wykorzystujący lokalny model LLM (Ollama z Deepseek) do podejmowania decyzji inwestycyjnych na rynku Forex, zintegrowany z platformą MetaTrader 5.

## Opis projektu

System automatycznie analizuje dane rynkowe z MT5, stosuje strategię opisaną w "metoda_master.md" i podejmuje decyzje handlowe przy użyciu lokalnego modelu LLM. Pozycje są otwierane i zamykane za pośrednictwem Expert Advisor (EA) w MT5.

## Główne funkcjonalności

- Pobieranie i analiza danych rynkowych z MT5
- Obliczanie wskaźników technicznych (50 SMA, ATR, VWAP)
- Identyfikacja setupów handlowych przy użyciu lokalnego modelu LLM
- Automatyczne otwieranie i zamykanie pozycji przez EA
- Zarządzanie ryzykiem zgodnie ze strategią
- Monitorowanie wyników i generowanie raportów

## Wymagania systemowe

- Windows 10/11 64-bit lub Linux (Ubuntu 22.04+)
- Python 3.10+
- MetaTrader 5
- Ollama z modelem Deepseek
- Min. 16GB RAM (32GB zalecane)
- Min. 50GB wolnej przestrzeni na dysku (SSD)
- Opcjonalnie: NVIDIA GPU z min. 8GB VRAM

## Struktura katalogów

```
LLM_Trader_MT5/
├── MT5_Connector/          # Moduł komunikacji z MT5
├── Expert_Advisor/         # Kod EA dla MT5
├── LLM_Engine/             # Silnik analizy LLM
├── Agent_Manager/          # Agent zarządzający
├── Database/               # Warstwa bazy danych
├── Dashboard/              # Interfejs użytkownika
├── Common/                 # Współdzielone komponenty
├── tests/                  # Testy
├── docs/                   # Dokumentacja
└── scripts/                # Skrypty pomocnicze
```

## Stan projektu

Projekt jest w fazie implementacji. Aktualny status można sprawdzić w pliku [progress_tracking.md](../progress_tracking.md).

## Licencja

Ten projekt jest dostępny na licencji MIT. Szczegóły w pliku LICENSE. 