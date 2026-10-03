# Fonti, metodo e verifiche

Preparato il 19 settembre 2026. Il caso e i risultati sono originali per questa lezione.

## Riferimenti consultati

- [D.M. 17 gennaio 2018 – NTC](https://www.gazzettaufficiale.it/eli/id/2018/2/20/18A00716/sg).
- [Testo ufficiale NTC in PDF](https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf): combinazioni §§2.5–2.6, tabella 2.6.I; vento §3.3; neve §3.4, figura 3.4.3 per le due falde. Non vengono riprodotte le tavole della norma.
- [D.M. 9 marzo 2023 – modifiche](https://www.gazzettaufficiale.it/eli/id/2023/03/22/23A01847/SG). Per un progetto consultare il testo vigente completo; la lezione non è una ricognizione legale delle norme applicabili.
- [SteelConstruction.info – proprietà dell'acciaio](https://steelconstruction.info/topics/design/steel-material-properties): proprietà elastiche di riferimento, E e nu.
- [JRC – Design of Steel Buildings, worked examples](https://eurocodes.jrc.ec.europa.eu/publications/eurocodes-background-applications-design-steel-buildings-worked-examples): approfondimento di progettazione in acciaio, non fonte dei numeri del nostro caso.
- `tool/materials.json` e documentazione TopOptLab 0.4: preset acciaio, massa volumica, unità e limiti di screening.

## Scelte originali dell'esercizio

Luce 6 m, piede 0,3 m, rialzo 1,5 m, interasse 3 m, spessore 12 mm. G1=0,15 e G2=0,60 kN/m² per proiezione orizzontale; neve al suolo 1,00 kN/m², CE=Ct=1; suzione netta normale 1,00 kN/m². Non sono valori verificati per una località. Ogni stazione rappresenta 3 m² di area tributaria orizzontale.

La modellazione è Q4 a tensione piana, elastica isotropa, con appoggi bilaterali e sei forze puntuali. SLS uniforme, tre casi ULS neve e un caso ULS uplift sono un sottoinsieme didattico delle azioni. Non si applicano contemporaneamente i casi alternativi. I pesi dell'obiettivo sono tutti 1, distinti dai coefficienti dei carichi.

La geometria estratta è binaria sulla griglia originaria: nessuno smoothing e nessuna mesh conforme a una superficie ricostruita. Lo studio h=100/50/25 suddivide la stessa forma binaria: massa e punti di carico restano fissi. Una nuova ottimizzazione a h=50 è invece un esperimento diverso.

Il massimo di tensione continua a crescere con il raffinamento. I carichi/vincoli puntuali e gli spigoli richiedono un modello locale più fisico. Il confronto con un altro solutore e le verifiche di instabilità, collegamenti e codice strutturale non sono svolti in questa lezione.

## Provenienza dei risultati e verifiche eseguite

- Tre fasi effettivamente risolte con cinque casi ciascuna; più due mesh di raffinamento della parte estratta.
- Peso proprio coerente con massa e fattore di gravità di ogni caso.
- Reazioni confrontate con equilibrio manuale di forze e momenti su tutti i casi del pieno e della parte estratta; scarto inferiore a 1e-5 N.
- Griglia generata con RhinoCommon confrontata con la richiesta Python: 630 celle attive, 44 Keep e corrispondenza dei sei nodi di carico.
- Collegamenti risolti in Grasshopper senza finestra: cinque Load Case, ciascuno con sei forze e Gravity; nessun errore su geometria, condizioni, materiale e Settings.
- Entrambi gli archivi GH/GHX riletti con SDK: proprietà e 164 oggetti verificati.
- Lo script `source/reproduce.py` è stato eseguito in una cartella nuova: masse, arresto e raffinamento riprodotti.
- PowerPoint: 40 slide con note, 15 tabelle e 4 grafici nativi con dati incorporati. Controlli del pacchetto, reimportazione e rendering completati; slide ispezionate visivamente. Dati dei grafici arrotondati a sei decimali; JSON conserva la precisione originale.
- Non eseguiti: collaudo interattivo del nuovo file in Rhino (preview, pulsanti, Bake/Undo) e apertura nella applicazione Microsoft PowerPoint. Il docente deve fare una prova prima della lezione.

## Figure

Tutte le mappe FEM, le densità, la forma binaria e i disegni geometrici derivano dai dati del caso. I grafici di massa, convergenza e picchi sono modificabili in PowerPoint. `figure/roof_concept.png` è invece un'illustrazione concettuale generata, non una fotografia o una geometria verificata. La reticolare della copertina è illustrativa e differisce dalla topologia calcolata.

Immagine di copertina generata con ImageGen, modalità built-in. Prompt originale:

> Use case: scientific-educational. Asset: introductory image for a university structural engineering lecture, landscape 16:9. Create a clean, elegant architectural axonometric cutaway illustration of a modest single-storey house with a pitched gable roof, on an off-white studio background. Remove part of the roof covering so several parallel steel roof trusses and longitudinal purlins are visible. Highlight ONE transverse steel truss in dark teal, the others in pale graphite grey. The truss has a horizontal bottom chord, two sloped top chords, and a few structurally plausible triangular webs, supported at two opposite walls. Show a modest roof pitch about 27 degrees, not a very steep roof. This is a conceptual architectural illustration, not a FEM plot or construction detail. High-end educational model render, precise edges, soft shadows, subdued materials. Compose the house towards the right two thirds with generous clean negative space at left for a slide title. No text, no labels, no numbers, no arrows, no logos, no people, no watermark.

Il software usa la libreria topoptlab di Stefan Hiemer. Il codice fornito con questa esercitazione segue la licenza GPL-3.0-or-later del progetto; vedere source/LICENSE.
