# Pre-commit Hook

Der Pre-commit Hook läuft automatisch vor jedem Commit und führt folgende Checks durch:

## Checks

1. **Code Formatting & Linting**
   - **Prettier** - Formatiert JavaScript, JSON, Markdown, YAML
   - **Pylint** - Lintet Python-Dateien in priceData/
   - **ESLint** - Lintet und fixiert JavaScript in price-service-ui/
2. **Gradle Builds** - Baut alle Gradle-Projekte (PersiCommons, VinoDomain, priceservice, VinoImporter)
3. **NPM Build** - Baut price-service-ui
4. **Markdown Lint** - Prüft README.md

## Installation

Der Hook ist bereits installiert in `.git/hooks/pre-commit`.

## Hook temporär umgehen

Falls der Hook bei einem Commit übersprungen werden soll:

```bash
git commit --no-verify -m "message"
```

## Hook testen

```bash
.git/hooks/pre-commit
```
