/**
 * Główny plik JavaScript dla dashboardu LLM Trading System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja tooltipów Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Obsługa podglądu obrazów wykresów
    var chartImages = document.querySelectorAll('.chart-preview');
    chartImages.forEach(function(image) {
        image.addEventListener('click', function() {
            var modalImage = document.getElementById('chartModalImage');
            var imageModal = new bootstrap.Modal(document.getElementById('chartModal'));
            
            if (modalImage && imageModal) {
                modalImage.src = this.src;
                imageModal.show();
            }
        });
    });

    // Walidacja formularza trade idea
    var tradeForm = document.getElementById('tradeIdeaForm');
    if (tradeForm) {
        tradeForm.addEventListener('submit', function(event) {
            var symbol = document.getElementById('symbol').value;
            var direction = document.getElementById('direction').value;
            var entryPrice = parseFloat(document.getElementById('entry_price').value);
            var stopLoss = parseFloat(document.getElementById('stop_loss').value);
            var takeProfit = parseFloat(document.getElementById('take_profit').value);
            
            // Sprawdź czy kierunek jest prawidłowy
            if (direction !== 'BUY' && direction !== 'SELL') {
                event.preventDefault();
                alert('Proszę wybrać prawidłowy kierunek transakcji (BUY/SELL).');
                return false;
            }
            
            // Sprawdź logikę poziomów dla pozycji BUY
            if (direction === 'BUY') {
                if (stopLoss >= entryPrice) {
                    event.preventDefault();
                    alert('Dla pozycji BUY, stop loss musi być poniżej ceny wejścia.');
                    return false;
                }
                if (takeProfit <= entryPrice) {
                    event.preventDefault();
                    alert('Dla pozycji BUY, take profit musi być powyżej ceny wejścia.');
                    return false;
                }
            }
            
            // Sprawdź logikę poziomów dla pozycji SELL
            if (direction === 'SELL') {
                if (stopLoss <= entryPrice) {
                    event.preventDefault();
                    alert('Dla pozycji SELL, stop loss musi być powyżej ceny wejścia.');
                    return false;
                }
                if (takeProfit >= entryPrice) {
                    event.preventDefault();
                    alert('Dla pozycji SELL, take profit musi być poniżej ceny wejścia.');
                    return false;
                }
            }
            
            // Oblicz RR ratio
            var risk, reward, riskRewardRatio;
            if (direction === 'BUY') {
                risk = entryPrice - stopLoss;
                reward = takeProfit - entryPrice;
            } else { // SELL
                risk = stopLoss - entryPrice;
                reward = entryPrice - takeProfit;
            }
            
            riskRewardRatio = reward / risk;
            
            // Sprawdź czy RR ratio jest akceptowalne
            if (riskRewardRatio < 1.0) {
                if (!confirm('Stosunek zysku do ryzyka wynosi ' + riskRewardRatio.toFixed(2) + ', co jest mniejsze niż zalecane 1.0. Czy chcesz kontynuować?')) {
                    event.preventDefault();
                    return false;
                }
            }
            
            return true;
        });
    }

    // Obsługa filtrowania na stronach z listami
    var filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            // Usuń puste pola z formularza przed wysłaniem
            var inputs = filterForm.querySelectorAll('input, select');
            inputs.forEach(function(input) {
                if (input.value === '' || input.value === null) {
                    input.disabled = true;
                }
            });
        });
    }

    // Obsługa akcji usuwania z potwierdzeniem
    var deleteButtons = document.querySelectorAll('[data-action="delete"]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm('Czy na pewno chcesz usunąć ten element? Ta operacja jest nieodwracalna.')) {
                event.preventDefault();
                return false;
            }
        });
    });

    // Obsługa dynamicznego podglądu plików
    var fileInput = document.getElementById('chart_image');
    var previewContainer = document.getElementById('imagePreviewContainer');
    var previewImage = document.getElementById('imagePreview');
    
    if (fileInput && previewContainer && previewImage) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files && fileInput.files[0]) {
                var reader = new FileReader();
                
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    previewContainer.style.display = 'block';
                }
                
                reader.readAsDataURL(fileInput.files[0]);
            } else {
                previewContainer.style.display = 'none';
            }
        });
    }
    
    // Inicjalizacja i ładowanie wykresów
    loadCharts();
});

/**
 * Funkcja ładująca wykresy na stronach ze statystykami
 */
function loadCharts() {
    // Wykres equity
    var equityChartContainer = document.getElementById('equityChart');
    if (equityChartContainer) {
        fetch('/api/equity_chart')
            .then(response => response.json())
            .then(data => {
                createEquityChart(equityChartContainer, data);
            })
            .catch(error => {
                console.error('Błąd podczas ładowania danych wykresu equity:', error);
                equityChartContainer.innerHTML = '<div class="alert alert-danger">Błąd podczas ładowania wykresu</div>';
            });
    }
    
    // Wykres wyników wg symboli
    var symbolPerformanceContainer = document.getElementById('symbolPerformanceChart');
    if (symbolPerformanceContainer) {
        fetch('/api/performance_by_symbol')
            .then(response => response.json())
            .then(data => {
                createSymbolPerformanceChart(symbolPerformanceContainer, data);
            })
            .catch(error => {
                console.error('Błąd podczas ładowania danych wykresu wg symboli:', error);
                symbolPerformanceContainer.innerHTML = '<div class="alert alert-danger">Błąd podczas ładowania wykresu</div>';
            });
    }
}

/**
 * Tworzy wykres equity
 */
function createEquityChart(container, data) {
    var trace = {
        x: data.dates,
        y: data.equity,
        type: 'scatter',
        mode: 'lines',
        name: 'Equity',
        line: {
            color: '#007bff',
            width: 2
        }
    };
    
    var layout = {
        title: 'Krzywa Equity',
        xaxis: {
            title: 'Data'
        },
        yaxis: {
            title: 'Equity'
        },
        autosize: true,
        margin: {
            l: 50,
            r: 20,
            b: 50,
            t: 50,
            pad: 4
        }
    };
    
    Plotly.newPlot(container, [trace], layout, {responsive: true});
}

/**
 * Tworzy wykres wyników wg symboli
 */
function createSymbolPerformanceChart(container, data) {
    var barColors = data.pnl.map(value => value >= 0 ? '#28a745' : '#dc3545');
    
    var trace = {
        x: data.symbols,
        y: data.pnl,
        type: 'bar',
        marker: {
            color: barColors
        }
    };
    
    var layout = {
        title: 'Wyniki wg Instrumentów',
        xaxis: {
            title: 'Symbol'
        },
        yaxis: {
            title: 'Zysk/Strata'
        },
        autosize: true,
        margin: {
            l: 50,
            r: 20,
            b: 50,
            t: 50,
            pad: 4
        }
    };
    
    Plotly.newPlot(container, [trace], layout, {responsive: true});
} 