# Guida docente

## Organizzazione

Prerequisiti: statica piana, elasticità e concetti di FEM. Gruppi da 2–3 persone. Durata proposta: 180 minuti.

| Attività | Minuti | Slide orientative |
| --- | ---: | --- |
| Problema e obiettivi | 15 | 1–6 |
| Materiale, carichi, combinazioni e statica | 35 | 7–14 |
| Preparazione ed esecuzione FEM | 25 | 15–22 |
| Previsione e ottimizzazione | 30 | 23–28 |
| Rianalisi e lettura critica | 20 | 29–36 |
| Variante in gruppi | 35 | 37 |
| Discussione e valutazione | 20 | 38–40 |

Preparazione: verificare il file GH su ogni PC, fare una corsa di riferimento e tenere disponibili i report inclusi. Una casa specifica non è stata assegnata: chiedere agli studenti quali dati reali mancano prima di discutere la sicurezza della struttura.

## Derivazioni da svolgere alla lavagna

- Area piena = 6×0,3 + 6×1,5/2 = 6,3 m²; volume = 0,0756 m³; massa = 593,46 kg.
- Area tributaria per stazione = 3×1 = 3 m² (orizzontali). Sei stazioni coprono 18 m².
- SLS neve uniforme: q = 0,15 + 0,60 + 0,80 = 1,55 kN/m²; F = 4,65 kN per stazione.
- ULS neve uniforme: q = 1,3×0,15 + 1,5×0,60 + 1,5×0,80 = 2,295 kN/m²; F = 6,885 kN.
- Falda con mezza neve: q = 1,3×0,15 + 1,5×0,60 + 1,5×0,40 = 1,695 kN/m²; F = 5,085 kN.
- Per vento normale alla falda: area inclinata = bΔx/cosα; Fx = ±γW qW bΔx tanα; Fy,vento = γW qW bΔx.
- Con tanα=0,5: Fx = ±2,250 kN; Fy,vento = 4,500 kN. Permanenti favorevoli = 3(0,15 + 0,8×0,60) = 1,890 kN; Fy netto = +2,610 kN. Aggiungere il peso della centina a 1g tramite Gravity.
- Statica del pieno SLS: Ay=By=(27,9+5,819854509)/2=16,859927 kN.
- Uplift del binario: Ay=By=−(15,66−199,704×9,80665/1000)/2=−6,850786 kN.

Lo schema uplift è STR didattico, non l'intero controllo EQU. Il criterio L/300 = 20 mm è una scelta illustrativa di esercizio, non una prescrizione universale. Il massimo |u| non coincide necessariamente con la freccia verticale in mezzeria.

## Note slide per slide

### 1. Una centina per il tetto

Lezione di tre ore per studenti di ingegneria: assunzioni, FEM, ottimizzazione e lettura critica. Il caso è realistico ma didattico: non sono disponibili località e dati di una casa specifica. La copertina è una illustrazione concettuale generata con ImageGen, non il risultato del solutore. Le mappe successive derivano da calcoli effettivi. Spiegazioni in italiano, nomi dei componenti in inglese.

### 2. Alla fine saprai motivare il modello

Prerequisiti: statica piana, elasticità e concetti di tensione/spostamento. Gruppi di 2–3. Programma: 15 minuti problema, 35 modello e carichi, 25 FEM, 30 ottimizzazione, 20 verifica, 35 esercitazione e 20 discussione. Prima di iniziare chiedere quali dati mancano per progettare una casa reale. Si valuta la qualità delle assunzioni e dei controlli, non soltanto la massa risparmiata.

### 3. Una centina reale richiede più del modello 2D

Si studia una centina interna di una copertura con arcarecci, a interasse 3 m. La variabile di progetto è una piastra sagomata di spessore costante, non un insieme di aste con sezioni commerciali. La forma può ispirare una reticolare, ma convertirla in aste richiede un nuovo modello. Si assume comportamento elastico nel piano. La stabilità fuori piano non è dimostrata: una lastra alta e sottile può essere governata da instabilità. In seguito occorrono controventi, sezioni, saldature/bulloni, ancoraggi e verifiche degli appoggi.

