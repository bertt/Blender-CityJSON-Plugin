bl_info = {
    "name": "Import CityJSON files",
    "author": "Konstantinos Mastorakis",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import > CityJSON (.json)",
    "description": "Visualize 3D City Models encoded in CityJSON format",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}

import bpy
import json
import random
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

material_colors = {
    "WallSurface": (0.8,0.8,0.8,1),
    "RoofSurface": (0.9,0.057,0.086,1),
    "GroundSurface": (0.507,0.233,0.036,1)
}

def clean_list(values):
    
    while isinstance(values[0],list):
        values = values[0]
    return values

def assign_properties(obj, props, prefix=[]):
    #Assigns the custom properties to obj based on the props
    for prop, value in props.items():
        if prop in ["geometry", "children", "parents"]:
            continue

        if isinstance(value, dict):
            obj = assign_properties(obj, value, prefix + [prop])
        else:
            obj[".".join(prefix + [prop])] = value

    return obj

#Translating function to origin
def coord_translate_axis_origin(vertices):
    
    #Finding minimum value of x,y,z
    minx = min(i[0] for i in vertices)
    miny = min(i[1] for i in vertices)
    minz = min(i[2] for i in vertices)
    
    #Calculating new coordinates
    translated_x = [i[0]-minx for i in vertices]
    translated_y = [i[1]-miny for i in vertices]
    translated_z = [i[2]-minz for i in vertices]
    
    return (tuple(zip(translated_x,translated_y,translated_z)),minx,miny,minz)

#Translating back to original coords function
def original_coordinates(vertices,minx,miny,minz):
    
    #Calculating original coordinates
    original_x = [i[0]+minx for i in vertices]
    original_y = [i[1]+miny for i in vertices]
    original_z = [i[2]+minz for i in vertices]
    
    return (tuple(zip(original_x,original_y,original_z)))

def clean_buffer(vertices, bounds):
    """Cleans the vertices index from unused vertices"""

    new_bounds = list()
    new_vertices = list()

    i = 0
    for bound in bounds:
        new_bound = list()
        for j in range(len(bound)):
            new_vertices.append(vertices[bound[j]])
            new_bound.append(i)
            i = i + 1
        
        new_bounds.append(tuple(new_bound))
    
    return new_vertices, new_bounds

def get_scene_name(lod):
    """Returns the scene name for a given lod"""

    return "LoD {lod}".format(lod=lod)

def get_scene(lod):
    """Returns the scene that corresponds to the given lod"""

    name = get_scene_name(lod)

    if name in bpy.data.scenes:
        return bpy.data.scenes[name]
    else:
        bpy.ops.scene.new(type='NEW')
        bpy.context.scene.name = name

def check_material(material, surface):
    """Checks if the material can represent the provided surface"""

    if not material.name.startswith(surface['type']):
        return False
    
    # TODO: Add logic here to check for semantic surface attributes

    return True

def get_material(surface):
    """Returns the material that corresponds to the semantic surface"""
    matches = [m for m in bpy.data.materials if check_material(m, surface)]

    if len(matches) > 0:
        return matches[0]
    
    mat = bpy.data.materials.new(name=surface['type'])

    assign_properties(mat, surface)

    #Assign color based on surface type    
    if surface['type'] in material_colors:
        mat.diffuse_color = material_colors[surface["type"]]                            
    else:
        mat.diffuse_color = (0,0,0,1)

    return mat

def create_empty_object(name):
    """Returns an empty blender object"""

    new_object = bpy.data.objects.new(name, None)

    return new_object

def create_mesh_object(name, vertices, faces):
    """Returns a mesh blendre object"""

    mesh_data = bpy.data.meshes.new(name)
    if len(faces):
        mesh_data.from_pydata(vertices, [], faces)
    new_object = bpy.data.objects.new(name, mesh_data)

    return new_object

