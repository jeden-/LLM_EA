//+------------------------------------------------------------------+
//|                                                      LLM_EA.mq5 |
//|                             System Handlowy LLM dla MetaTrader 5 |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024"
#property link      ""
#property version   "1.01"
#property strict

// Importy standardowych bibliotek
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

// Deklaracje obiektów globalnych
CTrade         Trade;          // Obiekt do zarządzania transakcjami
CSymbolInfo    SymbolInfo;     // Informacje o instrumencie
CPositionInfo  PositionInfo;   // Informacje o pozycjach

// Parametry wejściowe - ogólne
input string   InpComment      = "LLM_EA";      // Komentarz dla zleceń
input double   InpVolume       = 0.01;          // Wielkość pozycji w lotach
input int      InpMagicNumber  = 123456;        // Magic Number

// Parametry wejściowe - komunikacja przez pliki
input string   InpSignalFile   = "signal.txt";   // Plik sygnałów
input string   InpStatusFile   = "status.txt";   // Plik statusu
input int      InpStatusInterval = 5;            // Interwał wysyłania statusu (sekundy)
input bool     InpDebugMode    = false;          // Tryb debugowania

// Dodaj tę zmienną globalną na początku pliku
input bool InpUseBacktestSignals = false;  // Użyj wbudowanych sygnałów dla backtestingu

// Zmienne globalne
bool           g_is_initialized = false;
int            g_last_error = 0;
int            g_ticket = 0;
datetime       g_last_bar_time = 0;
string         g_signal = "";
double         g_entry_price = 0.0;
double         g_stop_loss = 0.0;
double         g_take_profit = 0.0;
bool           g_waiting_for_signal = false;
datetime       g_last_status_time = 0;
datetime       g_last_file_check_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Inicjalizacja obiektu Trade
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetMarginMode();
   Trade.SetTypeFillingBySymbol(Symbol());
   
   // Inicjalizacja obiektu informacji o symbolu
   if(!SymbolInfo.Name(Symbol()))
   {
      Print("Nie udało się zainicjalizować informacji o symbolu: ", Symbol());
      return INIT_FAILED;
   }
   
   // Sprawdź, czy handel jest dozwolony dla tego symbolu
   if(!SymbolInfo.TradeMode())
   {
      Print("Handel nie jest dozwolony dla tego symbolu: ", Symbol());
      return INIT_FAILED;
   }
   
   // Ustaw flagi inicjalizacji
   g_is_initialized = true;
   g_waiting_for_signal = true;
   g_last_status_time = 0; // Wymuś wysłanie statusu przy pierwszym ticku
   g_last_file_check_time = 0; // Wymuś sprawdzenie pliku przy pierwszym ticku
   
   // Reset zmiennych sygnałów
   g_signal = "";
   g_entry_price = 0.0;
   g_stop_loss = 0.0;
   g_take_profit = 0.0;
   
   // Wyślij początkowy status
   SendStatus();
   
   Print("LLM_EA zainicjalizowany pomyślnie. Oczekiwanie na sygnały...");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("LLM_EA zatrzymany. Powód: ", reason);
   g_is_initialized = false;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!g_is_initialized)
      return;
      
   // Aktualizacja informacji o symbolu
   SymbolInfo.Refresh();
   SymbolInfo.RefreshRates();
   
   // Sprawdź, czy mamy nową świecę
   datetime current_bar_time = iTime(Symbol(), PERIOD_CURRENT, 0);
   bool is_new_bar = (current_bar_time != g_last_bar_time);
   g_last_bar_time = current_bar_time;
   
   // Sprawdź, czy nadszedł czas na sprawdzenie pliku sygnałów
   datetime current_time = TimeLocal();
   if(current_time - g_last_file_check_time >= 1) // Sprawdzaj co sekundę
   {
      // Sprawdź plik sygnałów
      CheckSignalFile();
      g_last_file_check_time = current_time;
   }
   
   // Sprawdź, czy nadszedł czas na wysłanie statusu
   if(current_time - g_last_status_time >= InpStatusInterval)
   {
      SendStatus();
      g_last_status_time = current_time;
   }
   
   // Sprawdź sygnał i przetwórz go
   ProcessExternalSignal();
   
   // Sprawdź status otwartych pozycji
   ManageOpenPositions();

   // Dodany kod dla backtestingu - generuje sygnały oparte na przecięciu średnich kroczących
   if(InpUseBacktestSignals && is_new_bar) {
       // Tworzenie uchwytów do wskaźników MA
       int ma_fast_handle = iMA(Symbol(), PERIOD_CURRENT, 10, 0, MODE_SMA, PRICE_CLOSE);
       int ma_slow_handle = iMA(Symbol(), PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE);
       
       // Tablice do przechowywania wartości
       double ma_fast_values[];
       double ma_slow_values[];
       
       // Ustawienie indeksowania od 0
       ArraySetAsSeries(ma_fast_values, true);
       ArraySetAsSeries(ma_slow_values, true);
       
       // Kopiowanie wartości indykatorów do tablic
       CopyBuffer(ma_fast_handle, 0, 0, 3, ma_fast_values);
       CopyBuffer(ma_slow_handle, 0, 0, 3, ma_slow_values);
       
       // Sprawdzanie sygnałów
       // Sygnał kupna: szybka MA przecina wolną MA z dołu do góry
       if(ma_fast_values[1] < ma_slow_values[1] && ma_fast_values[0] > ma_slow_values[0]) {
           double sl = SymbolInfo.Bid() - (50 * SymbolInfo.Point());
           double tp = SymbolInfo.Bid() + (100 * SymbolInfo.Point());
           g_signal = "BUY";
           g_entry_price = SymbolInfo.Ask();
           g_stop_loss = sl;
           g_take_profit = tp;
           if(InpDebugMode) Print("Backtest: Wygenerowano sygnał BUY");
       }
       // Sygnał sprzedaży: szybka MA przecina wolną MA z góry na dół
       else if(ma_fast_values[1] > ma_slow_values[1] && ma_fast_values[0] < ma_slow_values[0]) {
           double sl = SymbolInfo.Ask() + (50 * SymbolInfo.Point());
           double tp = SymbolInfo.Ask() - (100 * SymbolInfo.Point());
           g_signal = "SELL";
           g_entry_price = SymbolInfo.Bid();
           g_stop_loss = sl;
           g_take_profit = tp;
           if(InpDebugMode) Print("Backtest: Wygenerowano sygnał SELL");
       }
       
       // Zwolnienie uchwytów wskaźników, gdy nie są już potrzebne
       IndicatorRelease(ma_fast_handle);
       IndicatorRelease(ma_slow_handle);
   }
}

