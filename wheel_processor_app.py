#!/usr/bin/env python3
"""
Wheel & Tire Processor - Standalone Application
A dedicated tool for managing wheel and tire specifications
with 3D preview and Blender integration.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import webbrowser
import tempfile
import shutil
from pathlib import Path
import threading
import http.server
import socketserver
from urllib.parse import quote

class WheelSpec:
    """Wheel specification data class"""
    def __init__(self, name="", diameter=17, width=7.5, offset=35, 
                 bolt_pattern="5x114.3", center_bore=64.1, load_rating=1500):
        self.name = name
        self.diameter = diameter  # inches
        self.width = width       # inches  
        self.offset = offset     # mm (ET)
        self.bolt_pattern = bolt_pattern
        self.center_bore = center_bore    # mm
        self.load_rating = load_rating    # lbs
        self.model_path = ""
        self.preview_image = ""
        
    def to_dict(self):
        return {
            'name': self.name,
            'diameter': self.diameter,
            'width': self.width,
            'offset': self.offset,
            'bolt_pattern': self.bolt_pattern,
            'center_bore': self.center_bore,
            'load_rating': self.load_rating,
            'model_path': self.model_path,
            'preview_image': self.preview_image
        }
    
    @classmethod
    def from_dict(cls, data):
        wheel = cls()
        for key, value in data.items():
            setattr(wheel, key, value)
        return wheel

class TireSpec:
    """Tire specification data class"""
    def __init__(self, width=225, aspect_ratio=45, diameter=17, 
                 load_index=91, speed_rating="Y"):
        self.width = width
        self.aspect_ratio = aspect_ratio
        self.diameter = diameter
        self.load_index = load_index
        self.speed_rating = speed_rating
        
        self.sidewall_height = (width * aspect_ratio / 100)
        self.overall_diameter = (diameter * 25.4) + (2 * self.sidewall_height)
        
    def get_size_string(self):
        return f"{self.width}/{self.aspect_ratio}R{self.diameter}"
    
    def update_calculated_values(self):
        self.sidewall_height = (self.width * self.aspect_ratio / 100)
        self.overall_diameter = (self.diameter * 25.4) + (2 * self.sidewall_height)

class WheelDatabase:
    """Database manager for wheels and tires"""
    def __init__(self):
        self.wheels = {}
        self.tire_combinations = {}
        self.data_file = "wheel_database.json"
        
    def add_wheel(self, wheel_spec):
        self.wheels[wheel_spec.name] = wheel_spec
        
    def add_tire_combination(self, wheel_name, tire_spec):
        if wheel_name not in self.tire_combinations:
            self.tire_combinations[wheel_name] = []
        self.tire_combinations[wheel_name].append(tire_spec)
        
    def get_wheel_names(self):
        return list(self.wheels.keys())
        
    def get_wheel(self, name):
        return self.wheels.get(name)
        
    def remove_wheel(self, name):
        if name in self.wheels:
            del self.wheels[name]
        if name in self.tire_combinations:
            del self.tire_combinations[name]
            
    def save_database(self):
        try:
            data = {
                'wheels': {name: wheel.to_dict() for name, wheel in self.wheels.items()},
                'tire_combinations': {
                    wheel_name: [
                        {
                            'width': tire.width,
                            'aspect_ratio': tire.aspect_ratio,
                            'diameter': tire.diameter,
                            'load_index': tire.load_index,
                            'speed_rating': tire.speed_rating
                        } for tire in tires
                    ] for wheel_name, tires in self.tire_combinations.items()
                }
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
            
    def load_database(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                for name, wheel_data in data.get('wheels', {}).items():
                    self.wheels[name] = WheelSpec.from_dict(wheel_data)
                    
                for wheel_name, tire_list in data.get('tire_combinations', {}).items():
                    self.tire_combinations[wheel_name] = []
                    for tire_data in tire_list:
                        tire = TireSpec(**tire_data)
                        self.tire_combinations[wheel_name].append(tire)
            return True
        except Exception as e:
            print(f"Error loading database: {e}")
            return False
            
    def export_for_blender(self, filename):
        """Export database in Blender-compatible format"""
        try:
            blender_data = {
                'wheels': {},
                'tire_combinations': {}
            }
            
            for name, wheel in self.wheels.items():
                blender_data['wheels'][name] = wheel.to_dict()
                
            for wheel_name, tires in self.tire_combinations.items():
                blender_data['tire_combinations'][wheel_name] = [
                    {
                        'width': tire.width,
                        'aspect_ratio': tire.aspect_ratio,
                        'diameter': tire.diameter,
                        'load_index': tire.load_index,
                        'speed_rating': tire.speed_rating
                    } for tire in tires
                ]
            
            with open(filename, 'w') as f:
                json.dump(blender_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting for Blender: {e}")
            return False

class Simple3DViewer:
    """Simple 3D viewer using web technologies"""
    def __init__(self):
        self.server_port = 8000
        self.server_thread = None
        self.temp_dir = tempfile.mkdtemp()
        self.setup_viewer_files()
        
    def setup_viewer_files(self):
        """Create HTML/JS files for 3D viewer"""
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Wheel 3D Viewer</title>
    <style>
        body { margin: 0; padding: 0; background: #2a2a2a; color: white; font-family: Arial; }
        #viewer { width: 100%; height: 90vh; }
        #controls { padding: 10px; background: #333; }
        .control-group { display: inline-block; margin-right: 20px; }
        button { padding: 5px 10px; margin: 2px; background: #555; color: white; border: 1px solid #777; cursor: pointer; }
        button:hover { background: #666; }
        #info { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 10px; border-radius: 5px; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/loaders/OBJLoader.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/examples/js/loaders/FBXLoader.js"></script>
</head>
<body>
    <div id="info">
        <h3>Wheel Viewer</h3>
        <div id="wheel-info">No wheel loaded</div>
    </div>
    
    <div id="viewer"></div>
    
    <div id="controls">
        <div class="control-group">
            <button onclick="resetView()">Reset View</button>
            <button onclick="toggleWireframe()">Wireframe</button>
            <button onclick="toggleTire()">Show/Hide Tire</button>
        </div>
        
        <div class="control-group">
            <label>Tire Width: </label>
            <input type="range" id="tireWidth" min="125" max="355" value="225" onchange="updateTire()">
            <span id="tireWidthValue">225</span>mm
        </div>
        
        <div class="control-group">
            <label>Aspect Ratio: </label>
            <input type="range" id="aspectRatio" min="25" max="90" value="45" onchange="updateTire()">
            <span id="aspectRatioValue">45</span>%
        </div>
    </div>

    <script>
        let scene, camera, renderer, controls;
        let wheelMesh, tireMesh;
        let wireframeMode = false;
        let showTire = true;
        
        function init() {
            // Scene setup
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x2a2a2a);
            
            // Camera
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(2, 1, 3);
            
            // Renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight * 0.9);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            document.getElementById('viewer').appendChild(renderer.domElement);
            
            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.1;
            
            // Lights
            const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(5, 10, 5);
            directionalLight.castShadow = true;
            scene.add(directionalLight);
            
            // Ground plane
            const planeGeometry = new THREE.PlaneGeometry(10, 10);
            const planeMaterial = new THREE.MeshLambertMaterial({ color: 0x333333 });
            const plane = new THREE.Mesh(planeGeometry, planeMaterial);
            plane.rotation.x = -Math.PI / 2;
            plane.position.y = -1;
            plane.receiveShadow = true;
            scene.add(plane);
            
            // Create default wheel and tire
            createDefaultWheel();
            createDefaultTire();
            
            animate();
        }
        
        function createDefaultWheel() {
            // Simple wheel geometry for preview
            const wheelGroup = new THREE.Group();
            
            // Rim
            const rimGeometry = new THREE.CylinderGeometry(0.4, 0.4, 0.15, 32);
            const rimMaterial = new THREE.MeshPhongMaterial({ 
                color: 0xcccccc, 
                shininess: 100 
            });
            const rim = new THREE.Mesh(rimGeometry, rimMaterial);
            rim.castShadow = true;
            wheelGroup.add(rim);
            
            // Spokes
            for (let i = 0; i < 5; i++) {
                const spokeGeometry = new THREE.BoxGeometry(0.05, 0.6, 0.1);
                const spokeMaterial = new THREE.MeshPhongMaterial({ color: 0xaaaaaa });
                const spoke = new THREE.Mesh(spokeGeometry, spokeMaterial);
                spoke.rotation.z = (i / 5) * Math.PI * 2;
                spoke.castShadow = true;
                wheelGroup.add(spoke);
            }
            
            wheelMesh = wheelGroup;
            scene.add(wheelMesh);
        }
        
        function createDefaultTire() {
            const tireGroup = new THREE.Group();
            
            // Tire torus
            const tireGeometry = new THREE.TorusGeometry(0.5, 0.1, 16, 100);
            const tireMaterial = new THREE.MeshLambertMaterial({ color: 0x1a1a1a });
            const tire = new THREE.Mesh(tireGeometry, tireMaterial);
            tire.castShadow = true;
            tire.receiveShadow = true;
            tireGroup.add(tire);
            
            tireMesh = tireGroup;
            scene.add(tireMesh);
        }
        
        function updateTire() {
            const width = document.getElementById('tireWidth').value;
            const aspectRatio = document.getElementById('aspectRatio').value;
            
            document.getElementById('tireWidthValue').textContent = width;
            document.getElementById('aspectRatioValue').textContent = aspectRatio;
            
            // Update tire geometry based on parameters
            if (tireMesh) {
                const sidewallHeight = (width * aspectRatio / 100) / 1000; // Convert to meters
                const tireRadius = 0.4 + sidewallHeight;
                const tireThickness = width / 5000; // Approximate thickness
                
                // Remove old tire
                scene.remove(tireMesh);
                
                // Create new tire
                const tireGeometry = new THREE.TorusGeometry(tireRadius, tireThickness, 16, 100);
                const tireMaterial = new THREE.MeshLambertMaterial({ color: 0x1a1a1a });
                tireMesh = new THREE.Mesh(tireGeometry, tireMaterial);
                tireMesh.castShadow = true;
                tireMesh.receiveShadow = true;
                
                if (showTire) {
                    scene.add(tireMesh);
                }
            }
        }
        
        function resetView() {
            camera.position.set(2, 1, 3);
            controls.reset();
        }
        
        function toggleWireframe() {
            wireframeMode = !wireframeMode;
            
            if (wheelMesh) {
                wheelMesh.traverse((child) => {
                    if (child.material) {
                        child.material.wireframe = wireframeMode;
                    }
                });
            }
            
            if (tireMesh && tireMesh.material) {
                tireMesh.material.wireframe = wireframeMode;
            }
        }
        
        function toggleTire() {
            showTire = !showTire;
            
            if (tireMesh) {
                if (showTire) {
                    scene.add(tireMesh);
                } else {
                    scene.remove(tireMesh);
                }
            }
        }
        
        function loadWheelData(wheelData) {
            document.getElementById('wheel-info').innerHTML = `
                <strong>${wheelData.name}</strong><br>
                ${wheelData.diameter}" × ${wheelData.width}"<br>
                Offset: ${wheelData.offset}mm<br>
                Bolt Pattern: ${wheelData.bolt_pattern}
            `;
        }
        
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        
        // Handle window resize
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight * 0.9);
        });
        
        // Initialize when page loads
        window.onload = init;
    </script>
</body>
</html>
        '''
        
        with open(os.path.join(self.temp_dir, 'viewer.html'), 'w') as f:
            f.write(html_content)
    
    def start_server(self):
        """Start local web server for 3D viewer"""
        if self.server_thread and self.server_thread.is_alive():
            return
            
        def serve():
            os.chdir(self.temp_dir)
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", self.server_port), handler) as httpd:
                httpd.serve_forever()
        
        self.server_thread = threading.Thread(target=serve, daemon=True)
        self.server_thread.start()
    
    def open_viewer(self):
        """Open 3D viewer in browser"""
        self.start_server()
        webbrowser.open(f'http://localhost:{self.server_port}/viewer.html')
    
    def cleanup(self):
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

class WheelProcessorApp:
    """Main application class"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Wheel & Tire Processor")
        self.root.geometry("800x600")
        
        self.database = WheelDatabase()
        self.database.load_database()
        
        self.viewer = Simple3DViewer()
        self.current_wheel = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Wheel Management Tab
        self.wheel_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.wheel_frame, text="Wheel Management")
        self.setup_wheel_tab()
        
        # Tire Management Tab
        self.tire_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tire_frame, text="Tire Management")
        self.setup_tire_tab()
        
        # Export Tab
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="Export & Integration")
        self.setup_export_tab()
        
    def setup_wheel_tab(self):
        """Setup wheel management interface"""
        # Left panel - Wheel list
        left_frame = ttk.Frame(self.wheel_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="Wheel Inventory", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Wheel listbox
        self.wheel_listbox = tk.Listbox(left_frame)
        self.wheel_listbox.pack(fill=tk.BOTH, expand=True)
        self.wheel_listbox.bind('<<ListboxSelect>>', self.on_wheel_select)
        
        # Wheel list buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Add Wheel", command=self.add_wheel).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove", command=self.remove_wheel).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="3D View", command=self.open_3d_viewer).pack(side=tk.LEFT)
        
        # Right panel - Wheel details
        right_frame = ttk.Frame(self.wheel_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ttk.Label(right_frame, text="Wheel Specifications", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Wheel specs form
        specs_frame = ttk.LabelFrame(right_frame, text="Specifications")
        specs_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Name
        ttk.Label(specs_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.wheel_name_var = tk.StringVar()
        ttk.Entry(specs_frame, textvariable=self.wheel_name_var, width=20).grid(row=0, column=1, padx=5, pady=2)
        
        # Diameter
        ttk.Label(specs_frame, text="Diameter (inches):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.wheel_diameter_var = tk.DoubleVar(value=17.0)
        ttk.Entry(specs_frame, textvariable=self.wheel_diameter_var, width=20).grid(row=1, column=1, padx=5, pady=2)
        
        # Width
        ttk.Label(specs_frame, text="Width (inches):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.wheel_width_var = tk.DoubleVar(value=7.5)
        ttk.Entry(specs_frame, textvariable=self.wheel_width_var, width=20).grid(row=2, column=1, padx=5, pady=2)
        
        # Offset
        ttk.Label(specs_frame, text="Offset (mm):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.wheel_offset_var = tk.DoubleVar(value=35)
        ttk.Entry(specs_frame, textvariable=self.wheel_offset_var, width=20).grid(row=3, column=1, padx=5, pady=2)
        
        # Bolt Pattern
        ttk.Label(specs_frame, text="Bolt Pattern:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.bolt_pattern_var = tk.StringVar(value="5x114.3")
        ttk.Entry(specs_frame, textvariable=self.bolt_pattern_var, width=20).grid(row=4, column=1, padx=5, pady=2)
        
        # Center Bore
        ttk.Label(specs_frame, text="Center Bore (mm):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.center_bore_var = tk.DoubleVar(value=64.1)
        ttk.Entry(specs_frame, textvariable=self.center_bore_var, width=20).grid(row=5, column=1, padx=5, pady=2)
        
        # 3D Model Path
        ttk.Label(specs_frame, text="3D Model:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        model_frame = ttk.Frame(specs_frame)
        model_frame.grid(row=6, column=1, padx=5, pady=2, sticky=tk.W)
        
        self.model_path_var = tk.StringVar()
        ttk.Entry(model_frame, textvariable=self.model_path_var, width=15).pack(side=tk.LEFT)
        ttk.Button(model_frame, text="Browse", command=self.browse_model_file).pack(side=tk.LEFT, padx=(5, 0))
        
        # Save/Update button
        ttk.Button(specs_frame, text="Save Wheel", command=self.save_wheel).grid(row=7, column=0, columnspan=2, pady=10)
        
        self.refresh_wheel_list()
        
    def setup_tire_tab(self):
        """Setup tire management interface"""
        # Tire size calculator
        calc_frame = ttk.LabelFrame(self.tire_frame, text="Tire Size Calculator")
        calc_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Width
        ttk.Label(calc_frame, text="Width (mm):").grid(row=0, column=0, padx=5, pady=5)
        self.tire_width_var = tk.IntVar(value=225)
        width_scale = ttk.Scale(calc_frame, from_=125, to=355, variable=self.tire_width_var, orient=tk.HORIZONTAL)
        width_scale.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.tire_width_label = ttk.Label(calc_frame, text="225")
        self.tire_width_label.grid(row=0, column=2, padx=5, pady=5)
        
        # Aspect Ratio
        ttk.Label(calc_frame, text="Aspect Ratio (%):").grid(row=1, column=0, padx=5, pady=5)
        self.tire_aspect_var = tk.IntVar(value=45)
        aspect_scale = ttk.Scale(calc_frame, from_=25, to=90, variable=self.tire_aspect_var, orient=tk.HORIZONTAL)
        aspect_scale.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.tire_aspect_label = ttk.Label(calc_frame, text="45")
        self.tire_aspect_label.grid(row=1, column=2, padx=5, pady=5)
        
        # Wheel Diameter
        ttk.Label(calc_frame, text="Wheel Diameter (in):").grid(row=2, column=0, padx=5, pady=5)
        self.tire_diameter_var = tk.IntVar(value=17)
        diameter_scale = ttk.Scale(calc_frame, from_=10, to=30, variable=self.tire_diameter_var, orient=tk.HORIZONTAL)
        diameter_scale.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.tire_diameter_label = ttk.Label(calc_frame, text="17")
        self.tire_diameter_label.grid(row=2, column=2, padx=5, pady=5)
        
        # Configure scale callbacks
        width_scale.configure(command=lambda v: self.update_tire_calc())
        aspect_scale.configure(command=lambda v: self.update_tire_calc())
        diameter_scale.configure(command=lambda v: self.update_tire_calc())
        
        calc_frame.columnconfigure(1, weight=1)
        
        # Results
        results_frame = ttk.LabelFrame(self.tire_frame, text="Calculated Values")
        results_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.tire_size_label = ttk.Label(results_frame, text="Tire Size: 225/45R17", font=('Arial', 12, 'bold'))
        self.tire_size_label.pack(pady=5)
        
        self.sidewall_label = ttk.Label(results_frame, text="Sidewall Height: 101.25 mm")
        self.sidewall_label.pack()
        
        self.overall_diameter_label = ttk.Label(results_frame, text="Overall Diameter: 633.5 mm")
        self.overall_diameter_label.pack()
        
        # Add to wheel button
        ttk.Button(results_frame, text="Add Tire to Selected Wheel", command=self.add_tire_to_wheel).pack(pady=10)
        
        self.update_tire_calc()
        
    def setup_export_tab(self):
        """Setup export and integration interface"""
        # Export section
        export_frame = ttk.LabelFrame(self.export_frame, text="Export Options")
        export_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(export_frame, text="Export for Blender", command=self.export_for_blender).pack(pady=5)
        ttk.Button(export_frame, text="Save Database", command=self.save_database).pack(pady=5)
        ttk.Button(export_frame, text="Load Database", command=self.load_database).pack(pady=5)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.export_frame, text="Blender Integration")
        instructions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        instructions = """
To use with Blender:

1. Install the Wheel & Tire System addon in Blender
2. Export your wheel database using 'Export for Blender'
3. In Blender, go to the Car Customization panel
4. Click 'Load Database' and select your exported file

Features available in Blender:
• Import your wheel 3D models with correct specifications
• Generate parametric tires based on your size calculations
• Fit tires to wheels automatically
• Use in car customization scenes
        """
        
        ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT).pack(padx=10, pady=10)
        
    def on_wheel_select(self, event):
        """Handle wheel selection"""
        selection = self.wheel_listbox.curselection()
        if selection:
            wheel_name = self.wheel_listbox.get(selection[0])
            self.current_wheel = self.database.get_wheel(wheel_name)
            self.load_wheel_specs()
            
    def load_wheel_specs(self):
        """Load wheel specifications into form"""
        if self.current_wheel:
            self.wheel_name_var.set(self.current_wheel.name)
            self.wheel_diameter_var.set(self.current_wheel.diameter)
            self.wheel_width_var.set(self.current_wheel.width)
            self.wheel_offset_var.set(self.current_wheel.offset)
            self.bolt_pattern_var.set(self.current_wheel.bolt_pattern)
            self.center_bore_var.set(self.current_wheel.center_bore)
            self.model_path_var.set(self.current_wheel.model_path)
            
    def add_wheel(self):
        """Add new wheel"""
        self.clear_wheel_form()
        
    def clear_wheel_form(self):
        """Clear wheel form"""
        self.wheel_name_var.set("")
        self.wheel_diameter_var.set(17.0)
        self.wheel_width_var.set(7.5)
        self.wheel_offset_var.set(35)
        self.bolt_pattern_var.set("5x114.3")
        self.center_bore_var.set(64.1)
        self.model_path_var.set("")
        
    def save_wheel(self):
        """Save wheel specifications"""
        if not self.wheel_name_var.get():
            messagebox.showerror("Error", "Please enter a wheel name")
            return
            
        wheel = WheelSpec(
            name=self.wheel_name_var.get(),
            diameter=self.wheel_diameter_var.get(),
            width=self.wheel_width_var.get(),
            offset=self.wheel_offset_var.get(),
            bolt_pattern=self.bolt_pattern_var.get(),
            center_bore=self.center_bore_var.get()
        )
        wheel.model_path = self.model_path_var.get()
        
        self.database.add_wheel(wheel)
        self.refresh_wheel_list()
        messagebox.showinfo("Success", f"Wheel '{wheel.name}' saved successfully")
        
    def remove_wheel(self):
        """Remove selected wheel"""
        selection = self.wheel_listbox.curselection()
        if selection:
            wheel_name = self.wheel_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Remove wheel '{wheel_name}'?"):
                self.database.remove_wheel(wheel_name)
                self.refresh_wheel_list()
                self.clear_wheel_form()
                
    def browse_model_file(self):
        """Browse for 3D model file"""
        filetypes = [
            ("3D Models", "*.obj *.fbx *.dae *.ply"),
            ("OBJ files", "*.obj"),
            ("FBX files", "*.fbx"),
            ("DAE files", "*.dae"),
            ("PLY files", "*.ply"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select 3D Model File",
            filetypes=filetypes
        )
        
        if filename:
            self.model_path_var.set(filename)
            
    def refresh_wheel_list(self):
        """Refresh wheel listbox"""
        self.wheel_listbox.delete(0, tk.END)
        for wheel_name in self.database.get_wheel_names():
            self.wheel_listbox.insert(tk.END, wheel_name)
            
    def update_tire_calc(self):
        """Update tire calculations"""
        width = self.tire_width_var.get()
        aspect = self.tire_aspect_var.get()
        diameter = self.tire_diameter_var.get()
        
        # Update labels
        self.tire_width_label.config(text=str(width))
        self.tire_aspect_label.config(text=str(aspect))
        self.tire_diameter_label.config(text=str(diameter))
        
        # Calculate values
        tire = TireSpec(width, aspect, diameter)
        
        self.tire_size_label.config(text=f"Tire Size: {tire.get_size_string()}")
        self.sidewall_label.config(text=f"Sidewall Height: {tire.sidewall_height:.1f} mm")
        self.overall_diameter_label.config(text=f"Overall Diameter: {tire.overall_diameter:.1f} mm")
        
    def add_tire_to_wheel(self):
        """Add current tire specification to selected wheel"""
        if not self.current_wheel:
            messagebox.showerror("Error", "Please select a wheel first")
            return
            
        tire = TireSpec(
            self.tire_width_var.get(),
            self.tire_aspect_var.get(),
            self.tire_diameter_var.get()
        )
        
        self.database.add_tire_combination(self.current_wheel.name, tire)
        messagebox.showinfo("Success", f"Tire {tire.get_size_string()} added to {self.current_wheel.name}")
        
    def open_3d_viewer(self):
        """Open 3D viewer"""
        self.viewer.open_viewer()
        
    def save_database(self):
        """Save database"""
        if self.database.save_database():
            messagebox.showinfo("Success", "Database saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save database")
            
    def load_database(self):
        """Load database"""
        if self.database.load_database():
            self.refresh_wheel_list()
            messagebox.showinfo("Success", "Database loaded successfully")
        else:
            messagebox.showerror("Error", "Failed to load database")
            
    def export_for_blender(self):
        """Export database for Blender"""
        filename = filedialog.asksaveasfilename(
            title="Export for Blender",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            if self.database.export_for_blender(filename):
                messagebox.showinfo("Success", f"Database exported to {filename}")
            else:
                messagebox.showerror("Error", "Failed to export database")
                
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle application closing"""
        self.viewer.cleanup()
        self.root.destroy()

if __name__ == "__main__":
    app = WheelProcessorApp()
    app.run()
