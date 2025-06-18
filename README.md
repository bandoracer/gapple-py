# Car Customization Tool

A comprehensive system for visualizing and testing car modifications including wheels, tires, suspension geometry, ride height, and fitment. Built with Blender integration and a standalone wheel/tire processor.

## Project Overview

This project consists of two main components:

1. **Standalone Wheel & Tire Processor** - A desktop application for managing wheel/tire inventory and specifications
2. **Blender Addon** - Professional 3D tools for car customization and visualization

The goal is to create a tool that lets you test visual customizations like:
- Wheel changes and fitment
- Wheel spacing/offset adjustments  
- Ride height modifications
- Tire size effects
- Suspension geometry visualization
- Real-world fitment validation

## Project Structure

```
car-customization-tool/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── standalone_app/
│   ├── wheel_processor.py            # Main standalone application
│   ├── wheel_database.json           # Database storage
│   └── assets/                       # 3D models, images, etc.
├── blender_addon/
│   ├── __init__.py                   # Addon initialization
│   ├── wheel_tire_system.py         # Main Blender addon code
│   ├── operators/                    # Blender operators
│   ├── panels/                       # UI panels
│   └── utils/                        # Utility functions
├── docs/
│   ├── API.md                        # API documentation
│   ├── user_guide.md                 # User guide
│   └── development.md                # Development notes
└── tests/
    ├── test_wheel_specs.py           # Unit tests
    └── test_blender_integration.py   # Integration tests
```

## What We've Built So Far

### Standalone Application (`wheel_processor.py`)

**Features Implemented:**
- ✅ Wheel inventory management with real-world specifications
- ✅ Tire size calculator with interactive sliders
- ✅ 3D web viewer using Three.js
- ✅ JSON database system
- ✅ Blender export functionality
- ✅ Form-based data entry for wheel specs

**Key Classes:**
- `WheelSpec` - Stores wheel specifications (diameter, width, offset, bolt pattern, etc.)
- `TireSpec` - Calculates tire dimensions from standard sizing (225/45R17 format)
- `WheelDatabase` - Manages storage and retrieval of wheel/tire combinations
- `Simple3DViewer` - Web-based 3D preview system
- `WheelProcessorApp` - Main Tkinter application interface

### Blender Addon (`wheel_tire_system.py`)

**Features Implemented:**
- ✅ Import wheel 3D models with automatic scaling
- ✅ Parametric tire generation based on real tire specs
- ✅ Wheel-to-tire fitting system
- ✅ Material assignment (tire rubber, wheel finishes)
- ✅ Database integration with standalone app
- ✅ Custom UI panels in Blender

**Key Components:**
- Wheel import operators for multiple 3D formats (OBJ, FBX, DAE, PLY)
- Procedural tire mesh generation using bmesh
- Real-world scaling and positioning
- Material system for realistic rendering

## Installation & Setup

### Prerequisites

```bash
# Python 3.7+
python --version

# Blender 2.8+ (for addon)
# Available at: https://www.blender.org/download/
```

### Standalone Application

1. **Clone/Download the project files**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python standalone_app/wheel_processor.py
   ```

### Blender Addon

1. **Open Blender**
2. **Go to:** Edit → Preferences → Add-ons → Install
3. **Select:** `blender_addon/wheel_tire_system.py`
4. **Enable** the "Car Customization: Wheel & Tire System" addon
5. **Find the panel** in 3D Viewport → Sidebar (N key) → "Car Customization" tab

## Dependencies

### Standalone App
```
tkinter (built-in with Python)
json (built-in)
threading (built-in)
http.server (built-in)
webbrowser (built-in)
```

### Blender Addon
```
bpy (Blender Python API)
bmesh (Blender mesh utilities)
mathutils (Blender math utilities)
```

### 3D Viewer
```
Three.js r128 (loaded via CDN)
OrbitControls
OBJLoader
FBXLoader
```

## Usage Workflow

### 1. Wheel/Tire Preparation (Standalone App)

```bash
python wheel_processor.py
```

1. **Add Wheels:**
   - Wheel Management tab
   - Click "Add Wheel"
   - Enter specifications (diameter, width, offset, bolt pattern)
   - Browse for 3D model file
   - Save wheel

2. **Calculate Tires:**
   - Tire Management tab
   - Use sliders for width, aspect ratio, wheel diameter
   - View real-time calculations
   - Add tire to selected wheel

3. **Preview in 3D:**
   - Click "3D View" to open web viewer
   - Adjust tire parameters in real-time
   - Toggle wireframe, show/hide components

4. **Export for Blender:**
   - Export & Integration tab
   - Click "Export for Blender"
   - Save JSON file

### 2. Car Customization (Blender)

1. **Load Database:**
   - Open Blender addon panel
   - Database section → "Load Database"
   - Select exported JSON file

2. **Import Wheels:**
   - Click "Import Wheel Model"
   - Select wheel from database or new file
   - Wheel automatically scales to correct size

3. **Create Tires:**
   - Click "Create Parametric Tire"
   - Set tire size (uses calculated values from app)
   - Tire generates with realistic geometry

4. **Fit Together:**
   - Select wheel and tire
   - Click "Fit Tire to Wheel"
   - Components automatically position and parent

## Key Technical Details

### Wheel Specifications Format
```python
WheelSpec = {
    'name': str,           # "BBS LM 18x8.5"
    'diameter': float,     # inches (17.0)
    'width': float,        # inches (7.5)
    'offset': float,       # mm (35)
    'bolt_pattern': str,   # "5x114.3"
    'center_bore': float,  # mm (64.1)
    'load_rating': int,    # lbs (1500)
    'model_path': str      # "/path/to/wheel.obj"
}
```

### Tire Size Calculations
```python
# Standard tire format: 225/45R17
width = 225  # mm
aspect_ratio = 45  # percentage
wheel_diameter = 17  # inches

