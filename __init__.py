bl_info = {
    "name": "Bend Helper",
    "author": "SynrgStudio",
    "version": (1, 3, 1),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Bend Helper",
    "description": "Interactive multi-axis mesh bending with GPU handles and multi-object support",
    "category": "Mesh",
    "doc_url": "https://github.com/SynrgStudio/bend_helper",
    "tracker_url": "",
}

import bpy
import bmesh
from mathutils import Vector, Matrix
from bpy.props import FloatProperty, BoolProperty, EnumProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup, Gizmo, GizmoGroup
from bpy_extras import view3d_utils
import math
import gpu
from gpu_extras.batch import batch_for_shader

# Almacenamiento global para datos del addon - SISTEMA MULTI-OBJETO
# Estructura: addon_data['objects'][obj.name] = {...estado del objeto...}
addon_data = {
    'objects': {},  # Dict de objetos: {obj_name: {handles, modifiers, subdivisions, handle_positions}}
    'dragging': False,
    'drag_axis': None,
    'drag_object': None,  # Nombre del objeto siendo arrastrado
    'mouse_start': None,
    'initial_angle': 0.0,
    'draw_handler': None  # Handler único que dibuja TODOS los objetos
}

def get_object_data(obj):
    """Obtener datos del objeto, creando entrada si no existe"""
    if obj.name not in addon_data['objects']:
        addon_data['objects'][obj.name] = {
            'handles': {},
            'modifiers': {},
            'subdivisions': {},
            'origins': {},
            'handle_positions': {}
        }
    return addon_data['objects'][obj.name]

def clear_object_data(obj_name):
    """Limpiar datos de un objeto específico"""
    if obj_name in addon_data['objects']:
        del addon_data['objects'][obj_name]

def draw_handles_callback():
    """Dibuja handles custom con GPU en el viewport SOLO del objeto activo seleccionado"""
    # Obtener el objeto actualmente seleccionado
    context = bpy.context
    if not context.active_object:
        return
    
    obj = context.active_object
    
    # Solo dibujar si el objeto tiene el addon activo
    if not obj.bend_helper.is_active:
        return
    
    # Verificar que tenemos datos para este objeto
    if obj.name not in addon_data['objects']:
        return
    
    obj_data = addon_data['objects'][obj.name]
    
    # Shader para líneas y círculos
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(3.0)
    
    # Configuración de handles por eje
    axes_config = {
        'X': {'color': (1.0, 0.2, 0.2, 0.9), 'offset': Vector((1, 0, 0))},
        'Y': {'color': (0.2, 1.0, 0.2, 0.9), 'offset': Vector((0, 1, 0))},
        'Z': {'color': (0.2, 0.2, 1.0, 0.9), 'offset': Vector((0, 0, 1))}
    }
    
    # Obtener dimensiones del objeto
    dims = obj.dimensions
    
    # Calcular el centro real del objeto (en coordenadas mundiales)
    bbox_center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
    world_center = obj.matrix_world @ bbox_center
    
    # Calcular tamaño de handle basado en el objeto (10% del lado más largo perpendicular)
    # Para eje X: mira Y y Z, usa el máximo
    # Para eje Y: mira X y Z, usa el máximo  
    # Para eje Z: mira X y Y, usa el máximo
    handle_sizes = {
        'X': max(dims.y, dims.z) * 0.1,
        'Y': max(dims.x, dims.z) * 0.1,
        'Z': max(dims.x, dims.y) * 0.1
    }
    
    for axis, config in axes_config.items():
        # Calcular posición del handle DESDE EL CENTRO DEL OBJETO
        offset = config['offset'].copy()
        if axis == 'X':
            offset.x *= (dims.x / 2 + 1.5)
        elif axis == 'Y':
            offset.y *= (dims.y / 2 + 1.5)
        elif axis == 'Z':
            offset.z *= (dims.z / 2 + 1.5)
        
        # Partir desde el centro del bounding box, no desde el origin del objeto
        handle_pos = world_center + offset
        obj_data['handle_positions'][axis] = handle_pos
        
        # Dibujar círculo (aproximado con líneas)
        num_segments = 32
        radius = max(handle_sizes[axis], 0.15)  # Mínimo 0.15 para objetos muy pequeños
        
        # Si está siendo arrastrado, aumentar tamaño
        if addon_data['dragging'] and addon_data['drag_object'] == obj.name and addon_data['drag_axis'] == axis:
            radius *= 1.5
            # Color más brillante
            color = (*[min(c * 1.3, 1.0) for c in config['color'][:3]], 1.0)
        else:
            color = config['color']
        
        # Generar vértices del círculo en vista 2D billboard
        # (para 3D real necesitaríamos calcular normal a cámara)
        circle_verts = []
        for i in range(num_segments + 1):
            angle = (i / num_segments) * 2 * math.pi
            # Offset en plano perpendicular al eje
            if axis == 'X':
                local_offset = Vector((0, math.cos(angle) * radius, math.sin(angle) * radius))
            elif axis == 'Y':
                local_offset = Vector((math.cos(angle) * radius, 0, math.sin(angle) * radius))
            else:  # Z
                local_offset = Vector((math.cos(angle) * radius, math.sin(angle) * radius, 0))
            
            circle_verts.append(handle_pos + local_offset)
        
        # Dibujar círculo
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": circle_verts})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        
        # Dibujar cruz en el centro
        cross_size = radius * 0.5
        if axis == 'X':
            cross_verts = [
                handle_pos + Vector((0, -cross_size, 0)),
                handle_pos + Vector((0, cross_size, 0)),
                handle_pos + Vector((0, 0, -cross_size)),
                handle_pos + Vector((0, 0, cross_size))
            ]
        elif axis == 'Y':
            cross_verts = [
                handle_pos + Vector((-cross_size, 0, 0)),
                handle_pos + Vector((cross_size, 0, 0)),
                handle_pos + Vector((0, 0, -cross_size)),
                handle_pos + Vector((0, 0, cross_size))
            ]
        else:  # Z
            cross_verts = [
                handle_pos + Vector((-cross_size, 0, 0)),
                handle_pos + Vector((cross_size, 0, 0)),
                handle_pos + Vector((0, -cross_size, 0)),
                handle_pos + Vector((0, cross_size, 0))
            ]
        
        batch = batch_for_shader(shader, 'LINES', {"pos": cross_verts})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
    
    # Restaurar estado
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')