### 4. Il dominio segue l’ingombro del tetto

Polilinea in mm: (0,0), (6000,0), (6000,300), (3000,1800), (0,300), chiusura. Pendenza=1500/3000=0,5; angolo=26,565°. I sei punti sono sulla falda a X=500,1500,2500,3500,4500,5500 mm. Keep protegge due appoggi e sei introduzioni del carico; le regioni sono intersecate col dominio. È una elevazione strutturale disegnata in World XY: in Rhino si guarda dalla vista Top. Y è verticale, non Z.

### 5. Le grandezze che non vanno confuse

Lo spessore resistente t entra in rigidezza e massa; l’interasse tributario b trasforma i carichi della copertura. Area del dominio=6×0,3+6×1,5/2=6,3 m². Volume pieno=6,3×0,012=0,0756 m³. Massa=0,0756×7850=593,46 kg. L’area tributaria della copertura è invece 6×3=18 m² orizzontali. Prima del calcolo far spiegare la differenza agli studenti.

### 6. Due appoggi: tre vincoli di traslazione

A blocca ux e uy; B solo uy. Si eliminano i tre moti rigidi del piano. Bloccare X anche a destra cambierebbe il modello. I Q4 hanno traslazioni, non una rotazione nodale come le travi. Il vincolo verticale è bilaterale: sotto vento può esercitare una reazione verso il basso, quindi si assume un ancoraggio. Un appoggio di solo contatto può distaccarsi e richiede un modello diverso. Chiedere quale dettaglio costruttivo realizza il vincolo.

### 7. Acciaio elastico e un sistema coerente di unità

Material: Preset=0, Length units=0 mm, Force units=0 N, Stock=12 mm. E=210000 N/mm², nu=0,30, massa volumica=7850 kg/m³. S235 è un riferimento con snervamento nominale 235 MPa per stock entro 16 mm, da confermare sul prodotto. SF=1,5 dà 156,7 MPa come screening: NON è gammaM né una verifica normativa. Calcolo lineare, isotropo, a piccole deformazioni e tensione piana; esclusi instabilità, plasticità, fatica e incendio. Fonte elasticità: https://steelconstruction.info/topics/design/steel-material-properties; dati preset: tool/materials.json.

### 8. I carichi climatici sono ipotesi dichiarate

Non è assegnata una località: non si inventano zona neve o esposizione. G1=0,15 rappresenta strutture secondarie; G2=0,60 pacchetto/impianti, in kN/m² orizzontali. Neve: sk=1,00 assunto, CE=Ct=1, mu1=0,8 → s=0,80. Vento: suzione netta normale 1,00 kN/m² assunta, già differenza tra pressioni esterne/interne. In un progetto si ricavano da sito, geometria ed esposizione. Il peso della centina è in Gravity: non aggiungerlo di nuovo. Metodo azioni: NTC §§3.3–3.4, https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf.

### 9. Dal carico superficiale alla forza su un punto

Sei risultanti rappresentano il trasferimento dagli arcarecci. Ciascuna raccoglie 1 m di striscia orizzontale ×3 m di larghezza tributaria. Allo SLS q=0,15+0,60+0,80=1,55 kN/m². F=q b Δx=4,65 kN → vettore (0,-4650,0) N. Totale sei forze=27,90 kN. Il peso pieno aggiunge 5,81985 kN. Totale=33,71985 kN. Load riceve la forza TOTALE del componente: se si selezionano più nodi la suddivide, non la ripete per ciascuno.

### 10. La neve va considerata anche sbilanciata

