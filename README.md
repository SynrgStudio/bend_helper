# Bend Helper - Blender Extension

**Version 1.3.0** - Interactive multi-axis mesh bending with GPU handles

[![Blender](https://img.shields.io/badge/Blender-4.3+-orange.svg)](https://www.blender.org/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

---

## ✨ Features

### 🎨 GPU-Drawn Handles
- **Beautiful colored handles**: Red (X), Green (Y), Blue (Z) circles rendered directly in viewport
- **Proportional sizing**: Handles scale to 10% of object dimensions for consistent visibility
- **Visual feedback**: Handles grow and brighten when dragging
- **Clean rendering**: No ugly empties cluttering your viewport

### 🔄 Multi-Object Support (NEW in v1.3!)
- **Edit multiple objects independently**: Activate addon on as many objects as you want
- **Object-specific state**: Each object maintains its own bend angles, subdivisions, and settings
- **Smart handle visibility**: Handles only appear on the currently selected object (no confusion!)
- **Switch freely**: Click between objects to see/edit their individual bends

### 🎮 Persistent Interactive Mode
- **Always active**: Interactive mode stays ON while you adjust UI controls
- **Drag handles**: Click and drag colored handles in viewport to bend interactively
- **UI interaction**: Change subdivisions, reset, or adjust sliders without exiting mode
- **ESC to exit**: Press ESC to exit interactive mode (or finish with Apply/Remove)

### ⚡ Intelligent Controls
- **Proportional handle sizing**: Handles size to 10% of perpendicular object dimensions
- **Accurate detection**: Improved 3D→2D raycast for precise handle clicking
- **Smooth dragging**: Real-time bend updates with visual feedback

---

## 📦 Installation

### Method 1: Manual Installation (Recommended for Development)

1. Copy the entire `bend_helper` folder to Blender's extensions directory:
   ```
   # Windows:
   C:\Users\[YOUR_USER]\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\

   # macOS:
   ~/Library/Application Support/Blender/4.5/extensions/user_default/

   # Linux:
   ~/.config/blender/4.5/extensions/user_default/
   ```

2. Open Blender → Edit → Preferences → Extensions
3. Find "Bend Helper" in the list
4. Enable the extension

### Method 2: Install from ZIP (For Distribution)

1. Create a ZIP file containing all files:
   - `__init__.py`
   - `blender_manifest.toml`
   - `LICENSE`
   - `README.md`

2. In Blender: Edit → Preferences → Extensions → Install from Disk
3. Select the ZIP file
4. Enable "Bend Helper"

---

## 🎯 How to Use

### Basic Workflow

1. **Select a mesh object** (cube, suzanne, any mesh)

2. **Open the Bend Helper panel**:
   - In 3D View, press `N` to open sidebar
   - Find "Bend Helper" tab

3. **Click "Activate"**:
   - Automatically adds subdivision (for smooth bending)
   - Creates 3 bend modifiers (X, Y, Z axes)
   - Spawns custom GPU handles in viewport
   - **Enters interactive mode automatically**

4. **Bend interactively**:
   - **Red handle** = Bend around X axis
   - **Green handle** = Bend around Y axis  
   - **Blue handle** = Bend around Z axis
   - **Click & drag any handle** to bend
   - Handles scale proportionally to object size (10% of perpendicular dimensions)

5. **Multi-object workflow** (NEW in v1.3!):
   - Activate addon on **Object A** → bend it
   - Select **Object B** → activate addon → bend it independently
   - Click back on **Object A** → handles reappear for Object A
   - Each object remembers its own bends, subdivisions, and state
   - Handles only visible on **currently selected object**

6. **Adjust settings** (while in interactive mode):
   - Change **Subdivisions** (1-6) for smoother/sharper bends
   - Click **"Refresh Subd"** to apply new subdivision level
   - Use **manual sliders** (X/Y/Z Axis) for precise control

7. **Exit interactive mode**:
   - Press **ESC** when done dragging
   - Or let it run in background (mode persists across UI interactions)

8. **Finalize** (choose one):
   - **"Reset All Bends"**: Set all angles back to 0 (modifiers stay, just reset to 0°)
   - **"Deactivate"**: Hide handles, exit mode (bends preserved on object)
   - **"Remove Bends"**: Delete all modifiers, return to original shape
   - **"Apply Bends"**: Bake modifiers into mesh permanently

---

## 🎮 Controls

| Action | Input |
|--------|-------|
| Start dragging handle | `Left Click` on colored circle |
| Drag to bend | `Mouse Move` while holding |
| Release handle | `Left Mouse Release` |
| Cancel drag | `Right Click` or `ESC` |
| Exit interactive mode | `ESC` (when not dragging) |
| Interact with UI | `Left Click` on panel (mode stays active) |
| Switch objects | `Left Click` on another object |

---

## ⚙️ Technical Details

### GPU Drawing System
- Uses `gpu.shader.from_builtin('UNIFORM_COLOR')` for rendering
- Draws circles with 32 segments for smooth appearance
- Handles scale to 10% of object's perpendicular dimensions
- Cross overlay for better visibility
- All drawing in `POST_VIEW` space (after geometry, before UI)

### Handle Detection
- Uses proper `region` and `rv3d` detection under mouse cursor
- Projects 3D handle positions to 2D screen space
- 50-pixel hit radius for easy clicking
- Only checks handles of currently selected object (no confusion)

### Persistent Modal
- Modal operator runs continuously once activated
- Returns `{'PASS_THROUGH'}` for all non-handle events
- Allows full UI interaction (buttons, sliders, menus)
- Only captures mouse when dragging handles

### Multi-Object Architecture (v1.3.0)
- `addon_data['objects']` dict stores per-object state
- Each object has independent: handles, modifiers, subdivisions, origins
- Draw handler filters by `context.active_object`
- Handles only visible on selected object
- State persists when switching between objects

### Subdivision Strategy
- Uses `SUBSURF` modifier with `subdivision_type='SIMPLE'`
- SIMPLE = maintains hard edges (no smoothing)
- Added BEFORE bend modifiers in stack
- Levels 3-4 recommended for best balance

---

## 🐛 Troubleshooting

**Handles not visible?**
- Make sure object is selected and "Activate" was clicked
- Check that 3D viewport is visible
- Try moving camera to see handles around object
- Handles only appear on **currently selected** object

**Handles too small/large?**
- Handles auto-scale to 10% of object's perpendicular dimensions
- Minimum size: 0.15 units for very small objects
- Size adapts when object is scaled/modified

**Dragging not working?**
- Ensure you clicked directly on colored circle
- Hit radius is generous (50px) but mouse must be close
- Try clicking the center cross
- Make sure object is still selected

**Bends look jagged?**
- Increase **Subdivisions** to 4 or 5
- Click **"Refresh Subd"** after changing
- Remember: higher = smoother but heavier

**Can't switch between objects?**
- Fixed in v1.3.0! Each object maintains independent state
- Click any object to see its handles (if addon is active on it)
- Handles hide when you deselect the object

**Multiple objects showing handles?**
- Fixed in v1.3.0! Only selected object shows handles
- Other objects keep their bends but handles are hidden

---

## 🔧 Developer Notes

### Key Functions
- `draw_handles_callback()`: GPU drawing, filters by active object
- `get_object_data(obj)`: Get/create per-object state
- `BENDHELPER_OT_InteractiveBend.modal()`: Persistent modal loop
- `check_handle_hit()`: 3D→2D raycast (active object only)

### Global State (`addon_data`)
```python
{
    'objects': {
        'Cube': {
            'handles': {axis: Object},
            'modifiers': {axis: Modifier},
            'subdivisions': {'ALL': Modifier},
            'origins': {axis: Object},
            'handle_positions': {axis: Vector}
        },
        'Sphere': { ... }  # Independent state
    },
    'dragging': bool,
    'drag_axis': str,  # 'X', 'Y', or 'Z'
    'drag_object': str,  # Name of object being dragged
    'mouse_start': (x, y),
    'initial_angle': float,
    'draw_handler': handler  # GPU draw handler reference (single, global)
}
```

---

## 📝 Changelog

### v1.3.0 (Current - Extension Release)
- ✅ **Multi-object support**: Edit multiple objects independently
- ✅ **Smart handle visibility**: Handles only on selected object
- ✅ **Proportional handle sizing**: 10% of perpendicular object dimensions
- ✅ **Extension format**: Now a proper Blender 4.3+ extension
- ✅ **Improved object state management**: Each object fully independent
- ✅ **Better pivot calculations**: Uses bounding box center, not origin
- ✅ Fixed: Handle size consistency across different object scales
- ✅ Fixed: Deactivate/Remove/Apply operations work correctly per-object

### v1.2.0
- ✅ Custom GPU-drawn handles (colored circles)
- ✅ Persistent interactive mode
- ✅ Fixed UI interaction while modal active
- ✅ Improved handle detection with proper region/rv3d
- ✅ "Refresh Subd" button with clear label
- ✅ Better visual feedback (handles scale/brighten)

### v1.1.0
- Interactive mode with draggable empties
- Subdivision support
- Multi-axis bending

### v1.0.0
- Initial release
- Basic bend functionality

---

## 📄 License

GNU General Public License v3.0 or later

This extension is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](LICENSE) file for full text.

---

## 🤝 Contributing

Found a bug? Have a feature request? Contributions are welcome!

1. Report issues on the issue tracker
2. Submit pull requests with improvements
3. Share your creations made with Bend Helper!

---

## 💡 Tips & Tricks

- **Combine bends**: Use X, Y, and Z together for complex curves
- **Animate bends**: Keyframe the bend angle properties for animation
- **Non-destructive**: Keep modifiers unapplied for easy tweaking
- **Duplicate bent objects**: Applied bends can be duplicated with `Shift+D`
- **Works with any mesh**: Cubes, cylinders, custom models, all work!

---

## ⚠️ Known Limitations

- Shape keys are not supported (will be disabled when addon activates)
- Very high subdivision levels (5-6) may slow down viewport
- Handles position based on bounding box (may not align with custom origins)
- Undo/Redo may require reactivating addon

---

**Made with ❤️ for the Blender community**

*Bend Helper v1.3.0 - Happy Bending! 🎨*

Feel free to improve this addon! Key areas for enhancement:
- Add undo/redo support for interactive dragging
- Implement handle snapping (15°, 30°, 45° increments)
- Add visual angle indicator (arc/text)
- Support for multiple objects simultaneously

---

**Enjoy bending! 🎨**