//+------------------------------------------------------------------+
//| Sprawdzenie pliku sygnałów                                       |
//+------------------------------------------------------------------+
void CheckSignalFile()
{
   if(!FileIsExist(InpSignalFile))
      return;
      
   int file_handle = FileOpen(InpSignalFile, FILE_READ|FILE_TXT);
   if(file_handle != INVALID_HANDLE)
   {
      string content = "";
      while(!FileIsEnding(file_handle))
      {
         content = FileReadString(file_handle);
      }
      FileClose(file_handle);
      
      // Usuń plik, aby nie przetwarzać sygnału ponownie
      FileDelete(InpSignalFile);
      
      // Przetwórz zawartość pliku
      if(content != "")
      {
         ProcessSignalContent(content);
      }
   }
}

//+------------------------------------------------------------------+
//| Przetwarzanie zawartości pliku sygnałów                          |
//+------------------------------------------------------------------+
void ProcessSignalContent(string content)
{
   if(InpDebugMode) Print("Otrzymano sygnał: ", content);
   
   // Format: ACTION,SYMBOL,ENTRY,SL,TP
   // np. BUY,EURUSD,1.1234,1.1200,1.1300
   
   string parts[];
   int count = StringSplit(content, ',', parts);
   
   if(count < 2)
   {
      Print("Nieprawidłowy format sygnału: ", content);
      return;
   }
   
   string action = parts[0];
   string symbol = parts[1];
   
   // Sprawdź, czy sygnał jest dla bieżącego symbolu
   if(symbol != Symbol())
   {
      if(InpDebugMode) Print("Sygnał dla innego symbolu: ", symbol, ", bieżący: ", Symbol());
      return;
   }
   
   if(action == "BUY" && count >= 5)
   {
      g_signal = "BUY";
      g_entry_price = StringToDouble(parts[2]);
      g_stop_loss = StringToDouble(parts[3]);
      g_take_profit = StringToDouble(parts[4]);
      
      if(InpDebugMode) Print("Ustawiono sygnał BUY: entry=", g_entry_price, ", SL=", g_stop_loss, ", TP=", g_take_profit);
   }
   else if(action == "SELL" && count >= 5)
   {
      g_signal = "SELL";
      g_entry_price = StringToDouble(parts[2]);
      g_stop_loss = StringToDouble(parts[3]);
      g_take_profit = StringToDouble(parts[4]);
      
      if(InpDebugMode) Print("Ustawiono sygnał SELL: entry=", g_entry_price, ", SL=", g_stop_loss, ", TP=", g_take_profit);
   }
   else if(action == "CLOSE")
   {
      g_signal = "CLOSE";
      g_entry_price = 0;
      g_stop_loss = 0;
      g_take_profit = 0;
      
      if(InpDebugMode) Print("Ustawiono sygnał CLOSE");
   }
   else
   {
      Print("Nieznana akcja: ", action);
   }
}