def update_bend_angle(self, context):
    """Callback para actualizar el bend en tiempo real"""
    obj = self.id_data  # El objeto dueño de esta propiedad
    
    if not obj.bend_helper.is_active:
        return
    
    obj_data = get_object_data(obj)
    
    # Actualizar cada modificador según su propiedad
    for axis in ['X', 'Y', 'Z']:
        mod = obj_data['modifiers'].get(axis)
        if mod:
            angle = getattr(obj.bend_helper, f'bend_{axis.lower()}')
            mod.angle = math.radians(angle)
    
    # Forzar actualización de viewport
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

class BendHelperProperties(PropertyGroup):
    bend_x: FloatProperty(
        name="Bend X",
        default=0.0,
        min=-180.0,
        max=180.0,
        description="Bend angle around X axis",
        update=update_bend_angle
    )
    bend_y: FloatProperty(
        name="Bend Y",
        default=0.0,
        min=-180.0,
        max=180.0,
        description="Bend angle around Y axis",
        update=update_bend_angle
    )
    bend_z: FloatProperty(
        name="Bend Z",
        default=0.0,
        min=-180.0,
        max=180.0,
        description="Bend angle around Z axis",
        update=update_bend_angle
    )
    subdivisions: IntProperty(
        name="Subdivisions",
        default=4,  # Niveles de subdivisión (4 = buen balance)
        min=1,
        max=6,
        description="Subdivision levels (higher = smoother bends but heavier)"
    )
    is_active: BoolProperty(
        name="Active",
        default=False
    )
    auto_interactive: BoolProperty(
        name="Auto Interactive Mode",
        default=True,
        description="Automatically start interactive mode when activating"
    )

