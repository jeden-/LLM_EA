"""
Macierzyste szablony HTML do testów komponentów UI.

Ten plik zawiera moki szablonów HTML używane w testach jednostkowych,
aby uniknąć problemów z rzeczywistymi szablonami.
"""

# Mockowy szablon base.html
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}System Handlowy LLM{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('home') }}">LLM EA Dashboard</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('home') }}">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('statistics') }}">Statystyki</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('market_analysis') }}">Analiza Rynku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('trade_ideas') }}">Pomysły Handlowe</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('account_status') }}">Status Konta</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <footer class="bg-dark text-light py-3 mt-5">
        <div class="container text-center">
            <p>&copy; 2024 System Handlowy LLM. Wszelkie prawa zastrzeżone.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
""" 