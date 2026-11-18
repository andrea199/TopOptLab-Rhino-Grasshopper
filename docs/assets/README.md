# README visual assets

- `topoptlab-icon.png`: selected concept A, generated with OpenAI image_gen for TopOptLab. A symbolic brand mark, not a numerical simulation result or a McNeel logo.
- `topoptlab-optimization.gif`: actual density snapshots from this repository's unmodified `tool/worker.py` and `tool/sample_problem.py`, running `example(80, 40, 100)`. The same plate-with-hole example is used by the native Example Geometry component. Created on 18 November 2026.

The GIF has 21 frames (iterations 0–100 at intervals of five), a grid of 80 × 40 cells, a target volume fraction of 0.45, a central downward load and the original example's supports/preserved regions. Its navy-to-turquoise scale encodes density from zero to one. Playback is accelerated, with longer pauses at the first and last frames. The animation is not a convergence or physical-design qualification claim.

The recorded run returned status `completed`, volume fraction 0.45, compliance 2.3493412649480263e-05 and normalized equilibrium error 8.267041565201971e-13. These figures describe this educational example only. The file is 960 × 650 pixels and 717,832 bytes.

Solver SHA-256 at generation: `b331ea1bb2ab0ea94304ca597fa2a367fb9e32d5c1727d796369d0e087ff253a`.

Both assets are stored in the repository so GitHub can display the README without external image hosting.
