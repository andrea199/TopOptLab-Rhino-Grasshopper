# Centina di un tetto: laboratorio FEM e ottimizzazione 2D

Lezione di 3 ore in italiano per una classe di ingegneria, con componenti software in inglese. Caso di studio: centina metallica di 6 m, cinque casi di carico, FEM del pieno, ottimizzazione e rianalisi della parte estratta.

## Inizia da qui

1. Estrai tutto lo ZIP in una cartella scrivibile. Lavora su una copia.
2. Apri `Centina_tetto_2D_lezione_v3.pptx`. Le note del relatore spiegano ogni slide e contengono le risposte attese. In PowerPoint attiva Note o Visualizzazione relatore.
3. Apri `case/roof_geometry_mm.3dm` in Rhino 8: millimetri, vista Top, Zoom Extents.
4. Apri `case/roof_2d_classroom.gh` in Grasshopper. Le geometrie sono già incluse; non occorre selezionarle da Rhino. Il file `.ghx` contiene la stessa definizione in formato testuale.
5. Mantieni i valori iniziali. Premi RUN in ordine: **01 BASELINE FEM → 02 OPTIMIZATION → 03 FINAL VERIFICATION**. Aspetta il completamento di ogni fase.
6. Review: Stage 0/1/2 sceglie il risultato visibile; Case 1–5 sceglie il carico; Field 0 è il campo predefinito, 1 spostamento, 2 tensione. Non avvia il calcolo.
7. Confronta i risultati con `reference/teaching_values.json` e con i report HTML già inclusi.

## File inclusi

- PowerPoint: 40 slide, 40 note del relatore, 15 tabelle e 4 grafici nativi modificabili.
- `GUIDA_DOCENTE.md`: programma, spiegazioni slide per slide, risposte e criteri di valutazione.
- `ESERCITAZIONE_STUDENTI.md`: consegna, tabella da compilare e domande.
- `case/`: geometria Rhino, modello Grasshopper e richiesta numerica di riferimento.
- `reference/fem`, `optimize`, `verify`: dati, casi e report delle tre fasi.
- `reference/refinement_h50`, `refinement_h25`: FEM a geometria estratta costante, raffinata.
- `figure/`: mappe numeriche e illustrazione concettuale originale della copertura.
- `source/`: modello e script di riproduzione dei calcoli, generatore C# dell'esempio.
- `FONTI_E_METODO.md`: fonti, assunzioni, provenienza delle figure e confini delle verifiche.

## Software necessario sui PC della classe

Rhino 8 con licenza attiva, Grasshopper e TopOptLab **0.4.0-dev** con il runtime Python configurato. CUDA non è necessaria: il caso usa CPU direct.

Questo è il pacchetto della lezione, non un installer autonomo del software. Su un PC nuovo usare la cartella completa TopOptLab-Rhino: installare Python 3.13 a 64 bit, salvare e chiudere Rhino, eseguire `INSTALL.cmd` dalla cartella del software. Il setup richiede internet per le dipendenze. Mantenere poi la cartella software nella stessa posizione; se si sposta, ripetere la configurazione. Non basta copiare il solo `.gha`.

Prima della lezione il docente deve aprire il nuovo file in Rhino ed eseguire le tre fasi. Sono stati controllati archivio, geometria, collegamenti e calcoli senza interfaccia; Bake/Undo e interazione del nuovo esempio non sono stati collaudati automaticamente.

## Risultati attesi con h = 100 mm

- Pieno: 630 celle, 44 Keep, 593,46 kg, max |u| SLS 0,447 mm.
- Ottimizzazione: Volume 0,30, 36 iterazioni nel riferimento, massa equivalente 178,038 kg.
- Threshold 0,40: 212 celle, 199,704 kg, max |u| SLS 1,229 mm.
- ULS neve a sinistra: massimo von Mises 57,03 MPa sulla griglia da 100 mm.
- Uplift: reazione verticale −6,851 kN per appoggio nella parte estratta.

Le tensioni di picco non sono convergenti nello studio incluso: salgono a 141,16 MPa con h = 25 mm. Il caso insegna anche a individuare i limiti dei carichi/appoggi puntuali.

## Problemi frequenti

| Sintomo | Controllo utile |
| --- | --- |
| Componenti mancanti | Verificare TopOptLab 0.4, installazione e riavvio di Rhino. |
| Worker/Python non disponibile | Controllare la configurazione del progetto; non spostare solo plugin o runtime. |
| Force acts in a constrained direction | Il carico è applicato su un DOF bloccato: controllare G e l'uscita N. |
| Use point or curve geometry | Usare un parametro Point/Curve, non una scritta contenente coordinate. |
| Fonte della verifica incompatibile | Ricalcolare l'ottimizzazione con gli stessi dati della verifica. |
| Parte sconnessa o nodo rimosso | Controllare Keep e soglia; non interpretare un vecchio risultato come quello attuale. |
| Preview sovrapposte | Nascondere le preview di geometria/condizioni e usare Review per una sola fase. |
| Cell size più piccolo | Usare 50 o 25 mm nel caso; mantenere Radius = 180/h; il costo numerico cresce. |

## Che cosa rappresenta

Modello elastico piano di una piastra a spessore costante. I valori climatici sono assunti per l'esercitazione, non ricavati da un sito reale. Le cinque combinazioni sono un sottoinsieme didattico. Restano da progettare instabilità fuori piano, sezioni/dettagli, collegamenti, ancoraggi e verifiche normative applicabili. La forma estratta è a celle quadrate: una modifica geometrica richiede un nuovo calcolo.