def objects_renderer(data, vertices):
    new_objects = []

    #Parsing the boundary data of every object
    for objid, cityobject in data['CityObjects'].items():
        city_obj = create_empty_object(objid)
        new_objects.append(city_obj)

        bound=list()
        for i in range(len(cityobject['geometry'])):
            geom = cityobject['geometry'][i]
            
            #Checking how nested the geometry is i.e what kind of 3D geometry it contains
            if((geom['type']=='MultiSurface') or (geom['type'] == 'CompositeSurface')):
                for face in geom['boundaries']:
                    # This if - else statement ignores all the holes if any in any geometry
                    if len(face)>0:
                        bound.append(tuple(face[0]))
                
            elif (geom['type']=='Solid'):
                for shell in geom['boundaries']:
                    for face in shell:
                        if (len(face)>0):
                            bound.append(tuple(face[0]))
                                                            
            elif (geom['type']=='MultiSolid'):
                for solid in geom['boundaries']:
                    for shell in solid:
                        for face in shell:
                            if (len(face)>0):
                                bound.append(tuple(face[0]))
        
            temp_vertices, temp_bound = clean_buffer(vertices, bound)
            
            obj_name = "{index}: [LoD{lod}] {name}".format(name=objid, lod=geom['lod'], index=i)
            obj = create_mesh_object(obj_name, temp_vertices, temp_bound)
            obj.parent = city_obj
            new_objects.append(obj)
            
            #Assigning attributes to chilren objects
            obj = assign_properties(obj, cityobject)

            #Assigning semantic surfaces
            obj_data = obj.data
            
            if 'semantics' in geom:
                values = geom['semantics']['values']
                
                for surface in geom['semantics']['surfaces']:
                    mat = get_material(surface)

                    obj_data.materials.append(mat)
                        
                obj_data.update()                       
                values = clean_list(values)
                
                j=0
                for face in obj_data.polygons:
                    face.material_index = values[j]
                    j+=1
    
    #Creating parent-child relationship 
    objects = bpy.data.objects  
    for objid, cityobject in data['CityObjects'].items():
        if 'parents' in cityobject and len(cityobject['parents']) > 0: 
            #Assigning child to parent
            objects[objid].parent = objects[cityobject['parents'][0]]

    scene = bpy.context.scene
    for obj in new_objects:
        scene.collection.objects.link(obj)

    return 0
    

def cityjson_parser(context, filepath, cityjson_import_settings):
    
    print("Importing CityJSON file...")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)
        
    #Open CityJSON file
    with open(filepath) as json_file:
        data = json.load(json_file)
        vertices=list() 
           
        #Checking if coordinates need to be transformed and transforming if necessary 
        if 'transform' not in data:
            for vertex in data['vertices']:
                vertices.append(tuple(vertex))
        else:
            trans_param = data['transform']
            #Transforming coords to actual real world coords
            for vertex in data['vertices']:
                x=vertex[0]*trans_param['scale'][0]+trans_param['translate'][0]
                y=vertex[1]*trans_param['scale'][1]+trans_param['translate'][1]
                z=vertex[2]*trans_param['scale'][2]+trans_param['translate'][2]
                vertices.append((x,y,z))
        
        translation = coord_translate_axis_origin(vertices)
        #Updating vertices with new translated vertices
        vertices = translation[0]
        
        #Pick a random building ID to find the number of geometries
        theid = random.choice(list(data['CityObjects']))
        while (len(data['CityObjects'][theid]['geometry']) == 0):
            theid = theid = random.choice(list(data['CityObjects']))
            
        objects_renderer(data, vertices)
        
        print("CityJSON file successfully imported.")
        
    return {'FINISHED'}


class ImportCityJSON(Operator, ImportHelper):
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import CityJSON"

    # ImportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    def execute(self, context):
        return cityjson_parser(context, self.filepath, self.use_setting)


data="CityJSON"

def write_cityjson(context, filepath, cityjson_export_settings):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    #print("running write_some_data...")
    #f = open(filepath, 'w', encoding='utf-8')
    #f.write("Hello World %s" % use_some_setting)
    #f.close()

    return {'FINISHED'}


#data ="Hello World"


class ExportCityJSON(Operator, ExportHelper):
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export CityJSON"

    # ExportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    def execute(self, context):
        return write_cityjson(context, self.filepath, self.use_setting)




# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportCityJSON.bl_idname, text="CityJSON (.json)")


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportCityJSON.bl_idname, text="CityJSON (.json)")
    
def register():
    bpy.utils.register_class(ImportCityJSON)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
    bpy.utils.register_class(ExportCityJSON)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportCityJSON)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    bpy.utils.unregister_class(ExportCityJSON)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')