class BENDHELPER_OT_Activate(Operator):
    bl_idname = "bendhelper.activate"
    bl_label = "Activate Bend Helper"
    bl_description = "Activate bend helper on selected object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}
        
        # Verificar si ya existen modificadores del addon (de una sesión anterior)
        existing_mods = self.check_existing_modifiers(obj)
        
        if existing_mods:
            # Re-usar modificadores existentes (reconectar al sistema)
            self.reconnect_existing_modifiers(obj)
        else:
            # Crear nuevos modificadores desde cero
            # PRIMERO: Añadir subdivisión temporal (ANTES de los bends)
            self.add_subdivision(obj)
            
            # SEGUNDO: Crear modificadores Simple Deform para cada eje (DESPUÉS de subdivisión)
            self.setup_modifiers(obj)
        
        # Activar el sistema para este objeto
        obj.bend_helper.is_active = True
        
        # TERCERO: Crear handles (empties) para cada eje
        self.create_handles(context, obj)
        
        # Registrar el draw handler para handles interactivos (solo una vez globalmente)
        self.register_draw_handler(context)
        
        # Auto-iniciar modo interactivo si está activado
        if obj.bend_helper.auto_interactive:
            bpy.ops.bendhelper.interactive_bend('INVOKE_DEFAULT')
        
        self.report({'INFO'}, "Bend Helper activated")
        return {'FINISHED'}
    
    def check_existing_modifiers(self, obj):
        """Verificar si ya existen modificadores del addon"""
        has_subsurf = any(mod.name == 'BendSubdiv_ALL' for mod in obj.modifiers)
        has_bends = any(mod.name in ['Bend_X', 'Bend_Y', 'Bend_Z'] for mod in obj.modifiers)
        return has_subsurf and has_bends
    
    def reconnect_existing_modifiers(self, obj):
        """Reconectar modificadores existentes al sistema"""
        obj_data = get_object_data(obj)
        
        # Reconectar subdivisión
        for mod in obj.modifiers:
            if mod.name == 'BendSubdiv_ALL':
                obj_data['subdivisions']['ALL'] = mod
                break
        
        # Reconectar modificadores bend y buscar sus origin empties
        for axis in ['X', 'Y', 'Z']:
            for mod in obj.modifiers:
                if mod.name == f'Bend_{axis}':
                    obj_data['modifiers'][axis] = mod
                    
                    # Buscar el origin empty asociado
                    if mod.origin:
                        obj_data['origins'][axis] = mod.origin
                    break
    
    def cleanup_existing_modifiers(self, obj):
        """Limpiar modificadores antiguos del addon si existen"""
        # Buscar y remover modificadores con nombres del addon
        mods_to_remove = []
        for mod in obj.modifiers:
            if mod.name in ['BendSubdiv_ALL', 'Bend_X', 'Bend_Y', 'Bend_Z']:
                mods_to_remove.append(mod)
        
        for mod in mods_to_remove:
            obj.modifiers.remove(mod)
        
        # Buscar y remover origin empties antiguos
        empties_to_remove = []
        for obj_data in bpy.data.objects:
            if obj_data.name.startswith(f"BendOrigin_") and obj.name in obj_data.name:
                empties_to_remove.append(obj_data)
            elif obj_data.name.startswith(f"BendHandle_") and obj.name in obj_data.name:
                empties_to_remove.append(obj_data)
        
        for empty in empties_to_remove:
            bpy.data.objects.remove(empty, do_unlink=True)
        
        # IMPORTANTE: Resetear propiedades bend a 0 para evitar "salto" al activar
        obj.bend_helper.bend_x = 0.0
        obj.bend_helper.bend_y = 0.0
        obj.bend_helper.bend_z = 0.0
    
    def add_subdivision(self, obj):
        """Añadir Subdivision Surface SIMPLE que mantiene la forma original"""
        obj_data = get_object_data(obj)
        
        # SIMPLE subdivide sin suavizar, manteniendo bordes duros
        subsurf = obj.modifiers.new(name="BendSubdiv_ALL", type='SUBSURF')
        subsurf.levels = obj.bend_helper.subdivisions
        subsurf.render_levels = obj.bend_helper.subdivisions
        subsurf.subdivision_type = 'SIMPLE'  # SIMPLE mantiene la forma, no suaviza
        subsurf.show_expanded = False
        
        obj_data['subdivisions']['ALL'] = subsurf
    
    def create_handles(self, context, obj):
        """Crear handles (solo referencias internas, visuales dibujados con GPU)"""
        obj_data = get_object_data(obj)
        axes = ['X', 'Y', 'Z']
        
        # Obtener dimensiones del objeto
        dims = obj.dimensions
        
        # Calcular el centro real del objeto (en coordenadas mundiales)
        bbox_center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
        world_center = obj.matrix_world @ bbox_center
        
        for axis in axes:
            # Crear empty INVISIBLE solo como referencia (opcional, podríamos no crearlo)
            # Los handles visuales se dibujarán con GPU
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            handle = context.active_object
            handle.name = f"BendHandle_{axis}_{obj.name}"
            handle.empty_display_size = 0.01  # Muy pequeño, casi invisible
            
            # Posicionar en el lado positivo del eje DESDE EL CENTRO DEL OBJETO
            offset = Vector((0, 0, 0))
            if axis == 'X':
                offset.x = dims.x / 2 + 1.5
            elif axis == 'Y':
                offset.y = dims.y / 2 + 1.5
            elif axis == 'Z':
                offset.z = dims.z / 2 + 1.5
            
            # Usar el centro del bounding box + offset, no obj.location
            handle.location = world_center + offset
            handle.hide_viewport = True  # Ocultar, usamos GPU draw
            handle.hide_render = True
            handle.hide_select = True
            
            # Añadir custom property para identificar el eje
            handle['bend_axis'] = axis
            handle['bend_object'] = obj.name
            
            # Guardar referencia
            obj_data['handles'][axis] = handle
        
        # Re-seleccionar el objeto original
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
    
    def setup_modifiers(self, obj):
        """Crear modificadores Simple Deform para cada eje"""
        obj_data = get_object_data(obj)
        
        # Simple Deform bend funciona así:
        # - deform_axis es el eje ALREDEDOR del cual dobla (el pivote)
        # - El objeto se dobla en el plano perpendicular a ese eje
        
        # Para que cada eje doble DESDE SU PROPIA PERSPECTIVA:
        # Bend X = Dobla viendo desde X = Pivote en X = deform_axis 'X'
        # Bend Y = Dobla viendo desde Y = Pivote en Y = deform_axis 'Y'  
        # Bend Z = Dobla viendo desde Z = Pivote en Z = deform_axis 'Z'
        
        axes_config = {
            'X': {
                'deform_axis': 'X',  # Pivote en X
                'rotation': (math.radians(90), 0, 0)  # Rotar para alinear
            },
            'Y': {
                'deform_axis': 'Y',  # Pivote en Y
                'rotation': (0, math.radians(90), 0)  # Rotar para alinear
            },
            'Z': {
                'deform_axis': 'Z',  # Pivote en Z
                'rotation': (0, 0, 0)  # Sin rotación
            }
        }
        
        for axis, config in axes_config.items():
            mod = obj.modifiers.new(name=f"Bend_{axis}", type='SIMPLE_DEFORM')
            mod.deform_method = 'BEND'
            mod.deform_axis = config['deform_axis']
            mod.angle = 0.0
            mod.show_expanded = False
            
            # Calcular el centro real del objeto (en coordenadas mundiales)
            # Usar el centro del bounding box, no el origin del objeto
            bbox_center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
            world_center = obj.matrix_world @ bbox_center
            
            # Crear un empty como origen para cada bend EN EL CENTRO DEL OBJETO
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=world_center)
            origin_empty = bpy.context.active_object
            origin_empty.name = f"BendOrigin_{axis}_{obj.name}"
            origin_empty.empty_display_size = 0.1
            origin_empty.parent = obj
            origin_empty.hide_viewport = True
            origin_empty.hide_render = True
            
            # Aplicar rotación según configuración
            origin_empty.rotation_euler = config['rotation']
            
            mod.origin = origin_empty
            
            obj_data['modifiers'][axis] = mod
            obj_data['origins'][axis] = origin_empty
        
        # Re-seleccionar el objeto original
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    
    def register_draw_handler(self, context):
        """Registrar handler para dibujar handles custom en el viewport"""
        if addon_data['draw_handler'] is None:
            addon_data['draw_handler'] = bpy.types.SpaceView3D.draw_handler_add(
                draw_handles_callback, (), 'WINDOW', 'POST_VIEW'
            )

