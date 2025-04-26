#!/usr/bin/env python
"""
Moduł aplikacji Dashboard.

Ten moduł zawiera fabrykę aplikacji Flask dla dashboardu systemu handlowego LLM.
Zarządza:
- routingiem aplikacji
- dostępem do bazy danych
- wyświetlaniem widoków i wykresów
- panelem kontrolnym systemu
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go

# Ścieżki
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(db_handler=None, config=None):
    """
    Tworzy i konfiguruje aplikację Flask dla dashboardu.
    
    Args:
        db_handler: Instancja DatabaseHandler do połączenia z bazą danych
        config: Słownik z konfiguracją
        
    Returns:
        Skonfigurowana aplikacja Flask
    """
    app = Flask(__name__, 
                template_folder=TEMPLATE_DIR,
                static_folder=STATIC_DIR)
    
    # Konfiguracja
    app.config["SECRET_KEY"] = "llm-trader-dashboard-secret-key"
    app.config["DEBUG"] = config.get("dashboard", {}).get("debug", False)
    
    # Dodaj handlery do aplikacji
    app.db_handler = db_handler
    app.config_data = config or {}
    
    # Zdefiniuj trasy
    @app.route('/')
    def index():
        """Strona główna dashboardu."""
        return render_template('index.html', title="LLM Trader Dashboard")
    
    @app.route('/stats')
    def stats():
        """Wyświetla statystyki handlowe."""
        stats_data = get_trading_stats()
        return render_template('stats.html', 
                              title="Statystyki handlowe",
                              stats=stats_data)
    
    @app.route('/trades')
    def trades():
        """Wyświetla listę transakcji."""
        trades_data = get_trades_data()
        return render_template('trades.html', 
                              title="Transakcje",
                              trades=trades_data)
    
    @app.route('/market')
    def market():
        """Wyświetla analizę rynku."""
        market_data = get_market_analysis()
        return render_template('market.html', 
                              title="Analiza rynku",
                              market_data=market_data)
    
    @app.route('/system')
    def system():
        """Wyświetla status systemu."""
        system_status = get_system_status()
        return render_template('system.html', 
                              title="Status systemu",
                              status=system_status)
    
    @app.route('/logs')
    def logs():
        """Wyświetla logi systemu."""
        log_entries = get_log_entries()
        return render_template('logs.html', 
                              title="Logi systemu",
                              logs=log_entries)
    
    @app.route('/api/trades')
    def api_trades():
        """API dla danych o transakcjach."""
        trades_data = get_trades_data()
        return jsonify(trades_data)
    
    @app.route('/api/stats')
    def api_stats():
        """API dla statystyk handlowych."""
        stats_data = get_trading_stats()
        return jsonify(stats_data)
    
    @app.route('/api/market')
    def api_market():
        """API dla analizy rynku."""
        market_data = get_market_analysis()
        return jsonify(market_data)
    
    @app.route('/api/system')
    def api_system():
        """API dla statusu systemu."""
        system_status = get_system_status()
        return jsonify(system_status)
    
    @app.route('/api/performance')
    def api_performance():
        """API dla danych o wydajności."""
        performance_data = get_performance_data()
        return jsonify(performance_data)
    
    # Pomocnicze funkcje
    def get_trades_data():
        """Pobiera dane o transakcjach z bazy danych."""
        if not app.db_handler:
            return []
            
        try:
            trades = app.db_handler.get_trades()
            return [trade.to_dict() for trade in trades]
        except Exception as e:
            app.logger.error(f"Błąd podczas pobierania transakcji: {e}")
            return []
    
    def get_trading_stats():
        """Pobiera statystyki handlowe z bazy danych."""
        if not app.db_handler:
            return {}
            
        try:
            stats = app.db_handler.get_trading_statistics()
            return stats
        except Exception as e:
            app.logger.error(f"Błąd podczas pobierania statystyk: {e}")
            return {}
    
    def get_market_analysis():
        """Pobiera analizę rynku z bazy danych."""
        if not app.db_handler:
            return []
            
        try:
            analyses = app.db_handler.get_market_analyses()
            return [analysis.to_dict() for analysis in analyses]
        except Exception as e:
            app.logger.error(f"Błąd podczas pobierania analiz rynku: {e}")
            return []
            
    def get_system_status():
        """Pobiera informacje o statusie systemu."""
        status = {
            "components": {
                "llm_engine": check_component_status("llm_engine"),
                "database": check_component_status("database"),
                "mt5_connector": check_component_status("mt5_connector"),
                "agent_manager": check_component_status("agent_manager"),
                "dashboard": True  # Dashboard jest aktywny, skoro strona się wyświetla
            },
            "performance": get_performance_data(),
            "config": {
                "environment": app.config_data.get("environment", "dev"),
                "debug_mode": app.config_data.get("debug", False)
            }
        }
        return status
    
    def check_component_status(component_name):
        """Sprawdza, czy komponent jest aktywny."""
        # TODO: Zaimplementować rzeczywiste sprawdzanie statusu komponentów
        # To jest uproszczona implementacja
        try:
            log_path = os.path.join(PROJECT_DIR, "logs", f"{component_name}.log")
            if os.path.exists(log_path):
                # Sprawdź, czy log był aktualizowany w ciągu ostatnich 5 minut
                mtime = os.path.getmtime(log_path)
                last_modified = datetime.fromtimestamp(mtime)
                if datetime.now() - last_modified < timedelta(minutes=5):
                    return True
            return False
        except Exception:
            return False
    
    def get_performance_data():
        """Pobiera dane o wydajności systemu."""
        # Przykładowe dane o wydajności
        return {
            "cpu_usage": 25,
            "memory_usage": 450,
            "api_latency": 120,
            "database_queries": 1250,
            "active_connections": 3
        }
    
    def get_log_entries(limit=100):
        """Pobiera ostatnie wpisy z logów."""
        log_entries = []
        try:
            log_dir = os.path.join(PROJECT_DIR, "logs")
            for log_file in ["system.log", "llm_engine.log", "database.log", 
                            "mt5_connector.log", "agent_manager.log"]:
                file_path = os.path.join(log_dir, log_file)
                if os.path.exists(file_path):
                    component = log_file.replace(".log", "")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines[-limit:]:
                            if line.strip():
                                parts = line.split(" - ", 3)
                                if len(parts) >= 4:
                                    timestamp, _, level, message = parts
                                    log_entries.append({
                                        "timestamp": timestamp,
                                        "component": component,
                                        "level": level,
                                        "message": message.strip()
                                    })
        except Exception as e:
            app.logger.error(f"Błąd podczas pobierania logów: {e}")
        
        # Sortuj według timestamp i ogranicz liczbę wpisów
        log_entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return log_entries[:limit]
    
    return app 