import bpy
import bmesh
import json
import os
from mathutils import Vector, Matrix
from bpy.props import StringProperty, FloatProperty, IntProperty, EnumProperty, BoolProperty
from bpy.types import Panel, Operator, PropertyGroup

# ==========================================
# WHEEL AND TIRE DATA CLASSES
# ==========================================

class WheelSpec:
    """Stores wheel specifications"""
    def __init__(self, name="", diameter=17, width=7.5, offset=35, 
                 bolt_pattern="5x114.3", center_bore=64.1, load_rating=1500):
        self.name = name
        self.diameter = diameter  # inches
        self.width = width       # inches  
        self.offset = offset     # mm (ET)
        self.bolt_pattern = bolt_pattern  # e.g., "5x114.3"
        self.center_bore = center_bore    # mm
        self.load_rating = load_rating    # lbs
        self.model_path = ""
        
    def to_dict(self):
        return {
            'name': self.name,
            'diameter': self.diameter,
            'width': self.width,
            'offset': self.offset,
            'bolt_pattern': self.bolt_pattern,
            'center_bore': self.center_bore,
            'load_rating': self.load_rating,
            'model_path': self.model_path
        }
    
    @classmethod
    def from_dict(cls, data):
        wheel = cls()
        for key, value in data.items():
            setattr(wheel, key, value)
        return wheel

class TireSpec:
    """Stores tire specifications"""
    def __init__(self, width=225, aspect_ratio=45, diameter=17, 
                 load_index=91, speed_rating="Y"):
        self.width = width              # mm
        self.aspect_ratio = aspect_ratio # percentage
        self.diameter = diameter        # inches (wheel diameter)
        self.load_index = load_index    # tire load capacity code
        self.speed_rating = speed_rating # maximum speed rating
        
        # Calculated properties
        self.sidewall_height = (width * aspect_ratio / 100)  # mm
        self.overall_diameter = (diameter * 25.4) + (2 * self.sidewall_height)  # mm
        
    def get_tire_size_string(self):
        """Returns standard tire size format: 225/45R17"""
        return f"{self.width}/{self.aspect_ratio}R{self.diameter}"
    
    def update_calculated_values(self):
        """Recalculate derived values when specs change"""
        self.sidewall_height = (self.width * self.aspect_ratio / 100)
        self.overall_diameter = (self.diameter * 25.4) + (2 * self.sidewall_height)

# ==========================================
# WHEEL DATABASE MANAGER
# ==========================================