A 26,6° il caso usa mu1=0,8. Il metodo prevede il caso uniforme e le due alternative con coefficiente dimezzato su una falda. I valori in tabella sono caratteristici, prima dei coefficienti della combinazione. Sinistra=P1–P3, destra=P4–P6. Non sommare i tre casi: sono alternativi. La forma simmetrica non giustifica ignorare il carico asimmetrico. Fonte: NTC §3.4.3.3, figura 3.4.3, https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf.

### 11. Il vento normale alla falda ha due componenti

Per la striscia l’area inclinata è bΔx/cos(alpha). Con qw=1 kN/m² normale alla falda: Fy=qw bΔx, Fx=±qw bΔx tan(alpha). Con gammaQ=1,5 e tan(alpha)=0,5: vento ±2,25 kN in X e +4,50 kN in Y. Sottrarre 3×(1,0×0,15+0,8×0,60)=1,89 kN di permanenti favorevoli: Fy=+2,61 kN. Gravity aggiunge il peso della centina a 1g. È un esempio STR di uplift, non l’inviluppo completo vento né la verifica EQU globale. Coefficienti: NTC tabella 2.6.I; metodo vento §3.3, https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf.

### 12. Cinque Load Case, già separati nel file

SLS=esercizio; ULS=ultimo. Caso 1: G1+G2+S. Casi 2–4: 1,3G1+1,5G2+1,5S con distribuzioni neve diverse. Caso 5: vento 1,5W e permanenti favorevoli 1,0G1, 0,8G2. Nei casi neve ULS Gravity usa 1,3g=12,748645 m/s²; altrove 1g. Le forze includono già i coefficienti: NON amplificarle con Weight. Il set didattico esclude combinazioni con variabili concomitanti, sisma, manutenzione ed EQU. Fonte coefficienti: NTC tabella 2.6.I, https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf.

### 13. Prima della FEM: controlliamo le reazioni a mano

Pieno SLS: 6×4,65+593,46×9,80665/1000=33,71985 kN. Per simmetria Ay=By=16,85993 kN. ULS uniforme: 6×6,885+1,3×5,81985=48,87581 kN → 24,43791 kN per lato. ULS neve sinistra: Ay=23,08791, By=20,38791 kN. La statica manuale di forza/momento coincide con il solver entro 1e-5 N. Fare prevedere quale appoggio aumenti. Equilibrio non significa accuratezza locale: anche una mesh grossolana può equilibrare bene i carichi.

### 14. Che cosa risolve la FEM in questo esercizio

Q4 a tensione piana: due traslazioni ux,uy per nodo. Materiale, spessore e discretizzazione producono K. Si applicano i vincoli e si risolve il sistema. Le derivate di u danno le deformazioni; la legge elastica dà le tensioni. Von Mises è una grandezza derivata dalle componenti di tensione, diversa da densità e deformata. Il fattore visuale della deformata non modifica il risultato. Il modello 2D non verifica instabilità fuori piano.

### 15. Step 1 · Aprire il materiale della lezione

Estrarre il pacchetto e lavorare su una copia. Servono Rhino 8 con licenza attiva, Grasshopper, TopOptLab 0.4 e Python del progetto già configurato. Aprire case/roof_geometry_mm.3dm: geometria e layer sono modificabili. Aprire case/roof_2d_classroom.gh; le geometrie sono internalizzate, quindi il GH non dipende da selezioni esterne. Il .ghx è una copia testuale. Gli archivi e la griglia sono verificati via SDK; il docente deve comunque aprire il caso in Rhino prima della lezione: non è stato automatizzato il collaudo interattivo.

### 16. Step 2 · Leggere il flusso della definizione

Geometria e Settings a sinistra; tre fasi al centro in verticale; Review a destra; dettagli dei cinque Load Case più in basso. Zoomare sul blocco da discutere. R dell’ottimizzazione va a Source della verifica, non R del pieno. Review cambia ciò che si vede, non quale calcolo parte. Ogni fase ha un proprio RUN. Gli input di condizioni e materiale sono condivisi per garantire modelli coerenti.

