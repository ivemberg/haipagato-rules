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

## Nota metodologica

`comune.milano.it` risponde **403** a richieste senza User-Agent da browser. Serve `curl -sSL -A "Mozilla/5.0 ..."`.

I riassunti automatici dei motori di ricerca su Area C sono **inaffidabili**: hanno riportato come vigente
l'estensione al weekend, smentita da tre fonti ufficiali. Verificare sempre sulla pagina del Comune o sul Disciplinare.
