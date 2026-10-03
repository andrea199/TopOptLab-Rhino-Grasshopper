# SPDX-License-Identifier: GPL-3.0-or-later
"""Normalized finite-domain density filter without a cell-by-neighbor sparse matrix."""
import numpy as np
from scipy.fft import rfftn, irfftn, next_fast_len
from scipy.sparse.linalg import LinearOperator


class GridDensityFilter(LinearOperator):
    """Same cone weights/subset normalization as upstream, with exact transpose action."""
    def __init__(self, grid_shape, variable_ids, radius):
        self.grid_shape=tuple(int(v) for v in grid_shape)
        self.ids=np.asarray(variable_ids,dtype=np.int64)
        self.radius=float(radius)
        if len(self.grid_shape)!=3 or any(v<1 for v in self.grid_shape) or not np.isfinite(radius) or not 1<=radius<=64:
            raise ValueError('Invalid density filter shape/radius')
        if self.ids.ndim!=1 or len(self.ids)==0 or np.any(self.ids<0) or np.any(self.ids>=np.prod(self.grid_shape)) or len(np.unique(self.ids))!=len(self.ids):
            raise ValueError('Invalid variable cell indices')
        reach=int(np.ceil(radius))-1
        coords=np.arange(-reach,reach+1,dtype=float)
        a,b,c=np.meshgrid(coords,coords,coords,indexing='ij')
        kernel=np.maximum(0,radius-np.sqrt(a*a+b*b+c*c))
        self.fft_shape=tuple(next_fast_len(n+k-1,real=True) for n,k in zip(self.grid_shape,kernel.shape))
        self.kernel_fft=rfftn(kernel,s=self.fft_shape,workers=1)
        self.crop=tuple(slice(reach,reach+n) for n in self.grid_shape)
        mask=np.zeros(self.grid_shape);mask.ravel()[self.ids]=1
        self.normalizer=self._convolve(mask).ravel()[self.ids]
        if np.any(self.normalizer<=0):raise ValueError('Empty density filter row')
        self.storage_bytes=self.ids.nbytes+self.kernel_fft.nbytes+self.normalizer.nbytes
        super().__init__(dtype=np.dtype(float),shape=(len(self.ids),len(self.ids)))

    def _convolve(self, grid):
        spectrum=rfftn(grid,s=self.fft_shape,workers=1)
        spectrum*=self.kernel_fft
        return irfftn(spectrum,s=self.fft_shape,workers=1)[self.crop]

    def _matvec(self, values):
        values=np.asarray(values,dtype=float).reshape(-1)
        grid=np.zeros(self.grid_shape);grid.ravel()[self.ids]=values
        return self._convolve(grid).ravel()[self.ids]/self.normalizer

    def _rmatvec(self, values):
        values=np.asarray(values,dtype=float).reshape(-1)
        grid=np.zeros(self.grid_shape);grid.ravel()[self.ids]=values/self.normalizer
        return self._convolve(grid).ravel()[self.ids]


class GroupAverage(LinearOperator):
    """Self-adjoint group averaging with O(n) storage, including long extrusions."""
    def __init__(self, labels):
        _,self.labels,self.counts=np.unique(np.asarray(labels),return_inverse=True,return_counts=True)
        super().__init__(dtype=np.dtype(float),shape=(len(self.labels),len(self.labels)))
    def _matvec(self, values):
        sums=np.bincount(self.labels,weights=np.asarray(values).ravel(),minlength=len(self.counts))
        return (sums/self.counts)[self.labels]
    def _rmatvec(self, values):
        return self._matvec(values)
