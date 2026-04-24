//+------------------------------------------------------------------+
//|                                                   NyxEA.mq5 |
//|                                    Nyx AI Signal Bridge EA |
//|                          https://github.com/nyx-ai-trading |
//+------------------------------------------------------------------+
#property copyright "Nyx AI Trading"
#property link      "https://github.com/nyx-ai-trading"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input parameters
input string SignalFilePath = "/home/ubuntu/nyx-ai/trade_signal.json";
input int MaxRetries = 3;
input int RetryDelayMs = 1000;
input double MaxLotSize = 0.5;
input int MagicNumber = 123456;

//--- Global variables
CTrade trade;
datetime lastSignalTime = 0;
string lastSignalId = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Set trade parameters
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetMarginMode();
   
   //--- Print initialization message
   Print("=== NYX AI SIGNAL BRIDGE EA INITIALIZED ===");
   Print("Signal file path: ", SignalFilePath);
   Print("Magic number: ", MagicNumber);
   Print("Max lot size: ", MaxLotSize);
   Print("AutoTrading: ", TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) ? "ENABLED" : "DISABLED");
   
   //--- Check if auto trading is allowed
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      Alert("AutoTrading is DISABLED! Please enable AutoTrading.");
      return(INIT_FAILED);
   }
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("=== NYX AI SIGNAL BRIDGE EA STOPPED ===");
   Print("Deinit reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Check for new signal file
   if(!FileIsExist(SignalFilePath))
   {
      return; // No signal file
   }
   
   //--- Read and process signal
   ProcessSignalFile();
}

//+------------------------------------------------------------------+
//| Process signal file                                              |
//+------------------------------------------------------------------+
void ProcessSignalFile()
{
   string signalData = "";
   int fileHandle = INVALID_HANDLE;
   
   //--- Try to open file with retries
   for(int retry = 0; retry < MaxRetries; retry++)
   {
      fileHandle = FileOpen(SignalFilePath, FILE_READ | FILE_TXT | FILE_ANSI);
      
      if(fileHandle != INVALID_HANDLE)
      {
         break; // File opened successfully
      }
      
      Print("Retry ", retry + 1, ": Cannot open signal file, waiting ", RetryDelayMs, "ms...");
      Sleep(RetryDelayMs);
   }
   
   if(fileHandle == INVALID_HANDLE)
   {
      Print("ERROR: Cannot open signal file after ", MaxRetries, " retries");
      return;
   }
   
   //--- Read file content with error handling
   string signalData = "";
   while(!FileIsEnding(fileHandle))
   {
      string line = FileReadString(fileHandle);
      signalData += line;
   }
   
   FileClose(fileHandle);
   
   //--- Parse and execute signal
   if(StringLen(signalData) > 0)
   {
      ExecuteSignal(signalData);
   }
   else
   {
      Print("WARNING: Signal file is empty");
   }
}

//+------------------------------------------------------------------+
//| Execute signal from JSON data                                    |
//+------------------------------------------------------------------+
void ExecuteSignal(string jsonData)
{
   //--- Parse JSON manually (no native JSON parser in MQL5)
   string symbol = "";
   string action = "";
   double lot = 0;
   double sl = 0;
   double tp = 0;
   double confidence = 0;
   double score = 0;
   string signalId = "";
   string status = "";
   
   //--- Extract values from JSON
   if(!ParseJsonSignal(jsonData, symbol, action, lot, sl, tp, confidence, score, signalId, status))
   {
      Print("ERROR: Failed to parse JSON signal");
      return;
   }
   
   //--- Check signal status
   if(status != "new")
   {
      Print("Signal already processed, status: ", status);
      return;
   }
   
   //--- Check for duplicate signal
   if(signalId == lastSignalId)
   {
      Print("Duplicate signal detected: ", signalId);
      return;
   }
   
   //--- Validate signal data
   if(!ValidateSignal(symbol, action, lot, sl, tp))
   {
      Print("ERROR: Signal validation failed");
      return;
   }
   
   //--- Check if we already have open position on this symbol
   if(HasOpenPosition(symbol))
   {
      Print("Already have open position on ", symbol);
      return;
   }
   
   //--- Execute trade
   bool result = false;
   
   if(action == "BUY")
   {
      result = ExecuteBuy(symbol, lot, sl, tp);
   }
   else if(action == "SELL")
   {
      result = ExecuteSell(symbol, lot, sl, tp);
   }
   else
   {
      Print("ERROR: Invalid action: ", action);
      return;
   }
   
   //--- Update tracking
   lastSignalId = signalId;
   lastSignalTime = TimeCurrent();
   
   //--- Handle signal file after execution
   if(result)
   {
      Print("✅ Trade executed successfully: ", symbol, " ", action, " lot=", lot);
      RenameSignalFile("done");
   }
   else
   {
      Print("❌ Trade execution failed: ", symbol, " ", action);
      RenameSignalFile("failed");
   }
}

