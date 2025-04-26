"""
Dashboard do wizualizacji wyników systemu handlowego LLM.

Ten moduł implementuje webowy dashboard do monitorowania i analizy 
wyników handlowych systemu LLM_EA. Wykorzystuje Flask jako framework webowy
oraz Plotly do interaktywnych wizualizacji.
"""
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import uuid

from Database.database import DatabaseHandler
from LLM_Engine.market_data import MarketData
from MT5_Connector.connector import MT5Connector
from Agent_Manager.risk_manager import RiskManager
from Agent_Manager.order_processor import OrderProcessor

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get('SECRET_KEY', 'tajny_klucz_do_zmiany_w_produkcji')
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'charts')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit 16MB dla plików

# Utwórz folder na wykresy, jeśli nie istnieje
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db_handler = DatabaseHandler()
mt5_connector = None  # Będzie inicjalizowany tylko gdy potrzebny
risk_manager = None
order_processor = None

# Konfiguracja
DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
DEFAULT_TIMEFRAMES = ["M15", "H1", "H4", "D1"]


@app.route('/')
@app.route('/index')
def index():
    """Strona główna dashboardu."""
    return render_template('index.html')


@app.route('/home')
def home():
    """Strona główna dashboardu."""
    # Pobierz podstawowe dane do wyświetlenia
    account_summary = {
        'balance': 10000.00,  # Przykładowe wartości, docelowo z MT5
        'pnl': 1250.50,
        'total_trades': 42,
        'win_rate': 65.2,
        'currency': 'USD'
    }
    
    # Pobierz aktywne transakcje
    active_trades = []  # Zastąpić rzeczywistymi danymi
    
    # Pobierz najnowsze pomysły handlowe
    trade_ideas = db_handler.get_trade_ideas(limit=5)
    
    return render_template('home.html', 
                          account_summary=account_summary,
                          active_trades=active_trades,
                          trade_ideas=trade_ideas)


@app.route('/statistics')
def statistics():
    """Strona ze statystykami handlowymi."""
    # Pobierz zakres dat z parametrów lub ustaw domyślne (ostatnie 30 dni)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
    
    # Pobierz dane z bazy
    trades = db_handler.get_trades(limit=1000)
    
    # Przefiltruj transakcje do wybranego zakresu dat
    filtered_trades = [
        trade for trade in trades 
        if start_date <= datetime.fromisoformat(trade["entry_time"]) <= end_date
    ]
    
    # Przygotuj dane statystyczne
    stats = calculate_statistics(filtered_trades)
    
    return render_template(
        'statistics.html', 
        stats=stats, 
        start_date=start_date.strftime('%Y-%m-%d'), 
        end_date=end_date.strftime('%Y-%m-%d')
    )


@app.route('/market_analysis')
def market_analysis():
    """Strona z analizami rynkowymi LLM."""
    # Pobierz parametry z URL lub ustaw domyślne
    symbol = request.args.get('symbol', 'EURUSD')
    timeframe = request.args.get('timeframe', 'H1')
    
    # Pobierz analizy z bazy danych
    analyses = db_handler.get_analyses(
        symbol=symbol, 
        timeframe=timeframe, 
        limit=10
    )
    
    return render_template(
        'market_analysis.html', 
        analyses=analyses, 
        symbol=symbol, 
        timeframe=timeframe,
        symbols=DEFAULT_SYMBOLS,
        timeframes=DEFAULT_TIMEFRAMES
    )


