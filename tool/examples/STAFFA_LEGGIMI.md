# Staffa per mensola — avvio rapido

Apri **engineering_shelf_bracket_3d.gh** con il plugin aggiornato.

Modello: 250 × 150 × 25 mm, quattro fori nominali da 8 mm, piastre conservate e volumi riservati a viti/utensili. Il diametro è un parametro di studio, non la scelta definitiva del tassello.

- **Payload PER BRACKET / kg = 4**: carico su ogni staffa.
- **Shelf share per bracket / kg = 0.5**: ipotesi da sostituire con la quota reale del peso del ripiano.
- X va dal muro alla punta; Z è verticale; Y è la larghezza.
- ABS è il riferimento già nel programma, non un materiale stampato qualificato.

Casi indipendenti: distribuito, anteriore, anteriore a destra e a sinistra. Ogni caso include peso del ripiano e della staffa. Non sommarli.

## Ordine dei pulsanti

1. **BASELINE FEM → RUN**, poi VIEW=0.
2. **OPTIMIZATION → RUN**, poi VIEW=1.
3. **FINAL VERIFICATION → RUN**, poi VIEW=2.
4. **EXTRACT**, poi VIEW=3.
5. **FINAL FEM**, poi VIEW=4.

**Load case** seleziona 1–4. **Field=1** mostra spostamenti; **Field=2** tensioni. Durante ottimizzazione le tensioni sono rilassate: controlla quelle della FEM finale.

Il limite di spostamento iniziale è 1 mm, scelto per lo studio. Il limite di tensione è disattivato finché mancano i dati del materiale stampato. Leggi stato, fattibilità e Report.

Dopo modifiche: Stop se sta calcolando, Reset e riparti dalla FEM iniziale.

## Celle e fori

Il nuovo esempio parte da **Cell size=2.5 mm**, **Voxel limit=250000**, **Physical filter radius=9 mm**, **Backend=4 (CUDA)** e **Threshold=0.32**. Su un PC senza CUDA seleziona esplicitamente **Backend=2 (CPU AMG)**. La scelta non cambia da sola.

A 2,5 mm la staffa ha 60.000 celle totali; a 2 mm ne ha 121.875. Prima di Run leggi il pannello Resources. Il programma controlla la memoria libera: alzare Voxel limit non permette di superare il budget di RAM/VRAM. Le griglie più fini richiedono tempi maggiori, soprattutto nei quattro casi di ottimizzazione.

Mantieni il filtro a 9 mm quando confronti risoluzioni diverse. Per vedere la forma continua premi EXTRACT e scegli VIEW=3: la vista della densità resta una griglia. Le celle più piccole migliorano la discretizzazione, ma non dimostrano da sole l'accuratezza delle tensioni.

I fori nella griglia sono approssimati. Il nuovo EXTRACT ricostruisce piastre e fori dalla specifica CAD collegata: la tolleranza radiale iniziale è 0,05 mm, indipendente dalla cella FEM. La superficie esportata è triangolata, non una superficie CAD esatta. **shelf_bracket_nominal_interfaces.3dm** è il riferimento degli attacchi, non il pezzo ottimizzato. La tolleranza di stampa e gli accoppiamenti vite restano da verificare. La FEM finale può ancora rifiutare una superficie con triangoli troppo sottili: non considerare una semplice estrazione come verifica strutturale.

I fissaggi sono idealizzati con due zone rigide. La portata reale dipende anche da stampa, materiale, carico nel tempo, viti, tasselli e muro.

Guida completa in inglese: **docs/SHELF_BRACKET.md**.

Misure aggiornate e stato delle prove: **docs/RESOLUTION_VALIDATION.md**. La precedente validazione da 5 mm è conservata separatamente.

Sul risultato da 2,5 mm verificato, la soglia 0,32 conserva circa 343 g e dà uno spostamento massimo di 0,243 mm nella FEM a voxel. La precedente soglia 0,35 eliminava troppo materiale. Questi valori non sono la verifica della mesh finale né una portata certificata.

## Stato preciso di questo aggiornamento

La staffa fine completa FEM iniziale, ottimizzazione, verifica a voxel ed estrazione.
La FEM tetraedrica della nuova superficie non è ancora completata: Gmsh può fermarsi
sulla sua parametrizzazione. Il caso precedente da 5 mm ha completato il percorso CAD/FEM,
ma questo non verifica automaticamente la nuova forma.

Puoi aprire subito **shelf_bracket_25mm_candidate_mm.stl** in Rhino impostando mm: è la
superficie calcolata, circa 310 g, con provenienza nel JSON omonimo. Serve per osservare e
lavorare sulla forma; non è ancora un pezzo approvato per la stampa o per una portata.
