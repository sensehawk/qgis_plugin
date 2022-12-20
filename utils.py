import requests
from urllib.request import urlopen
import os
import math
from .sensehawk_apis.core_apis import get_project_geojson, save_project_geojson, get_project_details
import json
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsMapLayer, QgsRasterLayer, QgsVectorLayer
import qgis
from qgis.utils import iface
from qgis.core import *
import qgis.utils
import tempfile
import random
import utm
import tempfile


def latlon_to_utm(latitude, longitude, zone_number=None):
    return utm.from_latlon(latitude, longitude, force_zone_number=zone_number)[:2]

def download_file(url, logger, output_path=None, directory_path=None):
    logger("Downloading {} to {}...".format(url, output_path))
    if not url or url == "None":
        logger("Invalid file url...")
        return None

    # if output_path already exists and is of the same size as the download, skip download
    if os.path.exists(output_path) and os.stat(output_path).st_size == urlopen(url).length:
        return output_path
    response = requests.get(url)
    open(output_path, "wb").write(response.content)
    print(output_path)
    return output_path

def random_color():
    # Generating random color for unlisted issue type
    random_color_pick = (["#" + ''.join([random.choice('0123456789ABCDEF') for j in range(6)])])
    color = ''
    for i in random_color_pick:
        color += i
    return color

def categorize_layer(class_maps=None):
    layer = qgis.utils.iface.activeLayer()
    layer.startEditing()
    fni = layer.fields().indexFromName('class_name')
    features = layer.uniqueValues(fni)

    # color classifying based on class_name for therm / class_name and class_maps for terra
    if not class_maps:
        color_code = {'hotspot': '#001c63', 'diode_failure': '#42e9de', 'module_failure': '#2ecc71',
                      'string_failure': '#3ded2d', 'module_reverse_polarity': '#ff84dc',
                      'potential_induced_degradation': '#550487', 'vegetation': '#076e0a',
                      'tracker_malfunction': '#c50000', 'string_reverse_polarity': '#f531bd',
                      'dirt': '#b5b0b0', 'cracked_modules': '#9b9e33', 'table': '#ffff00'}
    else:
        color_code = {
            i: class_maps[i]["properties"]["color"].replace("rgb(", "").replace(")", "").replace(" ", "").split(",") for
            i in class_maps}
        color_code = {i: "#%02x%02x%02x" % tuple(int(x) for x in color_code[i]) for i in color_code}

    # Applying color based on feature class name
    categories = []
    for feature in features:
        # initialize the default symbol for this geometry type
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())

        # configure a symbol layer
        layer_style = {}
        layer_style['color'] = 'transparent'
        layer_style['line_width'] = '0.660000'

        #  Applying colour to features based on class name
        if color_code.get(feature):
            layer_style['line_color'] = color_code.get(feature)
        else:
            layer_style['line_color'] = '#000000'

        # initialize the default symbol for this geometry type
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

        # replace default symbol layer with the configured one
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)

        # create renderer object
        category = QgsRendererCategory(feature, symbol, str(feature))
        # entry for the list of category items
        categories.append(category)

    # create renderer object
    renderer = QgsCategorizedSymbolRenderer('class_name', categories)

    # assign the created renderer to the layer
    if renderer is not None:
        layer.setRenderer(renderer)

    layer.triggerRepaint()

def Clear_fields():
    loaded_layers = qgis.utils.iface.activeLayer()
    loaded_layers.startEditing()
    loaded_layers.selectAll()
    iface.actionAddFeature().trigger()
    features = loaded_layers.getFeatures()
    for feature in features:
        feature['uid'] = None
        feature['name'] = None
        print(feature['uid'])
        loaded_layers.updateFeature(feature)
        loaded_layers.updateExtents()
    loaded_layers.removeSelection()


