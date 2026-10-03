# SPDX-License-Identifier: GPL-3.0-or-later
"""Same 12 x 6 plate used by the native Example Geometry component."""


def example(nx=48, ny=24, iterations=80):
    h = 12 / nx
    if abs(ny * h - 6) > 1e-10:
        raise ValueError('The example aspect ratio is 2:1')
    active, solid = [], []
    for col in range(nx):
        for row in range(ny):
            x, y = (col + .5) * h, (ny - row - .5) * h
            if (x - 6) ** 2 + (y - 3) ** 2 < 1:
                continue
            e = col * ny + row
            active.append(e)
            if x < 1 or x > 11:
                solid.append(e)
    return dict(schema='topoptlab-gh-request-v1', job_id='reference',
                domain=dict(nx=nx, ny=ny, cell=h, origin=[0, 0],
                            frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], active=active, solid=solid),
                supports=[dict(nodes=[ny], fix_x=True, fix_y=True),
                          dict(nodes=[nx * (ny + 1) + ny], fix_x=False, fix_y=True)],
                loads=[dict(nodes=[(nx // 2) * (ny + 1)], force=[0, -.001])],
                settings=dict(volume=.45, iterations=iterations, radius=2.4, young=1, poisson=.3, thickness=1))
