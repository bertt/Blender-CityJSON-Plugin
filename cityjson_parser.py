import bpy
import json

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

with open('/home/konstantinos/Desktop/Thesis/cityjson_datasets/vienna.json') as json_file: 
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
    
   
    
    
    #Parsing the boundary data of every object
    for theid in data['CityObjects']:
        name =theid
        for geom in data['CityObjects'][theid]['geometry']:
            bound=list()
            #Checking how nested the geometry is i.e what kind of 3D geometry it contains
            if((geom['type']=='MultiSurface') or (geom['type'] == 'CompositeSurface')):
                for face in geom['boundaries']:
                    for verts in face:
                        bound.append(tuple(verts))
                        
            elif (geom['type']=='Solid'):
                
                for shell in geom['boundaries']:
                    for face in shell:
                        for verts in face:
                            bound.append(tuple(verts))
                            
            elif (geom['type']=='MultiSolid'):
                
                for solid in geom['boundaries']:
                    for shell in solid:
                        for face in shell:
                            for verts in face:
                                bound.append(tuple(verts))
        #Visualization part
        mesh_data = bpy.data.meshes.new("cube_mesh_data")
        mesh_data.from_pydata(vertices, [], bound)
        mesh_data.update()
        obj = bpy.data.objects.new(name, mesh_data)
        scene = bpy.context.scene
        scene.collection.objects.link(obj)
        bpy.data.objects[name].select_set(True)
        
        
objects = bpy.data.objects
a = objects['UUID_LOD2_011390-b5d493d1-4222-4f08-8fa2']
b = objects['UUID_LOD2_011390-b5d493d1-4222-4f08-8fa2_1']
b.parent = a
    #bpy.ops.object.light_add(type='SUN', location=(91231.52200000001, 435866.023, 55.085))
    #bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(91531.52200000001, 435866.023, 15.085), rotation=(0.814687, 0.008346, 1.16357))