@app.route('/trade_ideas')
def trade_ideas():
    """Strona z pomysłami handlowymi."""
    # Pobierz parametry filtrowania
    symbol = request.args.get('symbol', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    # Pobierz pomysły handlowe z bazy danych
    filters = {}
    if symbol:
        filters['symbol'] = symbol
    if status:
        filters['status'] = status
    
    total, trade_ideas = db_handler.get_trade_ideas_paginated(
        page=page, 
        per_page=per_page, 
        filters=filters, 
        sort_by=sort_by, 
        order=order
    )
    
    # Oblicz liczbę stron
    pages = (total + per_page - 1) // per_page
    
    # Pobierz statystyki pomysłów handlowych
    stats = db_handler.get_trade_ideas_stats()
    
    return render_template(
        'trade_ideas.html', 
        trade_ideas=trade_ideas,
        stats=stats,
        pages=pages,
        current_page=page,
        now=datetime.now()
    )


@app.route('/trade_idea_details/<int:idea_id>')
def trade_idea_details(idea_id):
    """Szczegóły pomysłu handlowego."""
    # Pobierz pomysł handlowy z bazy danych
    trade_idea = db_handler.get_trade_idea(idea_id)
    
    if not trade_idea:
        flash('Nie znaleziono pomysłu handlowego o podanym ID.', 'danger')
        return redirect(url_for('trade_ideas'))
    
    # Pobierz powiązane transakcje
    related_trades = db_handler.get_trades_by_idea_id(idea_id)
    
    # Pobierz komentarze do pomysłu
    comments = db_handler.get_trade_idea_comments(idea_id)
    
    return render_template(
        'trade_idea_details.html',
        trade_idea=trade_idea,
        related_trades=related_trades,
        comments=comments
    )


@app.route('/add_trade_idea', methods=['GET', 'POST'])
def add_trade_idea():
    """Dodawanie nowego pomysłu handlowego."""
    if request.method == 'POST':
        try:
            # Pobierz dane z formularza
            symbol = request.form.get('symbol')
            direction = request.form.get('direction')
            entry_price = float(request.form.get('entry_price'))
            stop_loss = float(request.form.get('stop_loss'))
            take_profit = float(request.form.get('take_profit'))
            risk_percentage = float(request.form.get('risk_percentage', 1.0))
            valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%dT%H:%M')
            timeframe = request.form.get('timeframe')
            strategy = request.form.get('strategy')
            source = request.form.get('source')
            technical_analysis = request.form.get('technical_analysis')
            fundamental_analysis = request.form.get('fundamental_analysis', '')
            risk_analysis = request.form.get('risk_analysis', '')
            notes = request.form.get('notes', '')
            
            # Oblicz RR ratio
            if direction == 'BUY':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
                
            risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
            
            # Obsługa pliku z wykresem
            chart_image = None
            if 'chart_image' in request.files and request.files['chart_image'].filename:
                file = request.files['chart_image']
                if file and allowed_file(file.filename):
                    # Generuj unikalną nazwę pliku
                    filename = secure_filename(f"{symbol}_{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    chart_image = filename
            
            # Utworzenie nowego pomysłu handlowego
            idea_data = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'risk_reward_ratio': risk_reward_ratio,
                'valid_until': valid_until.isoformat(),
                'timeframe': timeframe,
                'strategy': strategy,
                'source': source,
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'risk_analysis': risk_analysis,
                'notes': notes,
                'chart_image': chart_image,
                'status': 'PENDING',
                'created_at': datetime.now().isoformat()
            }
            
            # Zapisz w bazie danych
            idea_id = db_handler.add_trade_idea(idea_data)
            
            # Sprawdź czy wykonać od razu
            if request.form.get('action') == 'execute':
                return redirect(url_for('execute_trade_idea', idea_id=idea_id))
                
            flash('Pomyślnie dodano nowy pomysł handlowy!', 'success')
            return redirect(url_for('trade_idea_details', idea_id=idea_id))
            
        except Exception as e:
            flash(f'Wystąpił błąd podczas dodawania pomysłu: {str(e)}', 'danger')
            return render_template('add_trade_idea.html', form_data=request.form)
    
    # Metoda GET - wyświetl formularz
    return render_template('add_trade_idea.html')


@app.route('/edit_trade_idea/<int:idea_id>', methods=['GET', 'POST'])
def edit_trade_idea(idea_id):
    """Edycja istniejącego pomysłu handlowego."""
    # Pobierz dane pomysłu
    trade_idea = db_handler.get_trade_idea(idea_id)
    
    if not trade_idea:
        flash('Nie znaleziono pomysłu handlowego o podanym ID.', 'danger')
        return redirect(url_for('trade_ideas'))
    
    if request.method == 'POST':
        try:
            # Pobierz dane z formularza
            symbol = request.form.get('symbol')
            direction = request.form.get('direction')
            entry_price = float(request.form.get('entry_price'))
            stop_loss = float(request.form.get('stop_loss'))
            take_profit = float(request.form.get('take_profit'))
            risk_percentage = float(request.form.get('risk_percentage', 1.0))
            valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%dT%H:%M')
            timeframe = request.form.get('timeframe')
            strategy = request.form.get('strategy')
            source = request.form.get('source')
            technical_analysis = request.form.get('technical_analysis')
            fundamental_analysis = request.form.get('fundamental_analysis', '')
            risk_analysis = request.form.get('risk_analysis', '')
            notes = request.form.get('notes', '')
            
            # Oblicz RR ratio
            if direction == 'BUY':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
                
            risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
            
            # Obsługa pliku z wykresem
            chart_image = trade_idea.get('chart_image')
            
            # Sprawdź czy usunąć istniejący wykres
            if request.form.get('delete_chart') and chart_image:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], chart_image))
                    chart_image = None
                except Exception as e:
                    pass  # Ignoruj błędy usuwania
            
            # Sprawdź czy dodać nowy wykres
            if 'chart_image' in request.files and request.files['chart_image'].filename:
                file = request.files['chart_image']
                if file and allowed_file(file.filename):
                    # Usuń stary plik jeśli istnieje
                    if chart_image:
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], chart_image))
                        except Exception as e:
                            pass  # Ignoruj błędy usuwania
                    
                    # Generuj unikalną nazwę pliku
                    filename = secure_filename(f"{symbol}_{uuid.uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    chart_image = filename
            
            # Aktualizacja danych pomysłu handlowego
            idea_data = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'risk_reward_ratio': risk_reward_ratio,
                'valid_until': valid_until.isoformat(),
                'timeframe': timeframe,
                'strategy': strategy,
                'source': source,
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'risk_analysis': risk_analysis,
                'notes': notes,
                'chart_image': chart_image,
                'updated_at': datetime.now().isoformat()
            }
            
            # Zaktualizuj w bazie danych
            db_handler.update_trade_idea(idea_id, idea_data)
            
            # Sprawdź czy wykonać po edycji
            if request.form.get('action') == 'execute' and trade_idea.get('status') == 'PENDING':
                return redirect(url_for('execute_trade_idea', idea_id=idea_id))
                
            flash('Pomyślnie zaktualizowano pomysł handlowy!', 'success')
            return redirect(url_for('trade_idea_details', idea_id=idea_id))
            
        except Exception as e:
            flash(f'Wystąpił błąd podczas edycji pomysłu: {str(e)}', 'danger')
    
    # Metoda GET - wyświetl formularz z danymi
    return render_template('edit_trade_idea.html', trade_idea=trade_idea)


