# Material provenance

Data and sources: tool/materials.json, retrieved 2026-09-18.

Structural steel E=210 GPa and nu=0.30:
[Steel Construction](https://steelconstruction.info/topics/design/steel-material-properties/).
Density 7850 kg/m³:
[steel design guide](https://www.steelconstruction.info/images/8/85/CFT_Design_Guide_March_2014.pdf).
S235 reference yield 235 MPa is limited to stock thickness <=16 mm:
[Tata Steel](https://products.tatasteelnederland.com/products/engineering/hot-rolled/structural-steel).
Confirm the delivered grade/product certificate.

ABS GP-22 E=2300 MPa, density 1040 kg/m³ and typical tensile yield 45 MPa at 23 °C:
[INEOS Styrolution](https://www.ineos-styrolution.com/Product/Terluran_TERLURAN-GP-22_SKU300600120827.html).
Nu=0.35 is an explicit modeling assumption; the cited sheet does not supply it.
Injection-molding reference data do not establish printed-ABS or creep performance.

Reference yield divided by the chosen factor provides screening only. JSON input
also supports user allowable stress/property overrides, recorded in the report.
