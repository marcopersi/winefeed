# ToS-Klausel: Anti-Scraping / Anti-Training (Entwurf — 6.1.2)

> **Status: ENTWURF, nicht rechtsverbindlich, keine Rechtsberatung.**
> Dieses Dokument ist der erste Entwurf der ToS-Klausel aus Schritt 6.1.2
> von `docs/data-api-security-plan.md`. Es ist die Arbeitsgrundlage für die
> Rechtsberatungs-Review (6.1.4, Owner: Nutzer) — die finale, rechtsverbindliche
> Fassung entsteht erst NACH dieser Review und wird gemäss 6.1.5 versioniert
> publiziert. Autor: Claude. Jurisdiktion: CH (bei EU-Nutzern ggf. zusätzlich
> EU-Recht — in 6.1.4 zu klären). Version 0.1, Stand 2026-11-14.

---

## Klausel — Nutzung der Daten; Verbot automatisierten Zugriffs und des Trainings von KI-/ML-Modellen

### 1. Geltungsbereich und Begriffsbestimmungen

(1) Diese Klausel gilt für jede Nutzung der Plattform und der über sie
zugänglich gemachten Daten (nachfolgend «Daten»), unabhängig davon, ob der
Zugriff über die Web-Oberfläche, eine API, einen mobilen Client oder einen
sonstigen technischen Weg erfolgt.

(2) «Automatisierter Zugriff» bzw. «Scraping» bezeichnet jedes programmatische,
maschinelle oder automatisierte Auslesen, Abrufen, Herunterladen, Kopieren,
Sammeln, Spiegeln, Archivieren oder sonstige systematische Extrahieren der Daten
— insbesondere durch Skripte, Bots, Crawler, Spider, Headless-Browser,
Browser-Automation, die Umgehung technischer Schutzmassnahmen oder die
systematische Enumeration von Kennungen — unabhängig vom eingesetzten Mittel
und unabhängig davon, ob ein gültiges Benutzerkonto besteht.

(3) «Training von KI-/ML-Modellen» bezeichnet jede Verwendung der Daten für das
Trainieren, Feintunen (Fine-Tuning), Evaluieren, Retrieval-Augmentieren oder
sonstige Nutzen der Daten im Zusammenhang mit maschinellen Lernmodellen,
künstlicher Intelligenz, generativen Modellen oder ähnlichen Systemen.

### 2. Zulässige Nutzung

(1) Die Daten dürfen ausschliesslich für die bestimmungsgemässe, persönliche
Nutzung der Plattform in dem Umfang verwendet werden, den die jeweils gültige
Zugriffsstufe (anonym / registriert / kostenpflichtig) ausdrücklich vorsieht.

(2) Jede darüber hinausgehende Vervielfältigung, Verbreitung, Weiterveräusserung,
öffentliche Wiedergabe oder Weiterverwendung der Daten — auch in aufbereiteter,
aggregierter oder abgeleiteter Form — bedarf der vorherigen schriftlichen
Zustimmung des Betreibers.

### 3. Verbot automatisierten Zugriffs (Scraping)

(1) Automatisierter Zugriff bzw. Scraping im Sinne von Ziffer 1(2) ist
untersagt. Untersagt ist insbesondere das systematische oder vollständige
Durchlaufen der Datenbestände (Enumeration), auch bei Einhaltung etwaiger
Zugriffsbeschränkungen, sowie das Umgehen, Neutralisieren oder Unterlaufen
technischer Schutzmassnahmen (vgl. Ziffer 5).

(2) Das Verbot gilt unabhängig davon, ob der Zugriff über ein eigenes oder ein
fremdes Benutzerkonto, über wechselnde IP-Adressen, über Dritte oder über
mehrere Konten erfolgt.

### 4. Verbot der Trainingsnutzung (inkl. abgeleiteter/aggregierter Daten)

(1) Jede Nutzung der Daten — einschliesslich daraus abgeleiteter, aggregierter,
transformierter, angereicherter oder aufbereiteter Daten — für das Training von
KI-/ML-Modellen im Sinne von Ziffer 1(3) ist ausdrücklich und vollständig
untersagt. Dieses Verbot erstreckt sich ausdrücklich auch auf bereits
aggregierte oder abgeleitete Produkte (Indizes, Bänder, Prognosen, geglättete
Zeitreihen), die über die Plattform zugänglich gemacht werden.

(2) Das Verbot gilt unabhängig davon, ob die Trainingsnutzung gewerblich oder
nicht gewerblich, entgeltlich oder unentgeltlich erfolgt, und unabhängig davon,
ob die Daten hierfür zunächst weiterverarbeitet, anonymisiert oder
pseudonymisiert wurden.

(3) Diese Ziffer begründet eine eigenständige, von Ziffer 3 unabhängige
Verpflichtung. Ein Zugriff, der nicht «automatisiert» im Sinne von Ziffer 1(2)
ist, kann gleichwohl gegen das Trainingsnutzungsverbot dieser Ziffer verstossen.