@app.route('/execute_trade_idea/<int:idea_id>')
def execute_trade_idea(idea_id):
    """Wykonanie pomysłu handlowego."""
    global mt5_connector, risk_manager, order_processor
    
    # Pobierz dane pomysłu
    trade_idea = db_handler.get_trade_idea(idea_id)
    
    if not trade_idea:
        flash('Nie znaleziono pomysłu handlowego o podanym ID.', 'danger')
        return redirect(url_for('trade_ideas'))
    
    if trade_idea.get('status') != 'PENDING':
        flash('Tylko oczekujące pomysły handlowe mogą być wykonane.', 'warning')
        return redirect(url_for('trade_idea_details', idea_id=idea_id))
    
    try:
        # Inicjalizuj MT5Connector jeśli nie istnieje
        if mt5_connector is None:
            mt5_connector = MT5Connector()
            
        # Inicjalizuj RiskManager jeśli nie istnieje
        if risk_manager is None:
            risk_manager = RiskManager(db_handler)
            risk_manager.set_mt5_connector(mt5_connector)
            
        # Inicjalizuj OrderProcessor jeśli nie istnieje
        if order_processor is None:
            order_processor = OrderProcessor(db_handler, mt5_connector, risk_manager)
        
        # Przetworzyć pomysł handlowy
        result = order_processor.process_trade_idea(trade_idea)
        
        if result.get('success'):
            flash('Pomyślnie wykonano pomysł handlowy!', 'success')
            # Aktualizuj status pomysłu w bazie danych
            db_handler.update_trade_idea(idea_id, {'status': 'EXECUTED'})
        else:
            flash(f'Nie udało się wykonać pomysłu: {result.get("error")}', 'danger')
            # Aktualizuj status pomysłu w bazie danych
            db_handler.update_trade_idea(idea_id, {'status': 'REJECTED', 'rejection_reason': result.get('error')})
            
    except Exception as e:
        flash(f'Wystąpił błąd podczas wykonywania pomysłu: {str(e)}', 'danger')
        # Aktualizuj status pomysłu w bazie danych
        db_handler.update_trade_idea(idea_id, {'status': 'REJECTED', 'rejection_reason': str(e)})
    
    return redirect(url_for('trade_idea_details', idea_id=idea_id))