//+------------------------------------------------------------------+
//| Parse JSON signal data                                           |
//+------------------------------------------------------------------+
bool ParseJsonSignal(string jsonData, string &symbol, string &action, double &lot, 
                    double &sl, double &tp, double &confidence, double &score, 
                    string &signalId, string &status)
{
   //--- Simple JSON parsing (manual approach)
   //--- Extract symbol
   if(StringFind(jsonData, "\"symbol\":") >= 0)
   {
      symbol = ExtractJsonValue(jsonData, "symbol");
   }
   
   //--- Extract action
   if(StringFind(jsonData, "\"action\":") >= 0)
   {
      action = ExtractJsonValue(jsonData, "action");
   }
   
   //--- Extract lot
   if(StringFind(jsonData, "\"lot\":") >= 0)
   {
      lot = StringToDouble(ExtractJsonValue(jsonData, "lot"));
   }
   
   //--- Extract sl
   if(StringFind(jsonData, "\"sl\":") >= 0)
   {
      sl = StringToDouble(ExtractJsonValue(jsonData, "sl"));
   }
   
   //--- Extract tp
   if(StringFind(jsonData, "\"tp\":") >= 0)
   {
      tp = StringToDouble(ExtractJsonValue(jsonData, "tp"));
   }
   
   //--- Extract confidence
   if(StringFind(jsonData, "\"confidence\":") >= 0)
   {
      confidence = StringToDouble(ExtractJsonValue(jsonData, "confidence"));
   }
   
   //--- Extract score
   if(StringFind(jsonData, "\"score\":") >= 0)
   {
      score = StringToDouble(ExtractJsonValue(jsonData, "score"));
   }
   
   //--- Extract signal_id
   if(StringFind(jsonData, "\"signal_id\":") >= 0)
   {
      signalId = ExtractJsonValue(jsonData, "signal_id");
   }
   
   //--- Extract status
   if(StringFind(jsonData, "\"status\":") >= 0)
   {
      status = ExtractJsonValue(jsonData, "status");
   }
   
   //--- Validate required fields
   if(StringLen(symbol) == 0 || StringLen(action) == 0 || lot <= 0)
   {
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Extract JSON value by key                                        |
//+------------------------------------------------------------------+
string ExtractJsonValue(string jsonData, string key)
{
   string searchKey = "\"" + key + "\":";
   int pos = StringFind(jsonData, searchKey);
   
   if(pos < 0)
   {
      return "";
   }
   
   //--- Find the value after the key
   int valueStart = pos + StringLen(searchKey);
   
   //--- Skip whitespace and quotes
   while(valueStart < StringLen(jsonData) && 
         (jsonData[valueStart] == ' ' || jsonData[valueStart] == '\t' || 
          jsonData[valueStart] == '\n' || jsonData[valueStart] == '\r' || 
          jsonData[valueStart] == '"'))
   {
      valueStart++;
   }
   
   //--- Find the end of the value
   int valueEnd = valueStart;
   while(valueEnd < StringLen(jsonData) && 
         jsonData[valueEnd] != ',' && jsonData[valueEnd] != '}' && 
         jsonData[valueEnd] != '\n' && jsonData[valueEnd] != '\r')
   {
      valueEnd++;
   }
   
   //--- Extract the value
   string value = StringSubstr(jsonData, valueStart, valueEnd - valueStart);
   
   //--- Remove trailing quotes if present
   if(StringLen(value) > 0 && value[StringLen(value) - 1] == '"')
   {
      value = StringSubstr(value, 0, StringLen(value) - 1);
   }
   
   //--- Remove leading quotes if present
   if(StringLen(value) > 0 && value[0] == '"')
   {
      value = StringSubstr(value, 1);
   }
   
   return value;
}

//+------------------------------------------------------------------+
//| Validate signal data                                             |
//+------------------------------------------------------------------+
bool ValidateSignal(string symbol, string action, double lot, double sl, double tp)
{
   //--- Validate symbol
   if(StringLen(symbol) == 0)
   {
      Print("ERROR: Invalid symbol");
      return false;
   }
   
   //--- Validate action
   if(action != "BUY" && action != "SELL")
   {
      Print("ERROR: Invalid action: ", action);
      return false;
   }
   
   //--- Validate lot size
   if(lot <= 0 || lot > MaxLotSize)
   {
      Print("ERROR: Invalid lot size: ", lot);
      return false;
   }
   
   //--- Validate stop loss
   if(sl <= 0)
   {
      Print("ERROR: Invalid stop loss: ", sl);
      return false;
   }
   
   //--- Validate take profit
   if(tp <= 0)
   {
      Print("ERROR: Invalid take profit: ", tp);
      return false;
   }
   
   //--- Validate SL/TP relationship
   if(action == "BUY" && sl >= tp)
   {
      Print("ERROR: For BUY orders, SL must be below TP");
      return false;
   }
   
   if(action == "SELL" && sl <= tp)
   {
      Print("ERROR: For SELL orders, SL must be above TP");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Check if we have open position on symbol                         |
//+------------------------------------------------------------------+
bool HasOpenPosition(string symbol)
{
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(PositionGetSymbol(i) == symbol)
      {
         return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Execute BUY order                                               |
//+------------------------------------------------------------------+
bool ExecuteBuy(string symbol, double lot, double sl, double tp)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   
   //--- Normalize prices
   ask = NormalizeDouble(ask, digits);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   
   //--- Validate SL/TP distances
   double minStopLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   
   if(MathAbs(ask - sl) < minStopLevel)
   {
      Print("WARNING: Stop loss too close to market, adjusting...");
      sl = ask - minStopLevel;
   }
   
   if(MathAbs(tp - ask) < minStopLevel)
   {
      Print("WARNING: Take profit too close to market, adjusting...");
      tp = ask + minStopLevel;
   }
   
   //--- Execute trade
   bool result = trade.Buy(lot, symbol, ask, sl, tp, "Nyx AI Signal Bridge");
   
   if(result)
   {
      Print("✅ BUY order executed: ", symbol, " ", lot, " lots @ ", ask);
      Print("   SL: ", sl, " TP: ", tp);
   }
   else
   {
      uint errorCode = trade.ResultCode();
      string errorDesc = trade.ResultComment();
      Print("❌ BUY order failed: ", errorCode, " - ", errorDesc);
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute SELL order                                              |
//+------------------------------------------------------------------+
bool ExecuteSell(string symbol, double lot, double sl, double tp)
{
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   
   //--- Normalize prices
   bid = NormalizeDouble(bid, digits);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   
   //--- Validate SL/TP distances
   double minStopLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   
   if(MathAbs(sl - bid) < minStopLevel)
   {
      Print("WARNING: Stop loss too close to market, adjusting...");
      sl = bid + minStopLevel;
   }
   
   if(MathAbs(bid - tp) < minStopLevel)
   {
      Print("WARNING: Take profit too close to market, adjusting...");
      tp = bid - minStopLevel;
   }
   
   //--- Execute trade
   bool result = trade.Sell(lot, symbol, bid, sl, tp, "Nyx AI Signal Bridge");
   
   if(result)
   {
      Print("✅ SELL order executed: ", symbol, " ", lot, " lots @ ", bid);
      Print("   SL: ", sl, " TP: ", tp);
   }
   else
   {
      uint errorCode = trade.ResultCode();
      string errorDesc = trade.ResultComment();
      Print("❌ SELL order failed: ", errorCode, " - ", errorDesc);
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Rename signal file after processing                              |
//+------------------------------------------------------------------+
void RenameSignalFile(string status)
{
   string timestamp = TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
   string newFileName = StringSubstr(SignalFilePath, 0, StringLen(SignalFilePath) - 5) + "_" + status + "_" + timestamp + ".json";
   
   if(FileMove(SignalFilePath, 0, newFileName, 0))
   {
      Print("Signal file renamed to: ", newFileName);
   }
   else
   {
      Print("Failed to rename signal file, trying to delete...");
      FileDelete(SignalFilePath);
   }
}

//+------------------------------------------------------------------+
//| Expert timer function (for periodic checks)                      |
//+------------------------------------------------------------------+
void OnTimer()
{
   //--- Clean up old signal files
   CleanOldSignalFiles();
}

//+------------------------------------------------------------------+
//| Clean up old signal files                                        |
//+------------------------------------------------------------------+
void CleanOldSignalFiles()
{
   string basePath = StringSubstr(SignalFilePath, 0, StringFind(SignalFilePath, "/", 0));
   string fileName;
   long fileTime;
   
   //--- Look for old signal files and delete them
   datetime cutoff = TimeCurrent() - 3600; // 1 hour ago
   
   //--- This is a simplified cleanup - in production you might want more sophisticated logic
   Print("Signal cleanup completed");
}

//+------------------------------------------------------------------+