### 5. Umgehungsverbot

(1) Es ist untersagt, technische Schutzmassnahmen der Plattform — insbesondere
Zugangsstufen und Authentifizierung, Zugriffsbeschränkungen und Rate-Limits,
die Aggregation oder Formung der ausgelieferten Daten, Erkennungs- und
Überwachungsmechanismen sowie allfällige Zugriffsschranken am Netzwerkrand — zu
umgehen, zu neutralisieren, zu deaktivieren oder zu unterlaufen.

(2) Untersagt ist auch der Versuch einer solchen Umgehung sowie die Bereitstellung
oder der Einsatz von Werkzeugen, deren wesentlicher Zweck die Umgehung dieser
Massnahmen ist.

### 6. Vorbehalt des Datenbankschutzrechts

(1) Die Datenbank der Plattform — d.h. die systematisch oder methodisch
angeordnete, einzeln zugängliche Sammlung der zusammengetragenen und
strukturierten Auktions- und Preisinformationen — stellt das Ergebnis einer in
ihrer Beschaffung, Überprüfung, Bereinigung, Aufbereitung und Darstellung
wesentlichen Investition dar (der Nachweis hierzu wird in der
Investitions-Dokumentation gemäss Schritt 6.1.1 geführt).

(2) Der Betreiber behält sich ausdrücklich sämtliche Rechte an dieser Datenbank
vor, einschliesslich des Rechts des Datenbankherstellers (Schutzrecht sui
generis) nach schweizerischem und — soweit anwendbar — europäischem Recht
(Richtlinie 96/9/EG), insbesondere das Recht, die Entnahme und/oder
Weiterverwendung der Gesamtheit oder eines in qualitativer oder quantitativer
Hinsicht wesentlichen Teils des Datenbankinhalts zu untersagen.

(3) Ziffern 3 und 4 dieses Abschnitts gelten ausdrücklich auch als Ausübung und
Sicherung dieses Vorbehalts.

### 7. Rechtsfolgen bei Verstoss

(1) Bei Verstoss gegen diese Klausel — insbesondere gegen Ziffern 3, 4 oder 5 —
ist der Betreiber berechtigt, das Benutzerkonto unverzüglich zu sperren und den
Zugriff auf die Plattform dauerhaft zu entziehen, ohne dass daraus ein Anspruch
auf Erstattung bereits geleisteter Entgelte entsteht.

(2) Der Betreiber behält sich ausdrücklich sämtliche weiteren Rechte und
Rechtsbehelfe vor, insbesondere auf Unterlassung, Beseitigung, Herausgabe,
Auskunft sowie auf Schadensersatz und Ersatz der für die Feststellung und
Durchsetzung erforderlichen Aufwendungen (einschliesslich angemessener Kosten
der Rechtsverfolgung).

### 8. Anwendbares Recht und Gerichtsstand

(1) Auf diese Klausel und ihre Verletzung ist — vorbehaltlich zwingender
Bestimmungen — materielles Schweizer Recht anwendbar.

(2) Ausschliesslicher Gerichtsstand ist, soweit gesetzlich zulässig, der Sitz
des Betreibers. Für Nutzer mit Wohnsitz ausserhalb der Schweiz bleibt die
Zuständigkeit der gesetzlichen Gerichtsstände vorbehalten.

---

## Anhang — Vollständigkeits-Check gegen das 6.1.2-Abnahmekriterium

| Gefordertes Element (AC 6.1.2) | Erfüllt durch |
|---|---|
| Definition «automatisierter Zugriff»/«Scraping» | Ziffer 1(2) |
| Separates, explizites Trainingsnutzungsverbot (inkl. abgeleiteter/aggregierter Daten) | Ziffer 4 (eigenständig von Ziffer 3, Abs. 3) |
| Anti-Umgehungs-Klausel (technische Schutzmassnahmen Stufe 1–5) | Ziffer 5 |
| Expliziter Vorbehalt des Datenbankschutzrechts (sui generis) | Ziffer 6 |
| Rechtsfolgen bei Verstoss (Sperre, Schadensersatzvorbehalt) | Ziffer 7 |
| Anwendbares Recht / Gerichtsstand | Ziffer 8 |
| Als «nicht rechtsverbindlich, Entwurf für Rechtsberatung» markiert | Status-Banner oben |

> Offene Punkte für die Rechtsberatung (6.1.4): Jurisdiktion für EU-Nutzer,
> konkreter Gerichtsstand/Sitz, Abstimmung der Rechtsfolgen mit
> anwendbarem Verbraucherrecht, Verhältnis zu `robots.txt`/`llms.txt`
> (6.3) und zum DMCA-/UWG-Durchsetzungsprozess (6.4).
