# Lokales Workflow-Testing mit act

## Installation

```bash
brew install act
```

## Workflows lokal testen

### Kompletten CI-Workflow ausführen:
```bash
act push
```

### Einzelnen Job ausführen:
```bash
act push -j lint
act push -j build
act push -j owasp-dependency-check
```

### Nur prüfen (Dry-run):
```bash
act push -n
```

### Mit Debugging:
```bash
act push -v
```

## Hinweise

- act verwendet Docker-Container, um GitHub Actions lokal zu emulieren
- Die `.actrc` Datei enthält die Standard-Konfiguration
- Secrets werden aus `.github/workflows/.act-secrets` geladen
- Der komplette Build dauert je nach Maschine 5-15 Minuten
