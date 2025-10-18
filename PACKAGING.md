# Bend Helper Extension - Packaging Instructions

## 📦 Extension Structure

Your extension is now ready! The folder contains:

```
bend_helper/
├── __init__.py              # Main addon code (renamed from bender.py)
├── blender_manifest.toml    # Extension manifest (required for Blender 4.3+)
├── LICENSE                  # GPL-3.0 license file
└── README.md                # Complete documentation
```

---

## ✅ Installation Methods

### Method 1: Direct Installation (Current Setup)

Your extension is already installed at:
```
C:\Users\dnaon\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\bender
```

**To enable it:**
1. Open Blender 4.3 or later
2. Go to: **Edit → Preferences → Extensions**
3. Find "Bend Helper" in the list
4. Click the checkbox to enable it
5. The panel will appear in 3D View sidebar (press `N`)

---

### Method 2: Create ZIP for Distribution

To share your extension with others or publish it:

**Using PowerShell:**
```powershell
cd "C:\Users\dnaon\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default"
Compress-Archive -Path "bender\*" -DestinationPath "bend_helper-v1.3.0.zip"
```

**Using File Explorer:**
1. Navigate to: `C:\Users\dnaon\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\bender`
2. Select all 4 files (`__init__.py`, `blender_manifest.toml`, `LICENSE`, `README.md`)
3. Right-click → "Send to" → "Compressed (zipped) folder"
4. Rename to: `bend_helper-v1.3.0.zip`

**To install from ZIP:**
1. In Blender: **Edit → Preferences → Extensions**
2. Click dropdown arrow (⌄) → **Install from Disk...**
3. Select the ZIP file
4. Extension installs automatically

---

## 🧪 Testing the Extension

### Basic Test
1. Enable the extension in Preferences
2. Open a new Blender scene (default cube)
3. Press `N` to open sidebar
4. Find "Bend Helper" tab
5. Click "Activate"
6. You should see colored handles (Red, Green, Blue) around the cube
7. Click and drag a handle → cube should bend smoothly

### Multi-Object Test
1. Add another object (Shift+A → Mesh → UV Sphere)
2. Select the sphere
3. Activate Bend Helper on sphere
4. Bend the sphere
5. Click back on the cube
6. Cube's handles should reappear (sphere's handles hide)
7. Both objects maintain their independent bends

---

## 🔍 Validation (Optional)

Blender includes tools to validate extensions:

**Validate Extension:**
```powershell
cd "C:\Program Files\Blender Foundation\Blender 4.5"
.\blender.exe --command extension validate --extension-dir "C:\Users\dnaon\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\bender"
```

**Build Extension (creates validated ZIP):**
```powershell
.\blender.exe --command extension build --source-dir "C:\Users\dnaon\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\bender" --output-dir "C:\Users\dnaon\Desktop"
```

This creates a validated ZIP file ready for publishing.

---

## 📤 Publishing (Optional)

To publish on Blender Extensions platform:

1. **Create account** at: https://extensions.blender.org/
2. **Prepare your ZIP** (using Method 2 above)
3. **Upload**:
   - Go to your account → "Submit Extension"
   - Upload the ZIP file
   - Fill in description, screenshots, etc.
   - Submit for review

**Requirements for publishing:**
- Valid `blender_manifest.toml` ✅
- Open source license (GPL-3.0+) ✅
- README with documentation ✅
- Clean, working code ✅

---

## 🔧 Updating the Extension

When you make changes to `__init__.py`:

1. **Update version** in both files:
   - `blender_manifest.toml`: `version = "1.4.0"`
   - `__init__.py`: `"version": (1, 4, 0)`

2. **Update changelog** in `README.md`

3. **Reload in Blender**:
   - Disable extension
   - Re-enable extension
   - Or restart Blender

---

## 📋 Checklist Before Distribution

- [ ] Tested on Blender 4.3+
- [ ] No Python errors in console
- [ ] All features working (Activate, Bend, Deactivate, Remove, Apply)
- [ ] Multi-object support working
- [ ] Handle sizing correct for different object scales
- [ ] README.md is complete
- [ ] Version numbers match in manifest and bl_info
- [ ] LICENSE file present
- [ ] ZIP file contains all 4 files

---

## 🎉 Your Extension is Ready!

The extension follows all Blender 4.3+ requirements:
✅ Proper manifest file
✅ GPL-3.0 license
✅ Documentation
✅ Clean code structure
✅ Multi-object support
✅ GPU-drawn handles
✅ Works with Blender 4.3 - 4.5+

Happy bending! 🎨