### 17. Step 3 · Dominio e zone da conservare

Domain deve mostrare 630 cells e 44 kept. Bounding grid 60×18, ma solo 630 celle nella sagoma. B è una polilinea chiusa, H vuoto, K otto regioni. La selezione avviene per centro cella, quindi la falda diventa a gradini. Keep attachments protegge celle che toccano i nodi di vincolo/carico. h, Radius e Keep hanno ruoli distinti. Per sostituire la curva: parametro Curve, Set one curve; aggiornare anche punti e carichi. Il caso pronto ha geometria fissata a 6 m, non scala automaticamente tutti i dati cambiando la curva.

### 18. Step 4 · Controllare punti, vincoli e vettori

Ogni Load ha D da Domain, G dal punto e F dal parametro Vector. Per costruire una forza usare Vector XYZ; non fare affidamento su testo non convertibile. Caso 1: (0,-4650,0) N. P1 nominale=(500,550,0); nodo FEM=(500,600,0). Gli altri nodi hanno Y=1100,1600,1600,1100,600 mm. È lo snapping alla griglia: controllare l’uscita N. Gli appoggi restano esatti. Force acts in a constrained direction segnala un carico sul grado di libertà bloccato: verificare selezione e schema, non sbloccare un vincolo a caso.

### 19. Step 5 · Impostazioni del calcolo di riferimento

Settings condivisi: CPU direct, 4 thread come limite BLAS, t=12, Volume=.30, 100 iterazioni, Radius=1.8 celle, Threshold=.40, Symmetry=X, Keep attachments=True. La simmetria X riflette rispetto alla mezzeria. Process=unspecified: la centina della lezione non è una parte da stampa 3D. Non si impongono Design Limits globali: si applicherebbero a tutti i casi, mentre qui SLS e ULS hanno criteri differenti da leggere separatamente. Material Stock=12 e Thickness=12 devono essere coerenti.

### 20. Step 6 · Eseguire la FEM del pieno

RUN soltanto in 01 BASELINE FEM. Attendere il termine e leggere Status. Report è il percorso HTML della sessione, con cinque casi. Review Stage=0, Case=1, Field=0 mostra von Mises. Attesi: 593,46 kg, max|u|=.446785 mm, Ay=By=16,85993 kN. Cambiare Case da 1 a 5 seleziona risposte già salvate. Per confrontare tensioni fra fasi scegliere Field=2, Legend maximum=60. Se compaiono molte linee nascondere la preview dei componenti di geometria e condizioni, già nascosta nel file. Salvare report e risultati prima delle varianti.

### 21. La FEM iniziale localizza l’introduzione dei carichi

Mappa del worker sul pieno, caso SLS snow uniform. Scala fissa 0–60 MPa, come nella verifica finale. Il massimo è 29,0598 MPa. Il colore è tensione equivalente, non densità. Indicare appoggi e punti di introduzione del carico: la modellazione puntuale genera forti gradienti. Chiedere dove conservare materiale. Il basso livello di tensione nel piano non dimostra la sicurezza della lastra: l’instabilità è esclusa.

### 22. La deformata è ingrandita per essere leggibile

Coordinate deformate con fattore 100. Il colore è la media elementare del modulo u; il massimo riportato è nodale, 0,446785 mm. Il pieno ha grande altezza resistente nel piano. Deformation display factor cambia solo la visualizzazione, non il calcolo. L/300=20 mm è un criterio didattico illustrativo, non un limite normativo universale. Un requisito reale deve indicare punto, direzione, combinazione e componente della copertura interessato.

### 23. Prima di ottimizzare: fai una previsione

Pausa di cinque minuti. Ogni gruppo disegna i percorsi dai sei carichi ai due appoggi e prova a distinguere zone tese/compresse. Non mostrare ancora la topologia. Si valuta l’ipotesi meccanica, non la somiglianza con un’immagine. Chiedere se alleggerire aumenta o diminuisce spostamenti e forza richiesta agli ancoraggi sotto suzione. Raccogliere previsioni da confrontare con i risultati.

