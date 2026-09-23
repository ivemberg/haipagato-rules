# haipagato-rules

Regole e geometrie di **["Hai pagato?"](https://github.com/ivemberg/haipagato-)**, l'app che ricorda
di pagare l'Area C di Milano e i pedaggi free flow prima che arrivi la multa.

Questo repo contiene i dati di dominio dell'app: orari, scadenze, esenzioni e geometrie delle zone.
È pubblico perché serve a due cose: essere raggiungibile via GitHub Pages per l'aggiornamento remoto
delle regole, e ospitare dati con licenze che **non possono stare sotto la licenza di un repo
applicativo** — CC BY 4.0 per i dati del Comune, ODbL per quelli OpenStreetMap.

La storia dei commit è quella originale, importata con `git subtree split`: ogni valore di
`rules.json` ha il commit che dice da quale fonte viene e quando è stato verificato. È la parte che
serve a difendere il dato fra sei mesi, e per questo non è stata buttata via con una copia.

## Licenze, per file

I file hanno origini diverse e licenze **diverse e non compatibili fra loro**. Per questo la licenza è
dichiarata per file, sia in questa tabella sia nel campo `attribution` in testa a ogni GeoJSON.

| File | Origine | Licenza | Attribuzione |
|---|---|---|---|
| `area-c.geojson` | [Comune di Milano, dataset `ds51`](https://dati.comune.milano.it/dataset/ds51_trafficotrasporti_aree_pedonali_ztl) | **CC BY 4.0** | Contiene dati del Comune di Milano — dati.comune.milano.it, licenza CC BY 4.0 |
| `area-c-varchi.geojson` | [Comune di Milano, dataset `ds82`](https://dati.comune.milano.it/dataset/ds82_infogeo_varchi_elettronici_localizzazione_) | **CC BY 4.0** | idem |
| `a36.geojson`, `a59.geojson`, `a60.geojson` | OpenStreetMap via Overpass | **ODbL 1.0** | © OpenStreetMap contributors |
| `rules.json` | redazione propria, da fonti ufficiali citate in `SOURCES.md` | vedi sotto | — |

## Perché `rules.json` non contiene geometrie

ODbL è una licenza **share-alike**: un file derivato da OSM è un *derivative database* e va ridistribuito
a sua volta sotto ODbL. CC BY non lo è.

Se `rules.json` contenesse coordinate prese da OSM, l'intero file diventerebbe ODbL e si porterebbe dietro
anche le regole redazionali e i dati CC BY del Comune, mescolando tre licenze in un unico file.

Perciò vale un vincolo preciso, scritto anche in `CLAUDE.md`:

> **`rules.json` non contiene geometrie.** Solo riferimenti a file (`geometry.file`, `geometry.gatesFile`)
> e parametri numerici. Le coordinate stanno nei GeoJSON, ognuno con la sua licenza.

Le `monitorRegions` in `rules.json` sono l'unica eccezione apparente: sono centri e raggi **calcolati**,
non coordinate estratte da OSM. Un centro di cerchio e un raggio non riproducono il tracciato e non
costituiscono un estratto sostanziale del database. Se un domani si volesse essere rigorosi fino in fondo,
la via pulita è spostarle in un file dedicato con licenza ODbL.

## Rigenerare i dati

```
python3 tools/build_areac.py      # perimetro Area C e varchi, dal Comune di Milano
python3 tools/build_freeflow.py   # tracciati A36/A59/A60, da OpenStreetMap
python3 tools/build_gpx.py        # percorsi GPX per il simulatore
```

⚠️ `tools/` arriva per intero dal repo dell'app, quindi contiene anche script che **qui non hanno
senso** (`verify.sh`, `check_no_kotlin_leak.sh`, `build_xcframework.sh`, `sync-rules.sh`): si
riferiscono al progetto iOS e non funzionano senza. Quelli che contano qui sono i tre sopra, più
`areac_lib.py` e `freeflow_lib.py` che usano.

Entrambi usano solo la libreria standard di Python, scaricano le fonti in `tools/.cache/`
(non versionata) ed eseguono le verifiche geometriche. **Se una verifica fallisce non scrivono nulla.**

## `schemaVersion`

`rules.json` dichiara `schemaVersion`, che è la versione della **forma** del file — diversa da
`version`, che è la versione dei **dati**.

Un'app vecchia deve poter leggere dati nuovi, ma non una forma che non capisce: il parser rifiuta
un file con `schemaVersion` sconosciuto e resta su quello incluso nel bundle. Chi cambia la forma
deve incrementarlo, altrimenti le app già installate proveranno a leggere qualcosa che non è.

## Fonti e verifiche

Ogni valore dei file di questa cartella è tracciato in [`SOURCES.md`](SOURCES.md) con URL, citazione
testuale e data di consultazione. I campi `verified: false` segnalano i valori **non** confermati da
fonte ufficiale: non sono errori, sono rischi dichiarati.
