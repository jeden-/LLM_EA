#!/usr/bin/env python3
"""
Skrypt do automatycznego generowania dokumentacji Sphinx dla systemu LLM Trading.
Skrypt wykona następujące kroki:
1. Wygeneruje dokumentację API na podstawie docstringów w kodzie
2. Wygeneruje dokumentację HTML
3. Opcjonalnie wygeneruje dokumentację PDF
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
import importlib.util
import site


def parse_arguments():
    """Parsuje argumenty wiersza poleceń."""
    parser = argparse.ArgumentParser(description="Generator dokumentacji Sphinx dla LLM Trading System")
    parser.add_argument("--pdf", action="store_true", help="Generuj również dokumentację PDF")
    parser.add_argument("--clean", action="store_true", help="Wyczyść istniejącą dokumentację przed generowaniem")
    parser.add_argument("--open", action="store_true", help="Otwórz wygenerowaną dokumentację HTML w przeglądarce")
    return parser.parse_args()


def check_requirements():
    """Sprawdza, czy wymagane narzędzia są zainstalowane."""
    try:
        import sphinx
        print(f"Znaleziono Sphinx w wersji {sphinx.__version__}")
    except ImportError:
        print("ERROR: Sphinx nie jest zainstalowany. Zainstaluj go używając: pip install sphinx sphinx-rtd-theme")
        return False
    
    # Znajdź ścieżkę do sphinx-build
    sphinx_build_path = None
    
    # Opcja 1: Sprawdź w katalogu skryptów Pythona
    script_dirs = []
    
    # Dodaj katalog skryptów użytkownika
    user_scripts = os.path.join(site.USER_BASE, "Scripts")
    if os.path.exists(user_scripts):
        script_dirs.append(user_scripts)
    
    # Dodaj ścieżkę w appdata dla Windowsa
    appdata_scripts = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", "Python39", "Scripts")
    if os.path.exists(appdata_scripts):
        script_dirs.append(appdata_scripts)
    
    # Dodaj standardowe ścieżki skryptów Pythona
    for path in site.getsitepackages():
        scripts_path = os.path.join(os.path.dirname(path), "Scripts")
        if os.path.exists(scripts_path):
            script_dirs.append(scripts_path)
    
    # Szukaj sphinx-build.exe w znalezionych katalogach
    for dir_path in script_dirs:
        sphinx_build = os.path.join(dir_path, "sphinx-build.exe")
        if os.path.exists(sphinx_build):
            sphinx_build_path = sphinx_build
            break
        
        sphinx_build = os.path.join(dir_path, "sphinx-build")
        if os.path.exists(sphinx_build):
            sphinx_build_path = sphinx_build
            break
    
    if sphinx_build_path:
        print(f"Znaleziono sphinx-build: {sphinx_build_path}")
        # Dodaj do os.environ['PATH'] aby inne funkcje mogły go używać
        os.environ['PATH'] = os.path.dirname(sphinx_build_path) + os.pathsep + os.environ.get('PATH', '')
        return True
    else:
        print("ERROR: sphinx-build nie został znaleziony. Sprawdź czy Sphinx jest poprawnie zainstalowany.")
        return False


def clean_docs(sphinx_dir):
    """Czyści istniejącą dokumentację."""
    build_dir = os.path.join(sphinx_dir, "_build")
    api_dir = os.path.join(sphinx_dir, "api")
    
    if os.path.exists(build_dir):
        print(f"Czyszczenie katalogu: {build_dir}")
        shutil.rmtree(build_dir)
    
    if os.path.exists(api_dir):
        print(f"Czyszczenie katalogu: {api_dir}")
        shutil.rmtree(api_dir)
    
    print("Istniejąca dokumentacja została wyczyszczona.")


def generate_api_docs(sphinx_dir, project_dir):
    """Generuje dokumentację API na podstawie docstringów."""
    print("Generowanie dokumentacji API...")
    api_dir = os.path.join(sphinx_dir, "api")
    
    os.makedirs(api_dir, exist_ok=True)
    
    # Znajdź sphinx-apidoc w tym samym katalogu co sphinx-build
    sphinx_apidoc_exe = None
    for path in os.environ['PATH'].split(os.pathsep):
        sphinx_apidoc_path = os.path.join(path, "sphinx-apidoc.exe")
        if os.path.exists(sphinx_apidoc_path):
            sphinx_apidoc_exe = sphinx_apidoc_path
            break
        
        sphinx_apidoc_path = os.path.join(path, "sphinx-apidoc")
        if os.path.exists(sphinx_apidoc_path):
            sphinx_apidoc_exe = sphinx_apidoc_path
            break
    
    # Jeśli nie znaleziono, użyj nazwy polecenia (może działać jeśli jest w PATH)
    if not sphinx_apidoc_exe:
        sphinx_apidoc_exe = "sphinx-apidoc"
    
    cmd = [
        sphinx_apidoc_exe,
        "-o", api_dir,
        project_dir,
        os.path.join(project_dir, "tests"),
        os.path.join(project_dir, "scripts"),
        os.path.join(project_dir, "*/__pycache__"),
        "-e",  # Osobny plik dla każdego modułu
        "-M",  # Umieść nazwę modułu przed nazwą funkcji/klasy
    ]
    
    print(f"Wykonywanie: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("Dokumentacja API została wygenerowana pomyślnie.")
    except subprocess.SubprocessError as e:
        print(f"ERROR: Nie udało się wygenerować dokumentacji API: {e}")
        return False
    
    return True


def generate_html_docs(sphinx_dir):
    """Generuje dokumentację HTML."""
    print("Generowanie dokumentacji HTML...")
    
    os.chdir(sphinx_dir)
    
    if os.name == 'nt':  # Windows
        cmd = ["make.bat", "html"]
    else:  # Linux/macOS
        cmd = ["make", "html"]
    
    print(f"Wykonywanie: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("Dokumentacja HTML została wygenerowana pomyślnie.")
    except subprocess.SubprocessError as e:
        print(f"ERROR: Nie udało się wygenerować dokumentacji HTML: {e}")
        return False
    
    return True


def generate_pdf_docs(sphinx_dir):
    """Generuje dokumentację PDF."""
    print("Generowanie dokumentacji PDF...")
    
    os.chdir(sphinx_dir)
    
    if os.name == 'nt':  # Windows
        cmd = ["make.bat", "latexpdf"]
    else:  # Linux/macOS
        cmd = ["make", "latexpdf"]
    
    print(f"Wykonywanie: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("Dokumentacja PDF została wygenerowana pomyślnie.")
    except subprocess.SubprocessError as e:
        print(f"WARNING: Nie udało się wygenerować dokumentacji PDF: {e}")
        print("         Upewnij się, że LaTeX jest zainstalowany w systemie.")
        return False
    
    return True


def open_html_docs(sphinx_dir):
    """Otwiera wygenerowaną dokumentację HTML w przeglądarce."""
    html_index = os.path.join(sphinx_dir, "_build", "html", "index.html")
    
    if not os.path.exists(html_index):
        print(f"ERROR: Plik {html_index} nie istnieje.")
        return False
    
    print(f"Otwieranie dokumentacji HTML: {html_index}")
    
    if os.name == 'nt':  # Windows
        os.startfile(html_index)
    elif os.name == 'posix':  # Linux/macOS
        if sys.platform == 'darwin':  # macOS
            subprocess.run(["open", html_index])
        else:  # Linux
            subprocess.run(["xdg-open", html_index])
    
    return True


def main():
    """Główna funkcja skryptu."""
    args = parse_arguments()
    
    # Znajdź ścieżki
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    sphinx_dir = os.path.join(script_dir, "sphinx")
    
    print(f"Katalog projektu: {project_dir}")
    print(f"Katalog Sphinx: {sphinx_dir}")
    
    # Sprawdź wymagania
    if not check_requirements():
        return 1
    
    # Wyczyść istniejącą dokumentację jeśli potrzeba
    if args.clean:
        clean_docs(sphinx_dir)
    
    # Generuj dokumentację API
    if not generate_api_docs(sphinx_dir, project_dir):
        return 1
    
    # Generuj dokumentację HTML
    if not generate_html_docs(sphinx_dir):
        return 1
    
    # Generuj dokumentację PDF jeśli potrzeba
    if args.pdf:
        generate_pdf_docs(sphinx_dir)
    
    # Otwórz dokumentację HTML jeśli potrzeba
    if args.open:
        open_html_docs(sphinx_dir)
    
    print("Generowanie dokumentacji zakończone pomyślnie.")
    print(f"Dokumentacja HTML dostępna w: {os.path.join(sphinx_dir, '_build', 'html')}")
    
    if args.pdf:
        pdf_path = os.path.join(sphinx_dir, "_build", "latex")
        if os.path.exists(pdf_path):
            print(f"Dokumentacja PDF dostępna w: {pdf_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 