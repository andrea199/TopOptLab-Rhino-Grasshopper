# Riproduzione numerica

Usare Python della `.venv` del progetto TopOptLab-Rhino. Esempio PowerShell, adattando entrambi i percorsi:

```powershell
& "C:/percorso/TopOptLab-Rhino/.venv/Scripts/python.exe" "C:/lezione/source/reproduce.py" --project-root "C:/percorso/TopOptLab-Rhino" --output "C:/lezione/nuova_prova"
```

La cartella di output deve essere nuova. Lo script esegue pieno, ottimizzazione, verifica e raffinamento della stessa parte estratta. Non installa dipendenze e non modifica il plugin.

`roof_model.py` contiene geometria e ipotesi in mm/N/MPa. `RoofExample.cs` genera e verifica gli archivi GH usando RhinoCommon, Grasshopper, GH_IO, Newtonsoft.Json e TopoptLab.GH.gha. Richiede l'SDK di Rhino e avvia RhinoCore senza finestra; i tre primi argomenti sono le cartelle System di Rhino, Grasshopper, e del GHA, il quarto è una cartella con `roof_request_h100.json`. Il caso compilato e i risultati sono già forniti: compilare il generatore non è necessario per la lezione.

Gli script sono distribuiti con licenza GPL-3.0-or-later, come il progetto. La licenza completa è in LICENSE.