def vlayer_load(geojson, project_details):

    vlayer_dicto = project_details['asset']['name'], project_details['group']['name']
    project_name = project_details['name']
    asset_group_name = '_'.join(vlayer_dicto)

    # saving json from the server at C:\Users\user_name\Documents\QgisQc_backup as a Backup
    user_name = os.getlogin()
    Bkup_path = os.path.join(f'C:\\Users\\{user_name}\\Documents\\QgisQc_backup\\{asset_group_name}\\{project_name}')
    geojson_path = os.path.join(f'C:\\Users\\{user_name}\\Documents\\QgisQc_backup\\{asset_group_name}\\{project_name}', "{}.json".format(project_name))

    # separating tables and issues

    if not os.path.isdir(Bkup_path):
        os.makedirs(Bkup_path)

    separated = {'table': [], 'issue': []}
    features = geojson['features']
    for feature in features:
        if feature['properties']['class_name'] == 'table':
            separated['table'].append(feature)
        else:
            separated['issue'].append(feature)

    template = {'type': 'FeatureCollection', 'features': []}
    for class_name, features in separated.items():
        template["features"] = features
        o_path = geojson_path.replace(".json", f"_{class_name}.json")
        with open(o_path, "w") as fi:
            json.dump(template, fi)
        vlayer = QgsVectorLayer(o_path, project_name+f'{class_name}', "ogr")
        QgsProject.instance().addMapLayer(vlayer)

        # coloring the layers
        categorized_layer()

        # clear uid and name fields to avoid duplicate keys
        Clear_fields()

def load_vectors(qgis_project, project_details, project_type, class_maps, class_groups,
                 raster_bounds, core_token, logger):
    project_uid = project_details["uid"]

    # Download vectors
    geojson = get_project_geojson(project_uid, core_token, project_type=project_type)

    if not geojson["features"]:
        # Create an extent feature if no feature exists
        extent_geometry = json.loads(QgsGeometry.fromRect(QgsRectangle(raster_bounds[0],
                                                                       raster_bounds[1],
                                                                       raster_bounds[2],
                                                                       raster_bounds[3])).asJson())
        extent_feature = {"type": "Feature", "properties": {"name": "Ortho Extent", "class_name": None},
                          "geometry": extent_geometry}
        geojson["features"] += [extent_feature]

    # Split geojson into groups for easy editing
    # Split vectors into class groups if the project type is terra
    # or else create class groups first for therm (Tables and Issues)
    # Grouping all new features with NULL class_name into one group (Unknown in Terra and Issues in Therm)
    if class_groups:
        class_groups["Unknown"] = [None]
        geojson_groups = {i:[] for i in class_groups}
    else:
        # If therm project, split into tables and issues
        class_groups = {"Tables": ["table"], "Issues": [None]}
        geojson_groups = {i:[] for i in class_groups}

    # Gather all known class names
    known_class_names = []
    for group in class_groups:
        known_class_names += class_groups[group]

    logger("Class groups: "+str(class_groups))
    logger("Class maps: "+str(class_maps))

    # Loop through features and group them
    for f in geojson["features"]:
        class_name = f["properties"]["class_name"]
        if class_name not in known_class_names:
            class_name = None
        # Find the group this feature belongs to
        class_group = None
        for group in class_groups:
            if class_name in class_groups[group]:
                class_group = group
                break
        if not class_group:
            continue
        geojson_groups[class_group].append(f)

    # Save all geojson groups
    geojson_paths = []
    for geojson_group in geojson_groups:
        grouped_features = geojson_groups[geojson_group]
        if not grouped_features:
            continue
        geojson["features"] = grouped_features
        geojson_path = os.path.join(tempfile.gettempdir(), "{}-{}.json".format(project_uid, geojson_group))
        with open(geojson_path, "w") as fi:
            json.dump(geojson, fi)
        geojson_paths.append(geojson_path)

    logger("Saving project geojsons...")

    # Load vectors
    for geojson_path in geojson_paths:
        vlayer = QgsVectorLayer(geojson_path, geojson_path, "ogr")
        qgis_project.addMapLayer(vlayer)
        # Apply styling
        categorize_layer(class_maps=class_maps)

    return geojson_paths, len(geojson["features"])

def combined_geojson(geojson_paths):
    # Combine all geojsons
    geojson = json.load(open(geojson_paths[0]))
    for geojson_path in geojson_paths[1:]:
        features = json.load(open(geojson_path))["features"]
        geojson["features"] += features
    return geojson

