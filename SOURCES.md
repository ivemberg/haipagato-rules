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

**Da chiudere prima del rilascio.** Percorsi possibili: Albo Pretorio del Comune, oppure scrivere a
`MTA.UfficioAreaC@comune.milano.it`.

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

## Nota metodologica

`comune.milano.it` risponde **403** a richieste senza User-Agent da browser. Serve `curl -sSL -A "Mozilla/5.0 ..."`.

I riassunti automatici dei motori di ricerca su Area C sono **inaffidabili**: hanno riportato come vigente
l'estensione al weekend, smentita da tre fonti ufficiali. Verificare sempre sulla pagina del Comune o sul Disciplinare.
