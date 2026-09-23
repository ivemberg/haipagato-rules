# Fonti delle regole

Ogni valore in `rules.json` deve avere qui una riga con URL, citazione testuale e data di consultazione.
Se una fonte ufficiale non conferma un valore, resta `"verified": false` e la riga spiega perché.

---

## Area C — giorni e orari di attivazione (`verified: true`)

**Valore:** lunedì–venerdì, 07:30–19:30, festivi esclusi. Non attiva sabato e domenica.

Tre fonti ufficiali indipendenti, consultate il **2026-09-22**:

1. [comune.milano.it — Area C](https://www.comune.milano.it/aree-tematiche/mobilita/area-c) (agg. 22/06/2026)
   > «Area C è attiva tutto l'anno dal lunedì al venerdì, dalle 7:30 alle 19:30 (festivi esclusi).»

2. [comune.milano.it — Quando è attiva Area C? (KA-01151)](https://servizicrm.comune.milano.it/centro-supporto/KA-01151/Orari-di-attivazione-Area-C) (agg. 17/10/2025)
   > «Area C è attiva nei giorni feriali con i seguenti orari: Lunedì/venerdì: 7:30-19:30. Area C non è attiva Sabato, Domenica e nei giorni festivi.»

3. [areac.atm-mi.it — Novità Area C](https://areac.atm-mi.it/Areac/IWeb/Novita.aspx)
   > «Area C è attiva dal lunedì al venerdì, dalle 7:30 alle 19:30.»

Fonte normativa, [Determina Dirigenziale n. 1856 del 13/03/2026 — Disciplinare dei sistemi di pagamento](https://www.comune.milano.it/documents/d/guest/determina-dirigenziale-n-1856-del-13-03-2026-pdf):
> «il divieto di accesso all'interno della ZTL Cerchia dei Bastioni – "Area C", dalle ore 07.30 alle ore 19.30 nei giorni feriali»

### Nota 1 — «giorni feriali» vs «lunedì–venerdì»

La determina usa «giorni feriali», che in senso stretto include il sabato. Tutte le fonti operative
(comune.milano.it, CRM, ATM) dicono invece esplicitamente lunedì–venerdì e «non attiva Sabato».
Vale la lettura operativa: **sabato escluso**.

### Nota 2 — l'estensione al weekend NON è in vigore

`PLAN.md` segnalava fonti che parlano di attivazione nel weekend. Verificato: **falso a oggi.**

- L'origine è una dichiarazione del sindaco Sala del giugno 2025 ripresa da
  [L'Automobile / ACI, 24/06/2025](https://www.lautomobile.aci.it/attualita/area-c-milano-da-gennaio-2026-sara-attiva-anche-nei-weekend/),
  che annunciava l'attivazione 7 giorni su 7 dal 1° gennaio 2026. L'articolo **non cita alcun atto amministrativo**.
- Numerosi siti secondari (blog assicurativi, portali auto) hanno ripubblicato l'annuncio come se fosse già legge.
  Anche i riassunti automatici dei motori di ricerca lo danno per vigente. **Non lo è.**
- La pagina ufficiale aggiornata al **22/06/2026** — cioè sei mesi *dopo* la presunta decorrenza — dice ancora lunedì–venerdì.
- Il Disciplinare del **13/03/2026** dice ancora «giorni feriali».

**Conseguenza per l'app:** non notificare mai sabato e domenica. Ma questa è la regola più a rischio
di cambiare: è il motivo principale per cui serve l'aggiornamento remoto di `rules.json` (M3).

---

## Area C — festivi (`verified: false`) ⚠️

**Nessuna fonte ufficiale di Area C elenca i giorni festivi.** Tutte dicono solo «festivi esclusi».
Il Disciplinare del 13/03/2026 non contiene la parola «festivi» né alcun calendario di sospensioni.

L'elenco in `rules.json` è **ricostruito**, non verificato:
festività civili italiane (L. 260/1963) + Sant'Ambrogio (7 dicembre), patrono di Milano.

Sant'Ambrogio come giorno di sospensione è confermato solo da fonti secondarie
(es. [MilanoToday](https://www.milanotoday.it/cronaca/areac-chiusa-7-dicembre-2012.html)), mai da comune.milano.it.

### Domanda aperta: sospensione estiva di agosto

Fonti secondarie riferiscono che Area C viene sospesa per un periodo continuativo in agosto,
deciso anno per anno con ordinanza. **Non trovata conferma ufficiale.** Se vero, e se l'app non lo sa,
genererebbe notifiche false per due settimane l'anno.

**Chiuso come rischio accettato** (M0, 2026-09-22). Non blocca il rilascio: l'errore cade dal lato sicuro,
un promemoria di troppo e mai una multa. Se un giorno si vuole chiudere davvero, i percorsi sono l'Albo Pretorio
del Comune o una mail a `MTA.UfficioAreaC@comune.milano.it`.

Lo schema ha il campo `zones[].suspensions` per accoglierla, oggi con `periods` vuoto e `verified: false`.
Vuoto significa "nessuna sospensione", non "non so": finché non è confermata, l'app continua a ricordare il
pagamento anche ad agosto. Un promemoria di troppo infastidisce, uno in meno costa una multa.

---

## Area C — scadenze di pagamento (`verified: true`)

Fonte primaria: [Determina Dirigenziale n. 1856 del 13/03/2026, «Disciplinare dei sistemi di pagamento»](https://www.comune.milano.it/documents/d/guest/determina-dirigenziale-n-1856-del-13-03-2026-pdf), consultata il 2026-09-22.

| Caso | Importo | Termine |
|---|---|---|
| Veicolo ordinario | 7,50 € | entro le 24:00 del **giorno successivo** all'ingresso |
| Residente/equiparato (dal 51° accesso) | 3,00 € | entro le 24:00 del giorno successivo |
| Veicolo di servizio | 4,50 € | entro le 24:00 del giorno successivo |
| **Autorimessa convenzionata** | 4,50 € | entro le 24:00 del **giorno stesso** |
| Pagamento differito (dimenticanza) | 22,50 € | entro le 24:00 del **settimo giorno** successivo |

> «Pagamento differito entro 7 giorni da 22,50€ per accessi non regolarizzati entro le ore 24.00
> del giorno successivo al transito ed entro il nuovo termine delle ore 24.00 del settimo giorno
> successivo a quello in cui è avvenuto l'accesso»

Conferma operativa su [FAQ ATM](https://areac.atm-mi.it/Areac/IWeb/FAQ2.aspx):
> «L'attivazione va effettuata nella giornata in cui avviene l'accesso [...] o, al massimo, entro le ore 24.00
> del giorno successivo. Fanno eccezione i tagliandi a tariffa agevolata delle autorimesse convenzionate
> e i ticket "NCC-Gita scolastica", che devono essere obbligatoriamente attivati entro la mezzanotte del giorno stesso.»

Ticket differito, sempre FAQ ATM:
> «puoi regolarizzare l'accesso ed effettuare il pagamento entro 7 giorni dall'ingresso acquistando e attivando
> un ticket da 22.5 €. Questo ticket può essere attivato solo dalla tua pagina personale MyAreaC, utilizzando
> la funzione "Entro 7 giorni", dopo aver registrato la targa del veicolo nella pagina "Gestione veicoli".»

### Nota — la pagina CRM del Comune è sbagliata

[KA-00945](https://servizicrm.comune.milano.it/centro-supporto/KA-00945/Tempistiche-attivazione-ticket-Area-C) scrive:
> «i ticket acquistati nelle autorimesse devono essere attivati lo stesso giorno in cui avviene l'accesso nella ztl
> o, al massimo, entro le ore 24 del giorno successivo»

Attribuisce alle autorimesse la proroga al giorno dopo. È l'**opposto** di quanto dicono il Disciplinare e le FAQ ATM,
dove le autorimesse sono l'eccezione *restrittiva*. Vale il Disciplinare.
È esattamente l'ambiguità annotata in `PLAN.md`.

### Altri dati utili

- Validità del ticket: giornaliera, copre tutti gli ingressi dello stesso veicolo nella stessa giornata
  «dall'orario del primo accesso fino alle 19.30» (FAQ ATM).
- Non è valida l'attivazione nei giorni *precedenti* al transito, salvo credito precaricato su targa registrata a MyAreaC.

---

## Area C — esenzioni (`verified: true`)

Fonte: Disciplinare DD 1856/2026, **Capitolo 6 — Esenzioni dal pagamento della somma di accesso**.

> «Sono esentati dal pagamento della somma di accesso e transito, **senza alcun adempimento**, le seguenti
> categorie di veicoli in quanto direttamente riconoscibili tramite i dispositivi automatici di rilevazione degli accessi:
> veicoli elettrici; autoveicoli, classe M1, ibridi con contributo emissivo di CO2 ≤ 100 g/km;
> motoveicoli, ciclomotori e velocipedi; veicoli di proprietà alle Forze Armate, alle Forze di Polizia [...]»

Per l'onboarding contano solo le tre categorie automatiche: elettrico, ibrido M1 con CO2 ≤ 100 g/km, moto/ciclomotore.
Il valore di CO2 è al campo **V.7** della carta di circolazione (confermato dal Disciplinare).

Categorie che richiedono comunicazione della targa al Comune (contrassegno disabili, forze dell'ordine, operatori
socio-sanitari): non sono un interruttore di onboarding, ma l'utente che le ha può comunque volere il promemoria spento.

Tariffe ridotte (non esenzioni): residenti 50 ingressi gratuiti/anno poi 3 €, veicoli di servizio 4,50 €,
autorimesse convenzionate 4,50 €.

Non esenti, contrariamente a quanto si potrebbe pensare: **auto d'epoca** (FAQ ATM, «per le auto d'epoca non sono
previste esenzioni dal pagamento») e veicoli ibridi non-M1 (M2, M3, N1-N3), a pagamento dal 1° ottobre 2023.

---

## Area C — URL ufficiali (`verified: true`)

Raccolti dai link in uscita della pagina ufficiale comune.milano.it/aree-tematiche/mobilita/area-c, 2026-09-22.

- Acquisto ticket: `https://areac.atm-mi.it/Areac/IWeb/Acquisto.aspx`
- Area personale MyAreaC (necessaria per il differito a 7 giorni): `https://areac.atm-mi.it/Areac/IWeb/MyAreaC_HomePage.aspx`
- Attivazione ticket: `https://areac.atm-mi.it/Areac/IWeb/Attivazione.aspx`
- FAQ: `https://areac.atm-mi.it/Areac/IWeb/FAQ2.aspx`
- Verifica classe veicolo: `https://areac.atm-mi.it/Areac/iweb/CercaClasse.aspx`
- Assistenza: `MTA.UfficioAreaC@comune.milano.it`

Il dominio operativo è `areac.atm-mi.it` (ATM gestisce per conto del Comune), **non** `comune.milano.it`.

---

## Area C — confine e varchi (`verified: true`)

Consultati il **2026-09-22** sul portale open data del Comune, `dati.comune.milano.it`.

### Perimetro

[`ds51_trafficotrasporti_aree_pedonali_ztl`](https://dati.comune.milano.it/dataset/ds51_trafficotrasporti_aree_pedonali_ztl)
— "Aree pedonali e ZTL", **CC BY**, aggiornato 08/05/2026.

217 MultiPolygon, dei quali **uno solo** ha `tipo: AREA_C` (`id_amat` 276, `nome` "AreaC", `val_inizio` 2000-01-01,
`val_fine` 2050-01-01). Un anello, nessun buco, 1120 vertici, CRS84/WGS84.
Bbox `9.164455, 45.452078` – `9.206617, 45.480865`.

`PLAN.md` ipotizzava di dover ricostruire il confine dai varchi o da OSM e marcarlo `verified: false`.
**Non serve:** il poligono ufficiale esiste ed è pubblicato. Estratto in `rules/area-c.geojson` con coordinate
arrotondate a 6 decimali (~0,1 m).

### Varchi

[`ds82_infogeo_varchi_elettronici_localizzazione_`](https://dati.comune.milano.it/dataset/ds82_infogeo_varchi_elettronici_localizzazione_)
— "Varchi Area C", **CC BY**, aggiornato 16/09/2026. 42 punti con `id_amat` e `label`.
Estratti in `rules/area-c-varchi.geojson`.

⚠️ **42 varchi nel dataset, 43 secondo la pagina del Comune**
([KA-01472](https://servizicrm.comune.milano.it/centro-supporto/KA-01472/Confini-e-varchi-di-Area-C):
«È delimitata da 43 varchi elettronici»). Non risolta e non inventata. Non è bloccante: i varchi non rilevano
nulla, servono solo al nome della notifica, quindi un varco mancante produce al più una notifica generica.

### I varchi non possono confermare un transito

Misurato: ogni varco dista dal confine **1,6–39,5 m**, mediana **14,1 m**, e 40 su 42 cadono dentro il poligono.
Le telecamere stanno appena all'interno del perimetro.

Questo li rende inutilizzabili come criterio di rilevamento: **stanno sulla Cerchia dei Bastioni**, cioè sulla
strada che si percorre senza entrare. Un percorso simulato lungo la circonvallazione ne sfiora **8** senza mai
entrare in zona. Usarli come conferma significherebbe fabbricare otto transiti inesistenti.
Da qui `geometry.gatesUse: "labelOnly"` in `rules.json`.

### Banda di isteresi

Il confine coincide con la carreggiata dei Bastioni e l'errore GPS urbano è dello stesso ordine della larghezza
della strada, quindi un punto-in-poligono nudo genera falsi positivi a ogni giro. `geometry.innerBufferM` vale
**50 m**: un punto è `DENTRO` solo se supera quella distanza dal bordo. Semantica completa e macchina a stati
in `PLAN.md`, sezione "Rilevamento del transito".

Il valore è una stima prudente da tarare sulla prova su strada di M2, non un dato di fonte.

### Verifiche eseguite

Riproducibili con `tools/build_areac.py` (solo libreria standard, scarica i dataset e rigenera i GeoJSON).
Se una verifica fallisce lo script non scrive nulla.

**Negativi — non deve nascere alcun transito:**

| Controllo | Esito |
|---|---|
| Poligono chiuso, anello singolo, nessun buco | 1120 vertici |
| Varchi estratti | 42 punti |
| Tutti i varchi entro 40 m dal confine | max 39,5 m, mediana 14,1 m |
| Duomo `DENTRO`, Stazione Centrale `FUORI` | ok |
| Giro dei Bastioni: sfiora ≥ 3 varchi | **8 varchi** |
| Giro dei Bastioni | nessun transito |
| Giro dei Bastioni con GPS 25 m spinto verso l'interno | nessun transito (fermo 4 s) |
| Sosta a 6 m dal confine per 10 minuti | nessun transito (sotto `probableMinDepthM`) |
| Passaggio in banda a 30 m senza fermarsi | nessun transito (sotto `probableMinDwellS`) |

**Positivi — il transito deve nascere:**

| Controllo | Esito |
|---|---|
| Ingresso da nord fino al Duomo | **confermato** |
| Orario interpolato fra ultimo `FUORI` e primo punto dentro | t=104,9 s in [104, 106] |
| Entra e parcheggia a 30 m dal confine, 5 minuti | **probabile** (31 m, fermo 306 s) |
| Ingresso reale a 70 m con GPS 25 m verso l'esterno | almeno probabile (letta 50 m contro 75 m reali) |

### Perché `probableMinDwellS` conta il tempo da fermo

Scritto con la definizione ovvia — tempo totale trascorso dentro il poligono — **il test fallisce**. Un percorso
lungo i Bastioni con errore GPS di 25 m sbilanciato verso l'interno resta in `BANDA` a 25 m, sopra i 15 m di
`probableMinDepthM`, per oltre 500 s: produrrebbe un "probabile" fasullo a ogni giro di circonvallazione.

Contando invece la permanenza **da fermo** in coda al viaggio (campioni finali entro `stationaryRadiusM` = 25 m
dall'ultimo) i due casi si separano puliti: chi percorre la Cerchia non si ferma mai (4 s), chi parcheggia sì (306 s).

### monitorRegion

Un solo cerchio: centro `45.466471, 9.185536`, raggio **2789 m** — cerchio circoscritto al bbox del poligono
più 500 m di margine. Entro il limite di 20 regioni di `CLMonitor` con ampio spazio per le free flow.

### Licenza e attribuzione

Entrambi i dataset sono **CC BY**. `rules/` viene ridistribuito su GitHub Pages, quindi l'attribuzione è
obbligatoria in due punti: nei file (campo `attribution` in testa a ogni GeoJSON) e nella schermata Info
dell'app, accanto a quella OpenStreetMap. Formula usata:

> Contiene dati del Comune di Milano — dati.comune.milano.it, licenza CC BY 4.0

---

## Free flow Pedemontana — A36, A59, A60 (`verified: true`)

Consultate il **2026-09-22**. Il sito ufficiale del concessionario è `pedemontana.com`
(portale operativo `apl.pedemontana.com`). `autostradapedemontanalombarda.it` non risponde.

### Gestore e rete

Autostrada Pedemontana Lombarda S.p.A. (P.IVA 08558150150, soggetta a direzione e coordinamento di
Regione Lombardia) gestisce tutte e tre le tratte, elencate sotto «La rete in esercizio» del proprio sito:

- **A36 Pedemontana** — [Tratta A](https://www.pedemontana.com/it/la-rete-esercizio/a36/tratta-a), Tratta B1
- **A59 Tangenziale di Como** — https://www.pedemontana.com/it/la-rete-esercizio/a59-tangenziale-di-como
- **A60 Tangenziale di Varese** — https://www.pedemontana.com/it/la-rete-esercizio/a60-tangenziale-di-varese

Free Flow® su tutte: nessun casello, nessuna barriera, rilevamento targa da portali.
[Come funziona il Free Flow®](https://apl.pedemontana.com/jax-web/scopri-il-free-flow.jsf):
> «Autostrada Pedemontana Lombarda è la prima autostrada italiana [...] che ti consente di viaggiare senza doverti
> mai fermare al casello [...] Il Sistema Free flow® non prevede la presenza dei caselli.»

### Scadenza: 15 giorni (`verified: true`)

[FAQ Free Flow® e pagamento del pedaggio](https://www.pedemontana.com/it/pedaggio-e-assistenza/faq/free-flow-pagamento-pedaggio):
> «Il pagamento del pedaggio di tutti i transiti effettuati nell'arco dello stesso giorno solare deve essere
> corrisposto entro i successivi 15 giorni naturali e consecutivi.»

[I termini di pagamento](https://apl.pedemontana.com/termini-di-pagamento):
> «Il pagamento del pedaggio deve essere effettuato entro 15 giorni solari e consecutivi dalla data di ciascun transito.»

Le due formulazioni coincidono: scadenza = data del transito + 15 giorni, fine giornata.

Conferma l'ipotesi in `PLAN.md`: **i transiti si aggregano per giorno solare**, non si paga per singolo passaggio.
E l'aggregazione è per **concessionario**, non per strada: A36, A59 e A60 dello stesso giorno sono un pagamento solo.
Per questo `rules.json` ha ora il campo `operator` sulle zone e la sezione `operators`.

### Non esiste una seconda scadenza

A differenza di Area C (ticket differito a 7 giorni), qui **dopo i 15 giorni non si può più pagare spontaneamente**:

> «l'importo dei transiti da pagare resta visibile esclusivamente nei 15 giorni a disposizione per il pagamento.»

Scaduto il termine parte il recupero crediti: sollecito con costi amministrativi, poi società esterna. In più,
sanzione amministrativa da **87 a 344 €** e **-2 punti** sulla patente (art. 176 commi 11, 11-bis e 21 CdS;
art. 126-bis CdS). Dal 01/06/2018 c'è collaborazione con la Polizia Stradale sulle attività sanzionatorie.

**Conseguenza per l'app:** per Area C il promemoria «ultima possibilità» al settimo giorno è un ripiego utile;
qui il quindicesimo giorno è l'unico appiglio e dopo non c'è rimedio. Il `lastCall` sulle zone free flow va
trattato come critico, non come cortesia.

### Canali ufficiali di pagamento (`verified: true`)

Dalla FAQ ufficiale. Il link «Paga il pedaggio» del sito punta a `apl.pedemontana.com/jax-web/jawBridge/home.jsf` (200 OK).

- **Telepedaggio** (Telepass o altro operatore SET/SIT-MP): addebito automatico al passaggio sotto il portale
- **Conto Targa**: domiciliazione su conto corrente o carta, gratuito
- **Ricaricabile Pedemontana**: borsellino elettronico associato alla targa, gratuito
- **Sito** `pedemontana.com` → «Paga il pedaggio», anche via **pagoPA**
- **App «Pedemontana Lombarda»** (App Store / Google Play)
- **CBILL** codice azienda `0335M` e sportelli automatici Intesa Sanpaolo (commissione 0,50 €)
- **Poste Italiane**: sezione «Paga Online» su poste.it e uffici postali
- **Satispay**
- **Punti di assistenza**: Punto Verde di Mozzate (CO) sull'A36; punti cortesia Milano Serravalle (A52 Sesto San Giovanni, A7 Milano Ovest)
- Esercenti convenzionati

Calcolo del pedaggio: https://apl.pedemontana.com/calcola-il-pedaggio — l'importo dipende da tratta e classe
volumetrica del veicolo, non è un valore fisso. Per questo `amountEur` è `null` sulle zone free flow.

Call center: **800 936 360** (dall'estero +39 011 089 80 90).

### Esenzioni: nessuna utile all'onboarding

[Esenzione dal pagamento del pedaggio](https://apl.pedemontana.com/jax-web/esenzione-dal-pagamento-del-pedaggio.jsf):
solo art. 373 comma 2 del DPR 495/1992 — associazioni di volontariato, forze armate, funzionari abilitati al
servizio di Polizia Stradale — e richiede autocertificazione.

**Nessuna esenzione per veicoli elettrici**, a differenza di Area C. L'unico interruttore sensato per le zone
free flow è «ho Telepass», che disattiva i promemoria perché l'addebito è automatico.

Esistono sconti (non esenzioni): «Sconto 30% per motocicli», «Nuovo Piano Sconti 2026». Non incidono sulla scadenza.

### Nota di sicurezza — phishing

Pedemontana pubblica un [avviso sulle truffe](https://www.pedemontana.com/it/media/protetti-dalle-truffe-fate-attenzione-ai-falsi-avvisi-di-pagamento-pedaggi):
circolano e-mail, SMS e WhatsApp che imitano richieste di pagamento pedaggi usando loghi ufficiali.

È un argomento a favore dell'app: un promemoria locale che apre **solo** l'URL ufficiale è più sicuro di un SMS.
Da valutare una riga esplicita nella schermata Info in M3.

---

## Tracciati A36 / A59 / A60 (`verified: true`)

Estratti da **OpenStreetMap** via Overpass il **2026-09-23**, licenza **ODbL 1.0**.
Rigenerabili con `python3 tools/build_freeflow.py`.

Query, una per strada, bbox `45.55, 8.60 → 45.95, 9.35`:

```
way["highway"="motorway"]["ref"~"^A ?36$"](bbox); out geom;
```

`highway=motorway` **esatto** è una whitelist: esclude per costruzione `motorway_link` (rampe e svincoli),
`construction`, `proposed` e `trunk`. Verificato a valle che non resti alcuna way con `construction:ref`
o `proposed:ref`.

| Strada | Way | Catene | Lunghezza way | Nome OSM |
|---|---|---|---|---|
| A36 | 53 | 2 | 41,1 km | Autostrada Pedemontana Lombarda |
| A59 | 41 | 2 | 5,4 km | Tangenziale di Como |
| A60 | 16 | 2 | 8,9 km | Tangenziale Sud di Varese |

Le way tagliate portano `toll=yes`, coerente col free flow.

### Perché le lunghezze sembrano piccole

A prima vista A59 con 5,4 km e A60 con 8,9 km sembrano tronche rispetto alle tangenziali "da mappa".
Non lo sono: la lunghezza in tabella è la **somma delle carreggiate**, quindi il tracciato è circa la metà —
A36 ≈ 20,5 km, A59 ≈ 2,7 km, A60 ≈ 4,5 km. Corrisponde ai **soli lotti in esercizio** di Pedemontana
(A36 Tratta A + B1, e i primi tratti delle due tangenziali), che è esattamente ciò che va tariffato oggi.

⚠️ Il riscontro è per coerenza interna, non su una tabella chilometrica ufficiale di Pedemontana: quella
pagina non è stata raggiunta. Se un lotto nuovo apre, il tracciato va rigenerato.

### Tratti ambigui: nessuno

Cercata la viabilità ordinaria (`trunk|primary|secondary|tertiary|unclassified|residential|living_street|service`)
entro 40 m dall'autostrada **e allineata** entro 30°:

| Strada | Segmenti ordinari vicini | Tratto parallelo contiguo più lungo | Catene ambigue |
|---|---|---|---|
| A36 | 836 | 575 m | 0 |
| A59 | 324 | 461 m | 0 |
| A60 | 353 | 313 m | 0 |

Una catena è marcata `ambiguous` se il tratto parallelo contiguo supera **`min(minFastProgressM, minProgressM)`**
= 1000 m, cioè il ramo più permissivo dei due: basta che uno scatti perché il transito nasca.
**Nessuna catena reale supera la soglia** — il massimo misurato è 575 m, con margine di 425 m.

Il ramo `ambiguous` resta quindi non esercitato dai dati veri: è coperto da quattro casi sintetici nei test,
altrimenti sarebbe codice non provato.

### Il ramo veloce senza avanzamento minimo era un bug

Nella prima stesura il ramo veloce chiedeva solo cinque punti consecutivi vicini, veloci e allineati, **senza
alcun avanzamento minimo**. Il tratto di viabilità parallela più lungo misurato è 575 m: a 70 km/h si copre
in mezzo minuto e produce una quindicina di punti veloci e allineati entro tolleranza. Era un falso positivo
garantito ogni volta che si costeggia l'autostrada.

Correzione: il ramo veloce vuole anche `minFastProgressM` (1000 m), scelto sopra i 575 m misurati con margine.
Di conseguenza il criterio di ambiguità guarda ora il **minimo fra i due rami** e non il solo ramo lento:
prima il minimo era di fatto zero, perché il ramo veloce non aveva soglia.

Anche il pavimento del "probabile" è stato alzato alla stessa soglia. Sotto i 1000 m un tratto parallelo e un
pezzo di autostrada sono indistinguibili, quindi un "probabile" sarebbe comunque un falso positivo che chiede
conferma ogni volta che si costeggia l'autostrada.

Il test contiene la prova di cogliere il bug: rieseguito con `min_fast_progress=0` lo stesso percorso
**deve** produrre un transito confermato, altrimenti passerebbe per conto suo senza provare la correzione.

### monitorRegions

Copertura golosa con ricerca binaria sul raggio, per trovare il più piccolo che stia nel budget:
**12 cerchi** per le tre autostrade, raggio massimo **2945 m** (margine 500 m incluso).
Con Area C fanno **13 su 20** di `CLMonitor`, ne restano 7.

Ripartizione: A36 8, A59 2, A60 2. Sono cerchi ampi, che si accendono in mezza Brianza: il contenimento
non è geometrico ma comportamentale, perché l'ingresso in regione non avvia il tracciamento fine, lo avvia
la conferma `CMMotionActivity` "in auto" (`requiresInVehicle: true`).

### Verifiche

21 controlli in `tools/build_freeflow.py`. Se uno fallisce non scrive nulla.

**Negativi — zero transiti:** filtro in-auto spento; cavalcavia perpendicolare a 50 km/h; strada parallela
a 60 m e a 45 m; veicolo fermo con rumore GPS per 20 minuti.

**Positivi:** A36 a 110 km/h; **A36 in coda a 20 km/h** (via avanzamento, 7989 m); A36 con rumore GPS 25 m;
A59 percorsa per intero.

**Soglie rinforzate:** ambiguo a 60 km/h con 2500 m → probabile; a 110 km/h → confermato; con 4500 m →
confermato; tratto breve → nessuno.

Due test contengono un controllo del proprio presupposto, perché senza passerebbero per la ragione sbagliata:

- il cavalcavia verifica di essere **davvero perpendicolare** (delta 90,0°) e di **attraversare davvero** la
  carreggiata. Alla prima stesura il vettore di moto era sbagliato e produceva una traccia *parallela*: il
  test falliva segnalando "allineato", che era corretto — era il test a essere sbagliato, non l'algoritmo;
- la strada parallela verifica di essere **fuori tolleranza da tutta la rete** prima di pretendere zero
  transiti. Con carreggiata doppia, spostarsi di 45 m dal verso sbagliato finisce sull'altra carreggiata,
  a meno di 40 m, e il test non proverebbe nulla.

---

## Nota metodologica

`comune.milano.it` risponde **403** a richieste senza User-Agent da browser. Serve `curl -sSL -A "Mozilla/5.0 ..."`.

I riassunti automatici dei motori di ricerca su Area C sono **inaffidabili**: hanno riportato come vigente
l'estensione al weekend, smentita da tre fonti ufficiali. Verificare sempre sulla pagina del Comune o sul Disciplinare.
