# Marquise brand source

The Marquise mark is a corner marquee seen from the street: two sign faces meet at a corner, with a lit strip along their underside. Agreed in #421. Later brand work takes its assets from this folder.

```
        lit face  |  shadow face
        (lilac)   |  (indigo)
   ---------------+---------------
        light strip (amber / yellow)
```

## Files

| File | Use | viewBox |
|---|---|---|
| `mark-light.svg` | Main mark on light backgrounds (amber strip) | `-92 -36 184 83.52` |
| `mark-dark.svg` | Main mark on dark backgrounds (yellow strip) | `-92 -36 184 83.52` |
| `mark-one-colour.svg` | One-colour mark (`currentColor`), footer | `-92 -36 184 88.52` |
| `favicon.svg` | Favicon for 16 to 32 px; strip turns yellow under `prefers-color-scheme: dark` | `-76 -64.8 152 152` |

The interface app serves a copy of `favicon.svg` and a 180×180 `apple-touch-icon.png` rendered from it.

## Geometry

Both faces meet on the vertical axis `x = 0`. Each face is mirrored left (lit) and right (shadow).

- **Main mark.** Faces run from the corner (`0,-32` to `0,32`) out to the edges (`±88,-17` to `±88,17`). The strip hangs under each face: `±88,17 0,32 0,43.52 ±88,23.12`.
- **One-colour mark.** Same faces. The strip floats below them so it still reads in a single colour: `±88,19.66 0,37 0,48.52 ±88,25.78`. The viewBox is 5 units taller.
- **Favicon.** A chunkier cut for small sizes. Faces run from `0,-40`/`0,40` to `±74,-22`/`±74,22`. The strip is thicker: `±74,22 0,40 0,62.4 ±74,34.32`. The viewBox is square.

## Light strip contrast rule

Yellow cannot reach 3:1 on white. The strip is amber `#e07a00` (3.02:1) on light backgrounds and yellow `#fcd34d` on dark ones.

## Palette alternatives

Saved, not used now. Lit / shadow / strip on light / strip on dark:

| Name | Lit | Shadow | Strip (light) | Strip (dark) |
|---|---|---|---|---|
| **lilac indigo** (current) | `#a78bfa` | `#6366f1` | `#e07a00` | `#fcd34d` |
| sunset | `#ff7a59` | `#e5386d` | `#e07a00` | `#ffc94a` |
| peach rose | `#ffa07a` | `#ef6f8e` | `#e07a00` | `#ffe08a` |
| coral plum | `#ff6f61` | `#b8336a` | `#e07a00` | `#ffd166` |
| tangerine | `#ff9f1c` | `#f2542d` | `#e07a00` | `#fff1c1` |
| candy | `#5e9cff` | `#06d6a0` | `#e07a00` | `#ffd166` |
| sky blue | `#56cfe1` | `#4e8fde` | `#e07a00` | `#ffd166` |
| mint sea | `#3ccfb4` | `#168aad` | `#e07a00` | `#ffd166` |
| lagoon | `#2ec4b6` | `#ff6b6b` | `#e07a00` | `#ffbf69` |
| berry | `#7f5af0` | `#d63af9` | `#ff5781` | `#ff8fab` |
| grape pink | `#9b5de5` | `#f15bb5` | `#e07a00` | `#fee440` |
| indigo violet | `#4361ee` | `#7209b7` | `#e07a00` | `#f7b801` |
