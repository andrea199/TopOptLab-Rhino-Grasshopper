# SPDX-License-Identifier: GPL-3.0-or-later
import copy,json,math
from pathlib import Path
CATALOG=json.loads(Path(__file__).with_name('materials.json').read_text())['materials']
def resolve(spec):
    preset=spec.get('preset','steel')
    if preset not in CATALOG:raise ValueError('Material preset must be steel or abs')
    data=copy.deepcopy(CATALOG[preset]);data['preset']=preset
    lm={'mm':1e-3,'m':1.0};fn={'N':1.0,'kN':1000.0}
    lu,fu=spec.get('length_unit','mm'),spec.get('force_unit','N')
    if lu not in lm or fu not in fn:raise ValueError('Supported units: mm or m; N or kN')
    for key in ['young_pa','poisson','density_kg_m3']:
        if key in spec:data[key]=float(spec[key]);data['notes'].append(key+' overridden by user')
    if any(not math.isfinite(data[k]) for k in ['young_pa','poisson','density_kg_m3']) or data['young_pa']<=0 or data['density_kg_m3']<=0 or not 0<=data['poisson']<=.49:raise ValueError('Invalid material properties')
    factor=float(spec.get('safety_factor',1.5))
    if not math.isfinite(factor) or factor<1:raise ValueError('Safety factor must be finite and >= 1')
    reference=None
    if preset=='abs':reference=data['reference_yield_pa']
    stock=float(spec.get('stock_thickness_mm',0))
    if not math.isfinite(stock) or stock<0:raise ValueError('Invalid stock thickness')
    if preset=='steel' and 0<stock<=16:reference=data['reference_yield_pa']
    if 'allowable_pa' in spec:
        allowable=float(spec['allowable_pa'])
        if not math.isfinite(allowable) or allowable<=0:raise ValueError('Invalid user allowable stress')
        data['notes'].append('Allowable stress supplied by user; not divided by safety factor again.')
    else:allowable=None if reference is None else reference/factor
    data.update(length_unit=lu,force_unit=fu,length_m=lm[lu],force_n=fn[fu],safety_factor=factor,
                young=data['young_pa']*lm[lu]**2/fn[fu],allowable=None if allowable is None else allowable*lm[lu]**2/fn[fu],
                allowable_status='not_available' if allowable is None else 'screening_only_not_code_verification')
    return data
