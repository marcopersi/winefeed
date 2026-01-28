#!/bin/bash

echo "🍷 Wine Feed - Supabase Setup"
echo "=============================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker ist nicht verfügbar. Bitte starten Sie Docker Desktop."
    exit 1
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️ Virtuelles Environment nicht aktiviert."
    echo "Führen Sie 'source venv/bin/activate' aus."
    exit 1
fi

echo "✅ Docker läuft"
echo "✅ Virtual Environment aktiviert"

# Start Supabase
echo ""
echo "🚀 Starte Supabase..."
supabase start

# Check if Supabase started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Supabase erfolgreich gestartet!"
    echo ""
    echo "📋 Nächste Schritte:"
    echo "1. Aktualisieren Sie die .env Datei mit den Supabase-Credentials"
    echo "2. Führen Sie 'python wine_manager.py' aus, um Beispieldaten zu laden"
    echo "3. Öffnen Sie http://localhost:54323 für das Supabase Studio"
    echo ""
else
    echo "❌ Fehler beim Starten von Supabase"
    exit 1
fi