@app.route('/delete_trade_idea/<int:idea_id>', methods=['POST'])
def delete_trade_idea(idea_id):
    """Usunięcie pomysłu handlowego."""
    # Pobierz dane pomysłu
    trade_idea = db_handler.get_trade_idea(idea_id)
    
    if not trade_idea:
        flash('Nie znaleziono pomysłu handlowego o podanym ID.', 'danger')
        return redirect(url_for('trade_ideas'))
    
    try:
        # Usuń zdjęcie wykresu jeśli istnieje
        if trade_idea.get('chart_image'):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], trade_idea['chart_image']))
            except Exception as e:
                pass  # Ignoruj błędy usuwania pliku
        
        # Usuń pomysł z bazy danych
        db_handler.delete_trade_idea(idea_id)
        
        flash('Pomyślnie usunięto pomysł handlowy!', 'success')
    except Exception as e:
        flash(f'Wystąpił błąd podczas usuwania pomysłu: {str(e)}', 'danger')
    
    return redirect(url_for('trade_ideas'))


@app.route('/add_comment/<int:idea_id>', methods=['POST'])
def add_comment(idea_id):
    """Dodawanie komentarza do pomysłu handlowego."""
    # Pobierz dane pomysłu
    trade_idea = db_handler.get_trade_idea(idea_id)
    
    if not trade_idea:
        flash('Nie znaleziono pomysłu handlowego o podanym ID.', 'danger')
        return redirect(url_for('trade_ideas'))
    
    # Pobierz treść komentarza
    comment_text = request.form.get('comment', '').strip()
    
    if not comment_text:
        flash('Komentarz nie może być pusty.', 'warning')
        return redirect(url_for('trade_idea_details', idea_id=idea_id))
    
    try:
        # Dodaj komentarz do bazy danych
        comment_data = {
            'trade_idea_id': idea_id,
            'author': 'Użytkownik',  # Docelowo zastąpić nazwą zalogowanego użytkownika
            'content': comment_text,
            'created_at': datetime.now().isoformat()
        }
        
        db_handler.add_trade_idea_comment(comment_data)
        
        flash('Dodano komentarz!', 'success')
    except Exception as e:
        flash(f'Wystąpił błąd podczas dodawania komentarza: {str(e)}', 'danger')
    
    return redirect(url_for('trade_idea_details', idea_id=idea_id))


@app.route('/account_status')
def account_status():
    """Strona ze statusem konta handlowego."""
    global mt5_connector
    
    # Inicjalizuj MT5Connector tylko jeśli potrzebny
    if mt5_connector is None:
        try:
            mt5_connector = MT5Connector()
        except Exception as e:
            return render_template('account_status.html', error=str(e))
    
    # Pobierz informacje o koncie
    try:
        account_info = mt5_connector.get_account_info()
        open_positions = mt5_connector.get_open_positions()
    except Exception as e:
        return render_template('account_status.html', error=str(e))
    
    return render_template(
        'account_status.html', 
        account_info=account_info, 
        open_positions=open_positions
    )


@app.route('/api/equity_chart')
def equity_chart():
    """API endpoint zwracający dane dla wykresu kapitału."""
    # Pobierz historię transakcji z bazy danych
    trades = db_handler.get_trades(limit=1000)
    
    # Oblicz krzywą kapitału
    equity_data = calculate_equity_curve(trades)
    
    return jsonify(equity_data)