//+------------------------------------------------------------------+
//| Wysłanie statusu do pliku                                        |
//+------------------------------------------------------------------+
void SendStatus()
{
   // Pobranie informacji o koncie
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   int positions = PositionsTotal();
   
   // Format: SYMBOL,ASK,BID,BALANCE,EQUITY,POSITIONS,TIMESTAMP
   string status = StringFormat("%s,%.5f,%.5f,%.2f,%.2f,%d,%s",
                               Symbol(),
                               SymbolInfo.Ask(),
                               SymbolInfo.Bid(),
                               balance,
                               equity,
                               positions,
                               TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS));
   
   // Zapis do pliku
   int file_handle = FileOpen(InpStatusFile, FILE_WRITE|FILE_TXT);
   if(file_handle != INVALID_HANDLE)
   {
      FileWriteString(file_handle, status);
      FileClose(file_handle);
      
      if(InpDebugMode) Print("Status zapisany do pliku: ", status);
   }
   else
   {
      Print("Nie udało się otworzyć pliku statusu: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Zarządzanie otwartymi pozycjami                                  |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   // Sprawdź, czy mamy otwarte pozycje dla tego symbolu
   if(PositionInfo.Select(Symbol()))
   {
      // Sprawdź, czy pozycja należy do tego EA
      if(PositionInfo.Magic() == InpMagicNumber)
      {
         // Tutaj będzie kod do zarządzania otwartymi pozycjami
         // Na razie tylko wyświetlamy status
         long position_type = PositionInfo.PositionType();
         double position_profit = PositionInfo.Profit();
         
         if(InpDebugMode)
         {
            if(position_type == POSITION_TYPE_BUY)
               Print("Otwarta pozycja BUY, profit: ", position_profit);
            else if(position_type == POSITION_TYPE_SELL)
               Print("Otwarta pozycja SELL, profit: ", position_profit);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Przetwarzanie zewnętrznych sygnałów                              |
//+------------------------------------------------------------------+
void ProcessExternalSignal()
{
   // Jeśli mamy ustawiony sygnał, przetwarzamy go
   if(g_signal != "")
   {
      if(g_signal == "BUY" && g_entry_price > 0)
      {
         if(InpDebugMode) Print("Przetwarzanie sygnału BUY z entry: ", g_entry_price);
         OpenBuyPosition(g_entry_price, g_stop_loss, g_take_profit);
         g_signal = ""; // Reset sygnału po wykonaniu
      }
      else if(g_signal == "SELL" && g_entry_price > 0)
      {
         if(InpDebugMode) Print("Przetwarzanie sygnału SELL z entry: ", g_entry_price);
         OpenSellPosition(g_entry_price, g_stop_loss, g_take_profit);
         g_signal = ""; // Reset sygnału po wykonaniu
      }
      else if(g_signal == "CLOSE")
      {
         if(InpDebugMode) Print("Przetwarzanie sygnału CLOSE");
         CloseAllPositions();
         g_signal = ""; // Reset sygnału po wykonaniu
      }
   }
}

//+------------------------------------------------------------------+
//| Otwieranie pozycji BUY                                           |
//+------------------------------------------------------------------+
bool OpenBuyPosition(double entry_price, double stop_loss, double take_profit)
{
   // Sprawdź, czy mamy już otwartą pozycję
   if(PositionInfo.Select(Symbol()) && PositionInfo.Magic() == InpMagicNumber)
   {
      Print("Już istnieje otwarta pozycja dla tego symbolu.");
      return false;
   }
   
   // Przygotuj parametry zlecenia
   double price = entry_price > 0 ? entry_price : SymbolInfo.Ask();
   double sl = stop_loss > 0 ? stop_loss : 0;
   double tp = take_profit > 0 ? take_profit : 0;
   
   // Sprawdź, czy SL i TP są oddalone o minimalny dystans
   if(sl > 0 && price - sl < SymbolInfo.StopsLevel() * SymbolInfo.Point())
   {
      Print("Stop Loss jest zbyt blisko aktualnej ceny!");
      return false;
   }
   
   if(tp > 0 && tp - price < SymbolInfo.StopsLevel() * SymbolInfo.Point())
   {
      Print("Take Profit jest zbyt blisko aktualnej ceny!");
      return false;
   }
   
   // Otwórz pozycję BUY
   bool result = Trade.Buy(InpVolume, Symbol(), price, sl, tp, InpComment);
   
   // Sprawdź rezultat
   if(result)
   {
      g_ticket = (int)Trade.ResultOrder();
      Print("Otwarto pozycję BUY, ticket: ", g_ticket);
      return true;
   }
   else
   {
      g_last_error = GetLastError();
      Print("Błąd podczas otwierania pozycji BUY: ", g_last_error);
      return false;
   }
}

//+------------------------------------------------------------------+
//| Otwieranie pozycji SELL                                          |
//+------------------------------------------------------------------+
bool OpenSellPosition(double entry_price, double stop_loss, double take_profit)
{
   // Sprawdź, czy mamy już otwartą pozycję
   if(PositionInfo.Select(Symbol()) && PositionInfo.Magic() == InpMagicNumber)
   {
      Print("Już istnieje otwarta pozycja dla tego symbolu.");
      return false;
   }
   
   // Przygotuj parametry zlecenia
   double price = entry_price > 0 ? entry_price : SymbolInfo.Bid();
   double sl = stop_loss > 0 ? stop_loss : 0;
   double tp = take_profit > 0 ? take_profit : 0;
   
   // Sprawdź, czy SL i TP są oddalone o minimalny dystans
   if(sl > 0 && sl - price < SymbolInfo.StopsLevel() * SymbolInfo.Point())
   {
      Print("Stop Loss jest zbyt blisko aktualnej ceny!");
      return false;
   }
   
   if(tp > 0 && price - tp < SymbolInfo.StopsLevel() * SymbolInfo.Point())
   {
      Print("Take Profit jest zbyt blisko aktualnej ceny!");
      return false;
   }
   
   // Otwórz pozycję SELL
   bool result = Trade.Sell(InpVolume, Symbol(), price, sl, tp, InpComment);
   
   // Sprawdź rezultat
   if(result)
   {
      g_ticket = (int)Trade.ResultOrder();
      Print("Otwarto pozycję SELL, ticket: ", g_ticket);
      return true;
   }
   else
   {
      g_last_error = GetLastError();
      Print("Błąd podczas otwierania pozycji SELL: ", g_last_error);
      return false;
   }
}

//+------------------------------------------------------------------+
//| Zamykanie wszystkich pozycji                                     |
//+------------------------------------------------------------------+
bool CloseAllPositions()
{
   bool result = true;
   
   // Zamknij wszystkie pozycje dla bieżącego symbolu
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         if(!Trade.PositionClose(ticket))
         {
            g_last_error = GetLastError();
            Print("Błąd podczas zamykania pozycji #", ticket, ": ", g_last_error);
            result = false;
         }
         else
         {
            Print("Zamknięto pozycję #", ticket);
         }
      }
   }
   
   return result;
} 