### 24. Ottimizzare significa scegliere dove usare il materiale

Ogni elemento ha una densità relativa rho fra minimo numerico e 1. La penalizzazione SIMP rende poco efficienti densità intermedie; il filtro limita oscillazioni alla scala della griglia. Compliance=f trasposto u: misura di flessibilità rispetto al carico. Si minimizza la somma pesata su cinque casi indipendenti. Weight=1 non normalizza casi di diversa intensità. SLS è incluso qui per dimostrare il flusso: scelta di casi e pesi va motivata. Keep è incluso nel 30%. La gestione della gravità dipendente dalla densità è sperimentale: occorre rianalizzare la forma binaria. Non si garantisce un ottimo globale unico.

### 25. Step 7 · Avviare e leggere l’ottimizzazione

RUN nel blocco 02 OPTIMIZATION dopo aver controllato la FEM. Review Stage=1 e Field=0 per la densità. La corsa di riferimento termina converged dopo 36 aggiornamenti, su un limite di 100. Piccoli scarti tra piattaforme sono possibili. STOP interrompe; RESET rimuove lo stato e prepara un nuovo calcolo. Dopo modifiche del modello ripetere la sequenza completa. Improvement nel report è rispetto all’inizializzazione a volume ridotto, NON al pieno. Leggere sempre termination_reason: iteration_limit non significa converged.

### 26. Il risultato è ancora un campo di densità

Densità effettiva del calcolo: giallo=1, blu circa 0, valori intermedi in mezzo. Massa equivalente=178,038 kg, il 30% del pieno. Una densità intermedia è una variabile numerica, non un materiale industriale già definito. Osservare i percorsi superiore e inferiore senza chiamarli automaticamente aste dimensionate. La forma è simmetrica perché è imposto il vincolo X e i due casi neve asimmetrici sono entrambi presenti. Keep conserva gli attacchi.

### 27. La storia del calcolo rende visibile la convergenza

History del solver, compliance aggregata divisa per quella iniziale. Mostrati punti ogni quattro iterazioni; il JSON contiene l’intera storia. Il finale è circa .082 del punto iniziale: riduzione del 91,8%, ma NON rispetto al pieno. L’inizializzazione diluita al 30% è molto flessibile. Una curva piatta non basta: leggere stato di arresto, variazione del progetto e criteri di convergenza. Il calcolo a peso proprio dipendente dalla densità richiede anche la verifica della parte estratta.

### 28. Step 8 · Threshold trasforma il campo in una parte

Threshold=.40 mantiene elementi rho>=.40. Restano 212 elementi, 199,704 kg, 33,6508% del pieno. Il passaggio a zero/uno cambia il volume: la massa non è più il 30% equivalente. La soglia va seguita dalla FEM, non scelta soltanto esteticamente. Una soglia alta può perdere attacchi o connessioni. L’estrazione resta a celle quadrate, senza smoothing o remeshing conforme. Non presentarla come una superficie 2D liscia già verificata né usare il componente Final Geometry 3D per questo caso.

### 29. Step 9 · Ricalcolare la parte estratta

R di OPTIMIZATION è collegato a Source di FINAL VERIFICATION. Premere RUN della fase 03. Il solver rianalizza la geometria binaria sulla stessa griglia e aggiorna il peso alla massa effettiva. Non è una mesh conforme a una curva smussata. Review Stage=2 e Case da 1 a 5. Se errore per fonte incompatibile, nodo rimosso o disconnessione, correggere il modello e non leggere un risultato precedente come attuale. Verification significa rianalisi numerica, non approvazione normativa; qui non sono richiesti limiti globali.

### 30. La neve sbilanciata diventa il caso più gravoso