@app.route('/api/performance_by_symbol')
def performance_by_symbol():
    """API endpoint zwracający wyniki handlowe w podziale na instrumenty."""
    # Pobierz transakcje z bazy danych
    trades = db_handler.get_trades(limit=1000)
    
    # Grupuj wyniki według symboli
    symbols_data = {}
    for trade in trades:
        symbol = trade.get('symbol', 'Unknown')
        profit_loss = trade.get('profit_loss', 0)
        
        if symbol not in symbols_data:
            symbols_data[symbol] = {'count': 0, 'profit_loss': 0}
        
        symbols_data[symbol]['count'] += 1
        symbols_data[symbol]['profit_loss'] += profit_loss
    
    # Konwertuj na format odpowiedni dla wykresu
    result = []
    for symbol, data in symbols_data.items():
        result.append({
            'symbol': symbol,
            'count': data['count'],
            'profit_loss': data['profit_loss']
        })
    
    return jsonify(result)


def calculate_statistics(trades):
    """Oblicza statystyki handlowe na podstawie historii transakcji."""
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'total_loss': 0,
            'net_profit': 0,
            'profit_factor': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'largest_profit': 0,
            'largest_loss': 0
        }
    
    # Inicjalizacja zmiennych
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.get('profit_loss', 0) > 0)
    losing_trades = sum(1 for t in trades if t.get('profit_loss', 0) < 0)
    
    # Obliczenie zysków i strat
    winning_amounts = [t.get('profit_loss', 0) for t in trades if t.get('profit_loss', 0) > 0]
    losing_amounts = [abs(t.get('profit_loss', 0)) for t in trades if t.get('profit_loss', 0) < 0]
    
    total_profit = sum(winning_amounts) if winning_amounts else 0
    total_loss = sum(losing_amounts) if losing_amounts else 0
    net_profit = total_profit - total_loss
    
    # Obliczenie wskaźników
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
    avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
    largest_profit = max(winning_amounts) if winning_amounts else 0
    largest_loss = max(losing_amounts) if losing_amounts else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_profit': round(total_profit, 2),
        'total_loss': round(total_loss, 2),
        'net_profit': round(net_profit, 2),
        'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf',
        'avg_profit': round(avg_profit, 2),
        'avg_loss': round(avg_loss, 2),
        'largest_profit': round(largest_profit, 2),
        'largest_loss': round(largest_loss, 2)
    }


def calculate_equity_curve(trades):
    """Oblicza krzywą kapitału na podstawie historii transakcji."""
    if not trades:
        return []
    
    # Posortuj transakcje według czasu
    sorted_trades = sorted(trades, key=lambda x: x.get('entry_time', ''))
    
    # Inicjalizuj krzywą kapitału
    equity_curve = []
    running_balance = 1000.0  # Początkowy kapitał
    
    for trade in sorted_trades:
        close_time = trade.get('close_time', None)
        profit_loss = trade.get('profit_loss', 0)
        
        if close_time and profit_loss is not None:
            running_balance += profit_loss
            equity_curve.append({
                'date': close_time,
                'equity': running_balance
            })
    
    return equity_curve


def allowed_file(filename):
    """Sprawdza czy plik ma dozwolone rozszerzenie."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Filtry do szablonów
@app.template_filter('status_badge')
def status_badge_filter(status):
    """Zwraca klasę bootstrap dla badge ze statusem."""
    if status == 'PENDING':
        return 'bg-warning'
    elif status == 'EXECUTED':
        return 'bg-success'
    elif status == 'EXPIRED':
        return 'bg-secondary'
    elif status == 'REJECTED':
        return 'bg-danger'
    else:
        return 'bg-info'


@app.template_filter('status_label')
def status_label_filter(status):
    """Zwraca etykietę dla statusu po polsku."""
    if status == 'PENDING':
        return 'Oczekujący'
    elif status == 'EXECUTED':
        return 'Wykonany'
    elif status == 'EXPIRED':
        return 'Wygasły'
    elif status == 'REJECTED':
        return 'Odrzucony'
    else:
        return status


@app.template_filter('datetime')
def datetime_filter(value, format='%d-%m-%Y %H:%M'):
    """Formatuje datę."""
    if value is None:
        return ''
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.strftime(format)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 