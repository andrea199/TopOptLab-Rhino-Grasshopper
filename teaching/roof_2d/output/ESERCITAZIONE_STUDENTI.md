# Esercitazione: centina metallica di un tetto

**Gruppo:** __________  **Studenti:** __________  **Data:** __________

## Obiettivo

Impostare e controllare una FEM piana, eseguire l'ottimizzazione, rianalizzare la geometria estratta e motivare una scelta. Il modello è una piastra di acciaio da 12 mm, con luce 6000 mm, interasse tributario 3000 mm, cinque casi di carico già predisposti.

## Prima di calcolare

1. Disegna A e B e scrivi quali spostamenti sono impediti. Che cosa significa un appoggio bilaterale sotto vento?
2. Calcola la massa del dominio pieno e la forza su ciascuna delle sei stazioni allo SLS.
3. Calcola Ay e By del pieno nel caso SLS uniforme con peso proprio.
4. Distingui spessore FEM, Stock thickness, interasse delle centine e Cell size.
5. Prevedi dove resterà materiale e come cambieranno gli ancoraggi alleggerendo la centina.

## Esecuzione

Apri `case/roof_geometry_mm.3dm` e `case/roof_2d_classroom.gh`. Mantieni i valori iniziali e premi RUN nelle fasi 01, 02, 03 in ordine, aspettando ogni completamento. Review sceglie solo cosa mostrare. Salva una copia del file e dei report.

## Tabella da consegnare

| Quantità | Riferimento pieno | Densità ottimizzata | Parte estratta | Variante |
| --- | --- | --- | --- | --- |
| h [mm], Radius [celle] | | | | |
| Volume, Threshold | | | | |
| Massa [kg] | | | | |
| Max |u| SLS [mm] | | | | |
| Max von Mises ULS sinistra [MPa] | | rilassata, da distinguere | | |
| Ay, By uplift [kN] | | | | |
| Iterazioni e stato di arresto | FEM | | rianalisi | |
| Connessioni / attacchi conservati | | | | |

## Variante assegnata

- Gruppo A: Volume 0,25 e 0,40; mantieni gli altri parametri.
- Gruppo B: Threshold 0,35 e 0,50; riesegui la verifica per entrambe le soglie.
- Gruppo C: h=50 mm, Radius=3,6 celle per conservare il filtro fisico da 180 mm; riesegui tutte le fasi.

Una variabile alla volta. Se la forma non è verificabile, registra messaggio e causa: non riutilizzare un risultato precedente.

## Discussione richiesta

1. La tua variante è più leggera? Quanto cambia lo spostamento?
2. Perché il peso della centina modifica il caso di sollevamento?
3. Quale differenza c'è tra rilanciare l'ottimizzazione con h più piccolo e raffinare la stessa parte estratta?
4. Nei dati inclusi il picco cresce passando da h=100 a h=25: quale dettaglio del modello approfondiresti?
5. Quali dati e verifiche mancano per impiegare il pezzo su una casa reale?

Consegna: file `.gh`, tabella compilata, una figura con legenda/unità e una pagina di conclusioni. Specifica versione del software e percorso dei report. Non definire la centina “verificata secondo norma” sulla base di questa sola esercitazione.