class BENDHELPER_OT_Deactivate(Operator):
    bl_idname = "bendhelper.deactivate"
    bl_label = "Deactivate Bend Helper"
    bl_description = "Deactivate interactive mode but keep current bends"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.bend_helper.is_active:
            return {'CANCELLED'}
        
        obj_data = get_object_data(obj)
        
        # Remover handles empties de ESTE objeto
        for axis, handle in obj_data['handles'].items():
            if handle and handle.name in bpy.data.objects:
                bpy.data.objects.remove(handle, do_unlink=True)
        
        # NO remover origin empties (los necesitan los modifiers para seguir funcionando)
        # NO remover modificadores (queremos que el bend se mantenga)
        
        # Limpiar datos de handles de ESTE objeto
        obj_data['handles'].clear()
        obj_data['handle_positions'].clear()
        
        # Si estaba siendo arrastrado este objeto, cancelar drag
        if addon_data['dragging'] and addon_data['drag_object'] == obj.name:
            addon_data['dragging'] = False
            addon_data['drag_axis'] = None
            addon_data['drag_object'] = None
        
        # Desactivar addon en este objeto
        obj.bend_helper.is_active = False
        
        # Remover draw handler solo si NO hay ningún objeto activo
        if not any(o.bend_helper.is_active for o in bpy.data.objects if hasattr(o, 'bend_helper')):
            if addon_data['draw_handler'] is not None:
                bpy.types.SpaceView3D.draw_handler_remove(addon_data['draw_handler'], 'WINDOW')
                addon_data['draw_handler'] = None
        
        # Refrescar viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        self.report({'INFO'}, "Bend Helper deactivated - bends preserved")
        return {'FINISHED'}