ULS snow left della parte binaria h=100. Massimo von Mises=57,0273 MPa, scala 0–60. Il caso uniforme dà 42,0265 MPa: una forma simmetrica non rende governante il carico simmetrico. Guardare introduzione dei carichi e parti sottili. I picchi dipendono dal Q4 e dalla mesh. Non basta 57<235 per dichiarare sicurezza: sono escluse instabilità e comportamento del dettaglio reale. Lo studio di mesh seguirà.

### 31. Confrontiamo tutti i casi, non una sola immagine

Dati dei cinque case files di baseline e verifica. |u| è il massimo modulo nodale, non necessariamente uy in mezzeria. I massimi di |u| sinistra/destra differiscono perché il vincolo orizzontale è solo a sinistra; tensioni massime e compliance dei casi speculari coincidono numericamente. Per la freccia in un punto leggere uy di quel nodo. Max|u| è un limite superiore di max|uy|. SLS serve per i requisiti di esercizio; ULS rappresenta le domande amplificate.

### 32. Meno massa, più deformabilità nel piano

Masse: pieno 593,46; campo densità 178,038; geometria binaria 199,704 kg. Riduzione pieno→binario=66,3492%. Max|u| SLS aumenta da .4468 a1.2290 mm sulla stessa griglia. Compliance SLS:11534,4→15322,2 Nmm. Il progetto è più leggero e più deformabile, non migliore in tutto. L/300=20 mm è un criterio didattico scelto, non norma universale; i valori calcolati sono inferiori, ma questo non esaurisce le verifiche né dimostra stabilità.

### 33. Alleggerire aumenta la richiesta agli ancoraggi

Uplift: sei risultanti sommano+15,66 kN verticali. Al pieno sottrarre 5,81985 kN di peso: trattenuta 9,84015 kN totale. Parte binaria: peso 1,95843 kN; trattenuta 13,70157 kN totale,6,85079 kN per lato. Il grafico mostra i moduli di Ry negativa, non resistenze già pronte per dimensionare bulloni. Servono altre combinazioni, leve, gruppo ancoraggi e resistenza del supporto. Chiedere se il risparmio della centina possa richiedere un ancoraggio diverso.

### 34. Raffinare la mesh tenendo ferma la geometria

Non sono tre ottimizzazioni. Ogni elemento mantenuto a h100 viene suddiviso2×2 e4×4: identici sagoma a gradini, massa, spessore, coordinate di carichi/appoggi. Si isola l’effetto FEM:212→848→3392 elementi. |u| SLS aumenta18,15% fra100 e50 e8,72% fra50 e25: NON è raggiunta una tolleranza 5%. Il picco cresce ancora di più. Richieste e report dei livelli sono in reference/. Cambiare h nel GH ricalcola invece la sagoma nominale: non equivale a questo raffinamento a forma fissa.

### 35. Il picco locale non è ancora una tensione di progetto

Picchi 57,03,86,64,141,16 MPa. Ascissa=livelli di mesh, non spazio. Carichi e vincoli puntuali possono creare singolarità; incidono anche spigoli rientranti del bordo a gradini. Non scegliere il valore più comodo. Modellare area di contatto, distribuzione delle forze, collegamenti e raccordi, poi un nuovo studio di mesh. Per confronto con altro solutore riprodurre modello, vincoli, carichi e tipo elemento. La statica manuale verificata qui è indipendente ma non sostituisce un benchmark di tensioni con altro codice.

### 36. Step 10 · Salvare, esportare e preparare il dettaglio

Salvare una copia della definizione e conservare report HTML e JSON. Nel blocco di ottimizzazione controllare Threshold=.40 e usare clic destro sull’uscita Mesh M → Bake per trasferire la mesh in Rhino. Se si usa un ingresso Bake, collegare un Button momentaneo. La mesh è discretizzata, non un solido liscio certificato. Undo di Rhino annulla il Bake: provarlo su una copia. Una curva ricostruita/smussata cambia il pezzo e richiede nuova FEM. La centina può diventare piastra sagomata irrigidita o reticolare di profilati, ma queste scelte richiedono modelli e verifiche nuove.

