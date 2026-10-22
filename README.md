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
| `js/config.js` | **Settings you are most likely to edit** (see below) |
| `js/main.js` | Page behaviour: step checkboxes, measured-results switch |
| `js/lab.js` | The "from current to position" interactive lab |
| `js/viewer.js` | The 3D viewer (Three.js) |
| `models/` | Compressed coil models for the viewer (plates and wire, as flat-sheet coordinates) |
| `scripts/` | The six pyCoilGen scripts (design + summary for X, Y, Z) |
| `CAD/wires/` | Wire-only STL of each coil, from pyCoilGen |
| `CAD/plates/` | The 12 grooved plates to print (STEP), 4 per coil |

## Common edits

- **Show the measured test results:** open `js/config.js` and change
  `SHOW_MEASURED = false` to `true`. Only do this once the lab agrees the numbers can be public.
- **Change text on the page:** edit `index.html`. Sections are marked with comments such as `<!-- 3. BUILD -->`.
- **Fill in a "to be added" item:** search `index.html` for `tbd`.

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