# Calculated values:
sidewall_height = (width * aspect_ratio / 100)  # mm
overall_diameter = (wheel_diameter * 25.4) + (2 * sidewall_height)  # mm
```

### Database Structure
```json
{
  "wheels": {
    "wheel_name": { /* WheelSpec */ }
  },
  "tire_combinations": {
    "wheel_name": [
      { /* TireSpec */ },
      { /* TireSpec */ }
    ]
  }
}
```

## Architecture Overview

### Data Flow
```
Standalone App → JSON Export → Blender Addon → 3D Scene
     ↓              ↓              ↓            ↓
Web Viewer    Database File   Import Tools   Final Result
```

### Component Interaction
1. **Standalone app** manages specifications and provides user-friendly interface
2. **JSON database** acts as bridge between applications
3. **Blender addon** handles 3D geometry and professional rendering
4. **Web viewer** provides quick preview without launching Blender

## Next Steps / Roadmap

### Phase 1: Enhanced Wheel/Tire System
- [ ] Batch import multiple wheels
- [ ] Wheel finish options (chrome, painted, machined)
- [ ] Tire tread pattern variations
- [ ] Advanced tire pressure/bulge visualization
- [ ] Wheel/tire weight calculations

### Phase 2: Car Integration
- [ ] Car model import and setup
- [ ] Suspension geometry system
- [ ] Ride height adjustment tools
- [ ] Wheel fitment validation (rubbing detection)
- [ ] Brake caliper clearance checking

### Phase 3: Advanced Features
- [ ] Real-time physics simulation
- [ ] Camber/toe adjustment visualization
- [ ] Performance impact calculations
- [ ] Photo-realistic rendering presets
- [ ] VR/AR preview capabilities

### Phase 4: Integration & Export
- [ ] Direct integration with popular car design tools
- [ ] Export to gaming engines (Unity, Unreal)
- [ ] Augmented reality mobile app
- [ ] Cloud-based wheel/tire database

## Development Notes

### Code Organization
- Keep wheel/tire logic separate from car-specific code
- Use data classes for specifications (makes serialization easy)
- Blender operators should be atomic (one action per operator)
- UI panels should reflect the workflow (prep → import → fit → render)

### Testing Strategy
- Unit tests for specification calculations
- Integration tests for Blender addon functionality
- Visual regression tests for 3D output
- Performance tests for large wheel databases

### Performance Considerations
- Lazy loading of 3D models in standalone app
- LOD (Level of Detail) for real-time preview
- Efficient mesh generation for parametric tires
- Database indexing for large inventories

## Troubleshooting

### Common Issues

**Standalone App won't start:**
- Check Python version (3.7+)
- Verify tkinter is available: `python -c "import tkinter"`

**3D Viewer not loading:**
- Check if port 8000 is available
- Try different browser
- Disable ad-blockers

**Blender Addon errors:**
- Check Blender version (2.8+)
- Verify addon is enabled in preferences
- Check console for Python errors

**Model import issues:**
- Verify 3D file format is supported
- Check file permissions
- Try exporting model in different format

### Debug Mode
Enable debug output by setting environment variable:
```bash
export CAR_CUSTOMIZER_DEBUG=1
python wheel_processor.py
```

## Contributing

### Code Style
- Follow PEP 8 for Python code
- Use descriptive variable names
- Comment complex calculations
- Include docstrings for all classes/functions

### Git Workflow
- Feature branches: `feature/wheel-database-upgrade`
- Bug fixes: `fix/tire-calculation-error`
- Documentation: `docs/api-reference-update`

## License

[Choose appropriate license - MIT, GPL, etc.]

## Contact

[Your contact information]

---

**Version:** 0.1.0  
**Last Updated:** [Current Date]  
**Blender Compatibility:** 2.8+  
**Python Compatibility:** 3.7+