### 37. Laboratorio a gruppi · una variabile alla volta

35 minuti, una copia del riferimento per gruppo. A:Volume=.25 e.40, invariati h,raggio,soglia. B:Volume=.30, Threshold=.35 e.50; rianalizzare ogni soglia e registrare eventuali errori di connessione senza forzare. C:h50, Radius3.6 per mantenere180 mm fisici; nuova ottimizzazione, diversa dallo studio a forma fissa. Consegnare massa,max|u| SLS,picco ULS sinistra,reazioni uplift,stato arresto e due limiti. Non sono forniti numeri inventati delle varianti: gli studenti devono calcolarli. Conservare errori e spiegazioni.

### 38. Prima di chiamarlo progetto: che cosa manca

È un caso didattico completo, non un esecutivo per una casa assegnata. Chiedere un dato mancante per ciascuno dei cinque controlli: sito/azioni; vincoli e attacchi; accuratezza locale; stabilità3D; produzione e collegamenti. Solo la copertina è illustrativa; le mappe vengono dal worker. Per uso reale servono verifiche applicabili e un modello di confronto. TopOptLab non approva automaticamente una struttura. Approfondimenti progetto acciaio JRC: https://eurocodes.jrc.ec.europa.eu/publications/eurocodes-background-applications-design-steel-buildings-worked-examples

### 39. Verifica dell’apprendimento

Risposte:1)F=1,55×3×1=4,65 kN.2)Alleggerire riduce il peso stabilizzante e aumenta la trattenuta richiesta sotto suzione.3)Il picco cresce: modellare contatto/attacco reale e rifare il confronto di mesh. Domande aggiuntive: Stock e Thickness hanno ruoli differenti ma qui valgono12 mm entrambi; Weight non è gammaQ; soglia cambia rigidezza e massa e richiede rianalisi. Rubrica:30%carichi/unità,25%modello/vincoli,25%lettura critica,20%riproducibilità/comunicazione. Non premiare una massa bassa con dati non verificabili.

### 40. Fonti, file e tracciabilità del caso

Fonti consultate il19settembre2026. NTC2018 §§2.5–2.6,3.3–3.4: https://www.gazzettaufficiale.it/eli/gu/2018/02/20/42/so/8/sg/pdf. Decreto: https://www.gazzettaufficiale.it/eli/id/2018/2/20/18A00716/sg . Per applicazioni reali consultare testo vigente e modifiche incluso DM 9 marzo 2023: https://www.gazzettaufficiale.it/eli/id/2023/03/22/23A01847/SG . Materiale: https://steelconstruction.info/topics/design/steel-material-properties. JRC acciaio: https://eurocodes.jrc.ec.europa.eu/publications/eurocodes-background-applications-design-steel-buildings-worked-examples. Geometria e valori climatici sono scelte didattiche originali. Risultati:reference/teaching_values.json,case-01..05.json e report.html. Codice di riproduzione in source/. Copertina generata ImageGen, prompt in FONTI_E_METODO.md; mappe realizzate dai dati FEM. Archivi GH verificati via SDK e griglia confrontata con il worker, non collaudo interattivo automatizzato.

## Valutazione suggerita

- 30%: carichi, combinazioni e conversioni dimensionali.
- 25%: giustificazione di geometria, vincoli e attacchi.
- 25%: interpretazione critica di massa, spostamenti, tensioni e mesh.
- 20%: riproducibilità del file, report e chiarezza della comunicazione.

Le varianti di gruppo non hanno numeri attesi precompilati: vengono calcolate dagli studenti. Un errore di connessione ben diagnosticato è un risultato didattico utile. Non premiare una geometria apparentemente leggera senza controlli.