class BENDHELPER_OT_Reset(Operator):
    bl_idname = "bendhelper.reset"
    bl_label = "Reset All Bends"
    bl_description = "Reset all bend angles to zero"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.bend_helper.is_active:
            return {'CANCELLED'}
        
        obj.bend_helper.bend_x = 0.0
        obj.bend_helper.bend_y = 0.0
        obj.bend_helper.bend_z = 0.0
        
        return {'FINISHED'}

class BENDHELPER_OT_RemoveBends(Operator):
    bl_idname = "bendhelper.remove_bends"
    bl_label = "Remove Bends"
    bl_description = "Remove all bend modifiers and close addon permanently"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.bend_helper.is_active:
            return {'CANCELLED'}
        
        obj_data = get_object_data(obj)
        
        # Remover handles empties de ESTE objeto
        for axis, handle in obj_data['handles'].items():
            if handle and handle.name in bpy.data.objects:
                bpy.data.objects.remove(handle, do_unlink=True)
        
        # Remover origin empties de ESTE objeto
        for axis, origin in obj_data['origins'].items():
            if origin and origin.name in bpy.data.objects:
                bpy.data.objects.remove(origin, do_unlink=True)
        
        # Remover modificadores de ESTE objeto (volver a forma original)
        # Remover subdivisión
        subsurf = obj_data['subdivisions'].get('ALL')
        if subsurf and subsurf.name in obj.modifiers:
            obj.modifiers.remove(subsurf)
        
        # Remover bends
        for axis in ['X', 'Y', 'Z']:
            mod = obj_data['modifiers'].get(axis)
            if mod and mod.name in obj.modifiers:
                obj.modifiers.remove(mod)
        
        # Si estaba siendo arrastrado este objeto, cancelar drag
        if addon_data['dragging'] and addon_data['drag_object'] == obj.name:
            addon_data['dragging'] = False
            addon_data['drag_axis'] = None
            addon_data['drag_object'] = None
        
        # Limpiar datos de ESTE objeto
        clear_object_data(obj.name)
        
        # Resetear propiedades y desactivar addon en el objeto
        obj.bend_helper.bend_x = 0.0
        obj.bend_helper.bend_y = 0.0
        obj.bend_helper.bend_z = 0.0
        obj.bend_helper.is_active = False
        
        # Remover draw handler solo si NO hay ningún objeto activo
        if not any(o.bend_helper.is_active for o in bpy.data.objects if hasattr(o, 'bend_helper')):
            if addon_data['draw_handler'] is not None:
                bpy.types.SpaceView3D.draw_handler_remove(addon_data['draw_handler'], 'WINDOW')
                addon_data['draw_handler'] = None
        
        # Refrescar viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        self.report({'INFO'}, "Bends removed - addon closed")
        return {'FINISHED'}

