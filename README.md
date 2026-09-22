# `rules/` — regole e geometrie di "Hai pagato?"

Questa cartella contiene i dati di dominio dell'app: orari, scadenze, esenzioni e geometrie delle zone.
Viene **ridistribuita pubblicamente** su GitHub Pages, quindi le licenze dei dati di origine valgono
anche qui e non solo dentro l'app.

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
```

Entrambi usano solo la libreria standard di Python, scaricano le fonti in `tools/.cache/`
(non versionata) ed eseguono le verifiche geometriche. **Se una verifica fallisce non scrivono nulla.**

## Fonti e verifiche

Ogni valore dei file di questa cartella è tracciato in [`SOURCES.md`](SOURCES.md) con URL, citazione
testuale e data di consultazione. I campi `verified: false` segnalano i valori **non** confermati da
fonte ufficiale: non sono errori, sono rischi dichiarati.
