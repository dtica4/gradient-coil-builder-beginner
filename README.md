# Gradient Coil Builder

Teaching website for the gradient coil subsystem of the 32 mT portable MRI (BioMed-EM Lab, SUTD).

**Live site:** https://dtica4.github.io/gradient-coil-builder-beginner/

Students learn what a gradient coil does, then design, build and test the X, Y and Z coils:
the coils are designed in pyCoilGen, their wire paths are cut as grooves into flat 3D-printed
plates, and the plates are wrapped into tubes and nested.

## What's in this repository

| Folder / file | What it holds |
|---|---|
| `index.html` | The website page |
| `css/style.css` | Colours, fonts and layout |
| `js/config.js` | Coil data used by the viewer and the lab |
| `js/main.js` | Page behaviour: step checkboxes, result tabs |
| `js/lab.js` | The "from current to position" interactive lab |
| `js/viewer.js` | The 3D viewer (Three.js) |
| `js/i18n.js` | The language switch (English, 中文, Español) |
| `js/i18n/zh.js`, `js/i18n/es.js` | Chinese and Spanish text, one entry per text block |
| `models/` | Compressed coil models for the viewer (plates and wire, as flat-sheet coordinates) |
| `scripts/` | The six pyCoilGen scripts (design + summary for X, Y, Z) |
| `CAD/wires/` | Wire-only STL of each coil, from pyCoilGen |
| `CAD/plates/` | The 12 grooved plates to print (STEP), 4 per coil |
| `CAD/cover/` | The PLA gradient cover that holds the three coils (STEP) |
| `images/` | Build photos; `images/results/` holds the test plots; `images/brand/` the team logo |

## Common edits

- **Change text on the page:** edit `index.html`. Sections are marked with comments such as `<!-- 3. BUILD -->`.
- **Fill in a "to be added" item:** search `index.html` for `tbd`.
- **Change a translation:** every text block in `index.html` has an id such as `data-i18n="t127"`. Find the same id in `js/i18n/zh.js` or `js/i18n/es.js` and edit its text. If you change the English text of a block, update its Chinese and Spanish entries too; a block with no entry simply shows in English.

After editing, upload the changed file (Add file → Upload files) and commit. The site updates within about a minute.

## Preview on your own computer

The 3D viewer needs a small local web server (opening `index.html` directly will not load the models):

```
python -m http.server 8000
```

Then open http://localhost:8000 in a browser.

## Credits

Coil designs made with [pyCoilGen](https://github.com/kev-m/pyCoilGen); inductance from FastHenry2.
3D viewer built with [Three.js](https://threejs.org/).