class BENDHELPER_OT_Apply(Operator):
    bl_idname = "bendhelper.apply"
    bl_label = "Apply Bends"
    bl_description = "Apply all bend modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.bend_helper.is_active:
            return {'CANCELLED'}
        
        obj_data = get_object_data(obj)
        context.view_layer.objects.active = obj
        
        # IMPORTANTE: Desparentear los empties origin ANTES de aplicar
        origins_to_delete = []
        for axis, origin in obj_data['origins'].items():
            if origin and origin.name in bpy.data.objects:
                # Guardar transform mundial
                matrix_world = origin.matrix_world.copy()
                # Desparentear
                origin.parent = None
                # Restaurar posición mundial
                origin.matrix_world = matrix_world
                origins_to_delete.append(origin)
        
        # Aplicar subdivisión primero
        subsurf = obj_data['subdivisions'].get('ALL')
        if subsurf and subsurf.name in obj.modifiers:
            try:
                bpy.ops.object.modifier_apply(modifier=subsurf.name)
            except:
                pass
        
        # Aplicar bends
        for axis in ['X', 'Y', 'Z']:
            mod = obj_data['modifiers'].get(axis)
            if mod and mod.name in obj.modifiers:
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                except Exception as e:
                    self.report({'WARNING'}, f"Could not apply Bend_{axis}: {str(e)}")
        
        # Eliminar los empties origin
        for origin in origins_to_delete:
            if origin.name in bpy.data.objects:
                bpy.data.objects.remove(origin, do_unlink=True)
        
        # Eliminar handles de ESTE objeto
        for axis, handle in obj_data['handles'].items():
            if handle and handle.name in bpy.data.objects:
                bpy.data.objects.remove(handle, do_unlink=True)
        
        # Si estaba siendo arrastrado este objeto, cancelar drag
        if addon_data['dragging'] and addon_data['drag_object'] == obj.name:
            addon_data['dragging'] = False
            addon_data['drag_axis'] = None
            addon_data['drag_object'] = None
        
        # Limpiar datos de ESTE objeto
        clear_object_data(obj.name)
        
        # Desactivar addon en este objeto
        obj.bend_helper.is_active = False
        # Resetear valores a 0 después de aplicar
        obj.bend_helper.bend_x = 0.0
        obj.bend_helper.bend_y = 0.0
        obj.bend_helper.bend_z = 0.0
        
        # Remover draw handler solo si NO hay ningún objeto activo
        if not any(o.bend_helper.is_active for o in bpy.data.objects if hasattr(o, 'bend_helper')):
            if addon_data['draw_handler'] is not None:
                bpy.types.SpaceView3D.draw_handler_remove(addon_data['draw_handler'], 'WINDOW')
                addon_data['draw_handler'] = None
        
        # Refrescar viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        self.report({'INFO'}, "Bends applied successfully")
        return {'FINISHED'}

