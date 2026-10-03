# SPDX-License-Identifier: GPL-3.0-or-later
"""MMA state and scaled inequalities for explicit engineering constraints."""
import numpy as np
from mmapy import mmasub, kktcheck


class MMAUpdate:
    def __init__(self, model, x, constraint_count):
        self.n=len(x);self.m=constraint_count;self.iteration=0
        self.xmin=np.full((self.n,1),.001);self.xmax=np.ones((self.n,1))
        if np.min(x)<.001:raise ValueError('Increase Volume: constrained optimization needs design density >= 0.001')
        self.old1=x[:,None].copy();self.old2=self.old1.copy()
        self.low=self.xmin.copy();self.upp=self.xmax.copy();self.dual=None
        self.scaling=None
        self.a=np.zeros((self.m,1));self.c=np.full((self.m,1),1000.);self.d=np.ones((self.m,1))

    def step(self,x,cost,gradient,values,jacobian):
        self.iteration+=1
        if self.scaling is None:self.scaling=np.maximum(1.,np.abs(values))
        with np.errstate(divide="raise",invalid="raise",over="raise"):
            result=mmasub(self.m,self.n,self.iteration,x[:,None],self.xmin,self.xmax,self.old1,self.old2,
                      cost,gradient[:,None],(values/self.scaling)[:,None],jacobian/self.scaling[:,None],self.low,self.upp,1.,self.a,self.c,self.d,move=.15)
        candidate=result[0].ravel()
        if not np.isfinite(candidate).all() or np.any(candidate<.001-1e-10) or np.any(candidate>1+1e-10):
            raise ValueError('MMA returned invalid design values')
        self.dual=result[1:9];self.low,self.upp=result[9:11]
        self.old2=self.old1.copy();self.old1=x[:,None].copy()
        return np.clip(candidate,.001,1.)

    def kkt(self,x,gradient,values,jacobian):
        if self.dual is None:return None
        _,_,maximum=kktcheck(self.m,self.n,x[:,None],*self.dual,self.xmin,self.xmax,gradient[:,None],(values/self.scaling)[:,None],jacobian/self.scaling[:,None],1.,self.a,self.c,self.d)
        return float(maximum)


def inequalities(model,rho,evaluations,gravity):
    values=[float(rho.mean()/model.target-1)]
    jacobian=[model.dv/(model.n*model.target)]
    # Self-weight keeps its material budget, within a very small normalized band.
    if gravity:
        values.append(float(1-rho.mean()/model.target-1e-6));jacobian.append(-jacobian[0])
    for evaluation in evaluations:
        values.extend(evaluation['values']);jacobian.extend(evaluation['jacobian'])
    values=np.asarray(values);jacobian=np.asarray(jacobian)
    if not np.isfinite(values).all() or not np.isfinite(jacobian).all():raise ValueError('Nonfinite engineering constraint')
    return values,jacobian



def optimize_constrained(model, cases, limits, evaluate, progress):
    from design_limits import evaluate_limits
    from worker import number,integer
    settings=model.request['settings'];gravity=any(c['body'] is not None for c in cases)
    x=model.initial();previous_c=None;previous_rho=None;stable=0;best=None;mma=None
    tol=number(settings.get('objective_tolerance',.001),'objective tolerance',1e-8,.1)
    dtol=number(settings.get('design_tolerance',.01),'design tolerance',1e-6,.2)
    window=integer(settings.get('convergence_window',5),'convergence window',2,50)
    minimum=integer(settings.get('minimum_iterations',10),'minimum iterations',1,1000)
    history=[];reason='iteration_limit';last_kkt=None;failure=None
    for iteration in range(model.iterations+1):
        model.engine.check_cancel();rho=model.density(x);combined,responses=evaluate(rho)
        evaluations=[evaluate_limits(model,case,rho,res,limits,True) for case,res in zip(cases,responses)]
        values,jacobian=inequalities(model,rho,evaluations,gravity)
        if iteration==0:baseline=combined['compliance'];mma=MMAUpdate(model,x,len(values))
        gradient=combined['gradient']/baseline
        last_kkt=mma.kkt(x,gradient,values,jacobian)
        violation=float(max(0,values.max()));feasible=violation<=limits['tolerance']
        change=None if previous_c is None else abs(combined['compliance']-previous_c)/max(abs(previous_c),1e-30)
        dchange=None if previous_rho is None else float(np.max(abs(rho-previous_rho)))
        row=dict(iteration=iteration,compliance=combined['compliance'],volume=float(rho.mean()),objective_change=change,
                 design_change=dchange,max_constraint_violation=violation,feasible=feasible,kkt_residual=last_kkt)
        history.append(row)
        # A feasible design always wins over an infeasible lower-compliance design.
        key=(0,combined['compliance']) if feasible else (1,violation,combined['compliance'])
        if best is None or key<best[0]:best=(key,rho.copy(),combined,responses,iteration,violation,last_kkt)
        progress(rho,combined,responses,iteration,baseline,history,dict(max_constraint_violation=violation,feasible=feasible))
        stationary=last_kkt is not None and last_kkt<=max(.001,limits['tolerance'])
        stable=stable+1 if iteration>=minimum and feasible and stationary and change is not None and change<=tol and dchange<=dtol else 0
        if stable>=window:
            reason='converged';best=(key,rho.copy(),combined,responses,iteration,violation,last_kkt);break
        previous_c=combined['compliance'];previous_rho=rho.copy()
        if iteration<model.iterations:
            model.engine.check_cancel()
            try:x=mma.step(x,combined['compliance']/baseline,gradient,values,jacobian)
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as error:
                # Preserve a valid FEM state for inspection; never report optimizer failure as convergence.
                reason='optimizer_failed';failure=str(error);break
            model.engine.check_cancel()
    _,rho,combined,responses,iteration,violation,returned_kkt=best
    return rho,combined,responses,iteration,baseline,history,reason,dict(method='MMA',feasible=violation<=limits['tolerance'],
        max_constraint_violation=violation,kkt_residual=returned_kkt,numerical_failure=failure,
        constraint_scaling='fixed initial row scaling; feasibility checked in original normalized constraints',aggregation='conservative KS upper bound',
        stress_model='sqrt(rho) times solid-material von Mises; relaxed design surrogate',density_lower_bound=.001,
        volume_policy='fixed budget within normalized 1e-6 band' if gravity else 'upper bound',
        note='A feasible relaxed density design is not a verified final shape.')
