// Site settings. Edit these values, then upload this file again.

// Show the measured test results (13–15 Oct 2026) in the Test section?
// Keep this false until the lab agrees the measured numbers can be public.
export const SHOW_MEASURED = false;

// Coil data used by the viewer and the lab. Values from the pyCoilGen designs.
export const COILS = {
  x: { name: 'X coil', diameter: 119.8, efficiency: 1.053, plates: 4,
       caption: 'X coil: four plates, one saddle-shaped wire loop in each.' },
  y: { name: 'Y coil', diameter: 126.2, efficiency: 1.015, plates: 4,
       caption: 'Y coil: same pattern as X, turned a quarter turn around the bore.' },
  z: { name: 'Z coil', diameter: 132.6, efficiency: 1.282, plates: 4,
       caption: 'Z coil: plates TL, TR, BL and BR. The wire winds around the bore many times as a double helix.' },
};

// Measured results, shown only when SHOW_MEASURED is true.
export const MEASURED = {
  date: '13–15 Oct 2026',
  rows: [
    { coil: 'X', eff: '1.048', design: '1.053', diff: '−0.5 %', grad: '5.24', lin: '2.9 %', linClean: '1.4 %' },
    { coil: 'Y', eff: '0.980', design: '1.015', diff: '−3.5 %', grad: '4.90', lin: '3.1 %', linClean: '1.4 %' },
    { coil: 'Z', eff: '1.290', design: '1.282', diff: '+0.6 %', grad: '6.45', lin: '2.7 %', linClean: '1.6 %' },
  ],
};