class BENDHELPER_OT_InteractiveBend(Operator):
    """Operador modal para bend interactivo arrastrando handles (PERSISTENTE)"""
    bl_idname = "bendhelper.interactive_bend"
    bl_label = "Interactive Bend"
    bl_description = "Click on handles in viewport to bend interactively"
    bl_options = {'REGISTER', 'UNDO'}
    
    _timer = None
    
    def modal(self, context, event):
        # Refrescar viewport constantemente
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        if event.type == 'TIMER':
            # Solo mantener vivo el modal
            return {'PASS_THROUGH'}
        
        if event.type == 'MOUSEMOVE':
            if addon_data['dragging']:
                # Calcular delta del mouse (coordenadas globales)
                delta_x = event.mouse_x - addon_data['mouse_start'][0]
                
                # Convertir a ángulo
                sensitivity = 0.3
                angle = addon_data['initial_angle'] + (delta_x * sensitivity)
                angle = max(-180, min(180, angle))
                
                # Actualizar el objeto que está siendo arrastrado
                obj_name = addon_data['drag_object']
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    axis = addon_data['drag_axis']
                    
                    if axis == 'X':
                        obj.bend_helper.bend_x = angle
                    elif axis == 'Y':
                        obj.bend_helper.bend_y = angle
                    elif axis == 'Z':
                        obj.bend_helper.bend_z = angle
                
                return {'RUNNING_MODAL'}
            
            # Si no está arrastrando, permitir interacción con UI
            return {'PASS_THROUGH'}
        
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                # Detectar click en handle (solo si está en 3D viewport)
                if self.is_in_3d_view(context, event):
                    hit_result = self.check_handle_hit(context, event)
                    if hit_result:
                        hit_axis, hit_obj_name = hit_result
                        addon_data['dragging'] = True
                        addon_data['drag_axis'] = hit_axis
                        addon_data['drag_object'] = hit_obj_name
                        addon_data['mouse_start'] = (event.mouse_x, event.mouse_y)
                        
                        obj = bpy.data.objects[hit_obj_name]
                        if hit_axis == 'X':
                            addon_data['initial_angle'] = obj.bend_helper.bend_x
                        elif hit_axis == 'Y':
                            addon_data['initial_angle'] = obj.bend_helper.bend_y
                        elif hit_axis == 'Z':
                            addon_data['initial_angle'] = obj.bend_helper.bend_z
                        
                        return {'RUNNING_MODAL'}
                
                # Si no hizo click en handle, permitir interacción normal con UI
                return {'PASS_THROUGH'}
            
            elif event.value == 'RELEASE':
                if addon_data['dragging']:
                    addon_data['dragging'] = False
                    addon_data['drag_axis'] = None
                    addon_data['drag_object'] = None
                    return {'RUNNING_MODAL'}
                
                return {'PASS_THROUGH'}
        
        elif event.type in {'RIGHTMOUSE'} and event.value == 'PRESS':
            if addon_data['dragging']:
                # Cancelar drag actual
                obj_name = addon_data['drag_object']
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    axis = addon_data['drag_axis']
                    angle = addon_data['initial_angle']
                    
                    if axis == 'X':
                        obj.bend_helper.bend_x = angle
                    elif axis == 'Y':
                        obj.bend_helper.bend_y = angle
                    elif axis == 'Z':
                        obj.bend_helper.bend_z = angle
                
                addon_data['dragging'] = False
                addon_data['drag_axis'] = None
                addon_data['drag_object'] = None
                return {'RUNNING_MODAL'}
            
            return {'PASS_THROUGH'}
        
        elif event.type == 'ESC' and event.value == 'PRESS':
            # ESC solo cancela drag o sale si no está arrastrando
            if addon_data['dragging']:
                # Cancelar drag
                obj_name = addon_data['drag_object']
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    axis = addon_data['drag_axis']
                    angle = addon_data['initial_angle']
                    
                    if axis == 'X':
                        obj.bend_helper.bend_x = angle
                    elif axis == 'Y':
                        obj.bend_helper.bend_y = angle
                    elif axis == 'Z':
                        obj.bend_helper.bend_z = angle
                
                addon_data['dragging'] = False
                addon_data['drag_axis'] = None
                addon_data['drag_object'] = None
                return {'RUNNING_MODAL'}
            else:
                # Salir del modo interactivo
                self.cancel(context)
                return {'FINISHED'}
        
        # Permitir todo lo demás (teclado, clicks en UI, etc.)
        return {'PASS_THROUGH'}
    
    def is_in_3d_view(self, context, event):
        """Verificar si el mouse está en el 3D viewport"""
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                if (area.x < event.mouse_x < area.x + area.width and
                    area.y < event.mouse_y < area.y + area.height):
                    return True
        return False
    
    def get_3d_view_region(self, context, event):
        """Obtener la región 3D bajo el mouse"""
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                if (area.x < event.mouse_x < area.x + area.width and
                    area.y < event.mouse_y < area.y + area.height):
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            # Encontrar rv3d
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    return region, space.region_3d
        return None, None
    
    def check_handle_hit(self, context, event):
        """Detectar si se hizo click en un handle usando distancia 3D - SOLO OBJETO ACTIVO"""
        # Obtener región y rv3d correctos
        region, rv3d = self.get_3d_view_region(context, event)
        if not region or not rv3d:
            return None
        
        # Solo verificar el objeto activo
        obj = context.active_object
        if not obj or not obj.bend_helper.is_active:
            return None
        
        if obj.name not in addon_data['objects']:
            return None
        
        obj_data = addon_data['objects'][obj.name]
        
        # Coordenadas del mouse relativas a la región
        mouse_region_x = event.mouse_x - region.x
        mouse_region_y = event.mouse_y - region.y
        
        # Verificar cada handle del objeto activo
        for axis in ['X', 'Y', 'Z']:
            handle_pos_3d = obj_data['handle_positions'].get(axis)
            if handle_pos_3d:
                # Convertir posición 3D del handle a 2D
                handle_2d = view3d_utils.location_3d_to_region_2d(
                    region, rv3d, handle_pos_3d
                )
                
                if handle_2d:
                    # Calcular distancia
                    dist = math.sqrt(
                        (mouse_region_x - handle_2d[0])**2 + 
                        (mouse_region_y - handle_2d[1])**2
                    )
                    
                    # Si está cerca (50 pixels = área generosa para click), considerar hit
                    if dist < 50:
                        return (axis, obj.name)  # Retornar eje Y nombre del objeto
        
        return None
    
    def invoke(self, context, event):
        # Verificar si hay AL MENOS un objeto con el addon activo
        has_active = any(o.bend_helper.is_active for o in bpy.data.objects if hasattr(o, 'bend_helper'))
        
        if not has_active:
            self.report({'ERROR'}, "Activate Bend Helper on at least one object first")
            return {'CANCELLED'}
        
        # Agregar timer para actualizaciones
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.016, window=context.window)  # ~60 FPS
        
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Bend Helper ACTIVE: Drag handles to bend | ESC to exit mode")
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        """Limpiar al salir"""
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        context.area.header_text_set(None)
        
        # Limpiar estado de drag
        addon_data['dragging'] = False
        addon_data['drag_axis'] = None
        addon_data['drag_object'] = None