class WheelDatabase:
    """Manages wheel and tire combinations"""
    def __init__(self):
        self.wheels = {}
        self.tire_combinations = {}
        self.data_file = os.path.join(bpy.utils.user_resource('SCRIPTS'), "wheel_database.json")
        
    def add_wheel(self, wheel_spec):
        """Add a wheel to the database"""
        self.wheels[wheel_spec.name] = wheel_spec
        
    def add_tire_combination(self, wheel_name, tire_spec):
        """Add a tire specification for a wheel"""
        if wheel_name not in self.tire_combinations:
            self.tire_combinations[wheel_name] = []
        self.tire_combinations[wheel_name].append(tire_spec)
        
    def get_compatible_tires(self, wheel_name):
        """Get all tire combinations for a wheel"""
        return self.tire_combinations.get(wheel_name, [])
        
    def save_database(self):
        """Save database to file"""
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
            print(f"Database saved to {self.data_file}")
        except Exception as e:
            print(f"Error saving database: {e}")
            
    def load_database(self):
        """Load database from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Load wheels
                for name, wheel_data in data.get('wheels', {}).items():
                    self.wheels[name] = WheelSpec.from_dict(wheel_data)
                    
                # Load tire combinations
                for wheel_name, tire_list in data.get('tire_combinations', {}).items():
                    self.tire_combinations[wheel_name] = []
                    for tire_data in tire_list:
                        tire = TireSpec(**tire_data)
                        self.tire_combinations[wheel_name].append(tire)
                        
            print("Database loaded successfully")
        except Exception as e:
            print(f"Error loading database: {e}")

# Global database instance
wheel_db = WheelDatabase()

# ==========================================
# TIRE GENERATION FUNCTIONS
# ==========================================

def create_parametric_tire(tire_spec, wheel_diameter_mm):
    """Create a procedural tire mesh based on specifications"""
    
    # Convert tire specs to metric
    tire_width_m = tire_spec.width / 1000
    sidewall_height_m = tire_spec.sidewall_height / 1000
    wheel_radius_m = wheel_diameter_mm / 2000
    tire_outer_radius_m = wheel_radius_m + sidewall_height_m
    
    # Create new mesh
    mesh = bpy.data.meshes.new(f"Tire_{tire_spec.get_tire_size_string()}")
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    
    # Generate tire geometry using bmesh
    bm = bmesh.new()
    
    # Create tire profile using spin
    profile_verts = []
    segments = 32
    
    # Create tire cross-section profile
    # Outer sidewall
    profile_verts.append((wheel_radius_m, -tire_width_m/2, 0))
    profile_verts.append((tire_outer_radius_m * 0.95, -tire_width_m/2, 0))
    profile_verts.append((tire_outer_radius_m, -tire_width_m/2 * 0.8, 0))
    
    # Tread area
    for i in range(5):
        angle = (i / 4) * 0.2 - 0.1
        x = tire_outer_radius_m + 0.01 * (1 - abs(angle * 10))  # Slight tread bulge
        y = -tire_width_m/2 * 0.8 + (i / 4) * tire_width_m * 0.6
        profile_verts.append((x, y, 0))
    
    # Other sidewall (mirror)
    for i in range(len(profile_verts) - 1, -1, -1):
        x, y, z = profile_verts[i]
        profile_verts.append((x, -y, z))
    
    # Create vertices in bmesh
    bm_verts = []
    for vert in profile_verts:
        bm_verts.append(bm.verts.new(vert))
    
    # Create edges for profile
    for i in range(len(bm_verts) - 1):
        bm.edges.new([bm_verts[i], bm_verts[i + 1]])
    
    # Spin the profile to create tire
    spin_axis = (0, 0, 1)
    spin_center = (0, 0, 0)
    
    bmesh.ops.spin(bm, 
                   geom=bm.edges[:] + bm.verts[:],
                   cent=spin_center,
                   axis=spin_axis,
                   angle=6.28318,  # 2π radians
                   steps=segments)
    
    # Remove duplicate vertices
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    # Calculate normals and update mesh
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    
    # Add material for tire
    create_tire_material(obj)
    
    return obj

def create_tire_material(tire_obj):
    """Create a realistic tire material"""
    mat_name = "TireMaterial"
    
    # Check if material already exists
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
    else:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Add principled BSDF
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        
        # Tire properties
        bsdf.inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1.0)  # Dark rubber
        bsdf.inputs['Roughness'].default_value = 0.8
        bsdf.inputs['Specular'].default_value = 0.2
        
        # Add output
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # Link nodes
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Assign material to tire
    if tire_obj.data.materials:
        tire_obj.data.materials[0] = mat
    else:
        tire_obj.data.materials.append(mat)

# ==========================================
# WHEEL IMPORT AND PROCESSING
# ==========================================

def import_wheel_model(filepath, wheel_spec):
    """Import a wheel 3D model and set up specifications"""
    
    # Store current selection
    original_selection = bpy.context.selected_objects[:]
    
    # Import based on file type
    file_ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if file_ext in ['.obj']:
            bpy.ops.import_scene.obj(filepath=filepath)
        elif file_ext in ['.fbx']:
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif file_ext in ['.dae']:
            bpy.ops.wm.collada_import(filepath=filepath)
        elif file_ext in ['.ply']:
            bpy.ops.import_mesh.ply(filepath=filepath)
        else:
            print(f"Unsupported file format: {file_ext}")
            return None
            
    except Exception as e:
        print(f"Error importing wheel model: {e}")
        return None
    
    # Get newly imported objects
    new_objects = [obj for obj in bpy.context.selected_objects if obj not in original_selection]
    
    if not new_objects:
        print("No objects were imported")
        return None
    
    # Assume the main wheel object is the largest by volume
    wheel_obj = max(new_objects, key=lambda obj: get_object_volume(obj))
    
    # Rename and set up wheel object
    wheel_obj.name = f"Wheel_{wheel_spec.name}"
    
    # Store wheel specifications as custom properties
    wheel_obj["wheel_diameter"] = wheel_spec.diameter
    wheel_obj["wheel_width"] = wheel_spec.width
    wheel_obj["wheel_offset"] = wheel_spec.offset
    wheel_obj["bolt_pattern"] = wheel_spec.bolt_pattern
    wheel_obj["center_bore"] = wheel_spec.center_bore
    
    # Scale wheel to correct size (assuming import is in arbitrary units)
    target_diameter_m = wheel_spec.diameter * 0.0254  # inches to meters
    current_bounds = get_object_bounds(wheel_obj)
    current_diameter = max(current_bounds[0], current_bounds[1])  # X or Y dimension
    
    if current_diameter > 0:
        scale_factor = target_diameter_m / current_diameter
        wheel_obj.scale = (scale_factor, scale_factor, scale_factor)
        bpy.context.view_layer.update()
    
    # Add to wheel database
    wheel_spec.model_path = filepath
    wheel_db.add_wheel(wheel_spec)
    
    print(f"Imported wheel: {wheel_spec.name}")
    return wheel_obj

def get_object_volume(obj):
    """Calculate approximate volume of an object"""
    if obj.type != 'MESH':
        return 0
    
    bounds = get_object_bounds(obj)
    return bounds[0] * bounds[1] * bounds[2]

def get_object_bounds(obj):
    """Get object bounding box dimensions"""
    if obj.type != 'MESH':
        return (0, 0, 0)
    
    bbox = [Vector(corner) for corner in obj.bound_box]
    min_coords = Vector((min(bbox, key=lambda v: v.x).x,
                        min(bbox, key=lambda v: v.y).y,
                        min(bbox, key=lambda v: v.z).z))
    max_coords = Vector((max(bbox, key=lambda v: v.x).x,
                        max(bbox, key=lambda v: v.y).y,
                        max(bbox, key=lambda v: v.z).z))
    
    dimensions = max_coords - min_coords
    return (dimensions.x, dimensions.y, dimensions.z)

# ==========================================
# BLENDER OPERATORS
# ==========================================

class MESH_OT_import_wheel(Operator):
    """Import a wheel model"""
    bl_idname = "mesh.import_wheel"
    bl_label = "Import Wheel"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    # Wheel specifications
    wheel_name: StringProperty(name="Wheel Name", default="NewWheel")
    diameter: FloatProperty(name="Diameter (inches)", default=17.0, min=10, max=30)
    width: FloatProperty(name="Width (inches)", default=7.5, min=4, max=15)
    offset: FloatProperty(name="Offset (mm)", default=35, min=-50, max=100)
    bolt_pattern: StringProperty(name="Bolt Pattern", default="5x114.3")
    center_bore: FloatProperty(name="Center Bore (mm)", default=64.1, min=50, max=100)
    
    def execute(self, context):
        wheel_spec = WheelSpec(
            name=self.wheel_name,
            diameter=self.diameter,
            width=self.width,
            offset=self.offset,
            bolt_pattern=self.bolt_pattern,
            center_bore=self.center_bore
        )
        
        wheel_obj = import_wheel_model(self.filepath, wheel_spec)
        
        if wheel_obj:
            self.report({'INFO'}, f"Successfully imported wheel: {self.wheel_name}")
        else:
            self.report({'ERROR'}, "Failed to import wheel")
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class MESH_OT_create_tire(Operator):
    """Create a parametric tire"""
    bl_idname = "mesh.create_tire"
    bl_label = "Create Tire"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Tire specifications
    tire_width: IntProperty(name="Width (mm)", default=225, min=125, max=355)
    aspect_ratio: IntProperty(name="Aspect Ratio", default=45, min=25, max=90)
    wheel_diameter: IntProperty(name="Wheel Diameter (inches)", default=17, min=10, max=30)
    
    def execute(self, context):
        tire_spec = TireSpec(
            width=self.tire_width,
            aspect_ratio=self.aspect_ratio,
            diameter=self.wheel_diameter
        )
        
        tire_obj = create_parametric_tire(tire_spec, self.wheel_diameter * 25.4)
        
        if tire_obj:
            self.report({'INFO'}, f"Created tire: {tire_spec.get_tire_size_string()}")
        else:
            self.report({'ERROR'}, "Failed to create tire")
            
        return {'FINISHED'}

class MESH_OT_fit_tire_to_wheel(Operator):
    """Fit a tire to the selected wheel"""
    bl_idname = "mesh.fit_tire_to_wheel"
    bl_label = "Fit Tire to Wheel"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected = context.selected_objects
        
        if len(selected) != 2:
            self.report({'ERROR'}, "Please select exactly one wheel and one tire")
            return {'CANCELLED'}
        
        wheel_obj = None
        tire_obj = None
        
        # Identify wheel and tire
        for obj in selected:
            if "wheel_diameter" in obj:
                wheel_obj = obj
            elif "Tire_" in obj.name:
                tire_obj = obj
        
        if not wheel_obj or not tire_obj:
            self.report({'ERROR'}, "Could not identify wheel and tire objects")
            return {'CANCELLED'}
        
        # Position tire on wheel
        tire_obj.location = wheel_obj.location
        tire_obj.rotation_euler = wheel_obj.rotation_euler
        
        # Parent tire to wheel
        tire_obj.parent = wheel_obj
        tire_obj.parent_type = 'OBJECT'
        
        self.report({'INFO'}, "Tire fitted to wheel successfully")
        return {'FINISHED'}

# ==========================================
# UI PANELS
# ==========================================

class VIEW3D_PT_wheel_tire_panel(Panel):
    """Wheel and Tire Management Panel"""
    bl_label = "Wheel & Tire System"
    bl_idname = "VIEW3D_PT_wheel_tire"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Car Customization"
    
    def draw(self, context):
        layout = self.layout
        
        # Wheel Import Section
        box = layout.box()
        box.label(text="Wheel Management", icon='MESH_CIRCLE')
        box.operator("mesh.import_wheel", text="Import Wheel Model", icon='IMPORT')
        
        # Tire Creation Section
        box = layout.box()
        box.label(text="Tire Management", icon='MESH_TORUS')
        box.operator("mesh.create_tire", text="Create Parametric Tire", icon='MESH_TORUS')
        
        # Fitting Section
        box = layout.box()
        box.label(text="Assembly", icon='CONSTRAINT')
        box.operator("mesh.fit_tire_to_wheel", text="Fit Tire to Wheel", icon='CONSTRAINT')
        
        # Database Section
        box = layout.box()
        box.label(text="Database", icon='FILE_FOLDER')
        row = box.row()
        row.operator("wm.save_wheel_database", text="Save Database", icon='FILE_TICK')
        row.operator("wm.load_wheel_database", text="Load Database", icon='FOLDER_REDIRECT')

class WM_OT_save_wheel_database(Operator):
    """Save wheel database"""
    bl_idname = "wm.save_wheel_database"
    bl_label = "Save Database"
    
    def execute(self, context):
        wheel_db.save_database()
        self.report({'INFO'}, "Wheel database saved")
        return {'FINISHED'}

class WM_OT_load_wheel_database(Operator):
    """Load wheel database"""
    bl_idname = "wm.load_wheel_database"
    bl_label = "Load Database"
    
    def execute(self, context):
        wheel_db.load_database()
        self.report({'INFO'}, "Wheel database loaded")
        return {'FINISHED'}

# ==========================================
# REGISTRATION
# ==========================================

classes = [
    MESH_OT_import_wheel,
    MESH_OT_create_tire,
    MESH_OT_fit_tire_to_wheel,
    WM_OT_save_wheel_database,
    WM_OT_load_wheel_database,
    VIEW3D_PT_wheel_tire_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Load database on startup
    wheel_db.load_database()
    
    print("Wheel & Tire System registered successfully")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    print("Wheel & Tire System unregistered")

if __name__ == "__main__":
    register()