class BENDHELPER_OT_UpdateSubdivisions(Operator):
    bl_idname = "bendhelper.update_subdivisions"
    bl_label = "Refresh Subd"
    bl_description = "Refresh subdivision level for smooth bending"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.bend_helper.is_active:
            return {'CANCELLED'}
        
        obj_data = get_object_data(obj)
        subdiv_level = obj.bend_helper.subdivisions
        
        # Actualizar nivel de subdivisión
        subsurf = obj_data['subdivisions'].get('ALL')
        if subsurf:
            subsurf.levels = subdiv_level
            subsurf.render_levels = subdiv_level
        
        self.report({'INFO'}, f"Updated to {subdiv_level} subdivision levels")
        return {'FINISHED'}

class BENDHELPER_PT_MainPanel(Panel):
    bl_label = "Bend Helper"
    bl_idname = "BENDHELPER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bend Helper'
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            layout.label(text="Select a mesh object", icon='INFO')
            return
        
        props = obj.bend_helper
        
        if not props.is_active:
            layout.operator("bendhelper.activate", icon='PLAY', text="Activate")
        else:
            layout.operator("bendhelper.deactivate", icon='PAUSE', text="Deactivate")
            
            layout.separator()
            
            # Subdivisiones
            box = layout.box()
            box.label(text="Geometry:", icon='MOD_SUBSURF')
            row = box.row()
            row.prop(props, "subdivisions")
            row.operator("bendhelper.update_subdivisions", text="Refresh", icon='FILE_REFRESH')
            box.label(text="Higher = smoother (3-4 usually enough)", icon='INFO')
            
            layout.separator()
            
            # Controles manuales para cada eje
            box = layout.box()
            box.label(text="Manual Control:", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            
            box.prop(props, "bend_x", text="X Axis", slider=True)
            box.prop(props, "bend_y", text="Y Axis", slider=True)
            box.prop(props, "bend_z", text="Z Axis", slider=True)
            
            layout.separator()
            
            # Botones de acción
            row = layout.row()
            row.operator("bendhelper.reset", icon='LOOP_BACK', text="Reset")
            
            row = layout.row()
            row.operator("bendhelper.remove_bends", icon='X', text="Remove Bends")
            row.operator("bendhelper.apply", icon='CHECKMARK', text="Apply Bends")

# Registro
classes = (
    BendHelperProperties,
    BENDHELPER_OT_Activate,
    BENDHELPER_OT_Deactivate,
    BENDHELPER_OT_Reset,
    BENDHELPER_OT_RemoveBends,
    BENDHELPER_OT_Apply,
    BENDHELPER_OT_InteractiveBend,
    BENDHELPER_OT_UpdateSubdivisions,
    BENDHELPER_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.bend_helper = bpy.props.PointerProperty(type=BendHelperProperties)

def unregister():
    # Limpiar draw handler si existe
    if addon_data.get('draw_handler') is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(addon_data['draw_handler'], 'WINDOW')
        except:
            pass
    
    # Limpiar handles de TODOS los objetos activos
    for obj_name in list(addon_data.get('objects', {}).keys()):
        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]
            if obj.bend_helper.is_active:
                try:
                    # Usar la operación deactivate desde el contexto del objeto
                    ctx = bpy.context.copy()
                    ctx['active_object'] = obj
                    bpy.ops.bendhelper.deactivate(ctx)
                except:
                    pass
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Object.bend_helper
    
    addon_data.clear()

if __name__ == "__main__":
    register()