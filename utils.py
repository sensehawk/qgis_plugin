import requests
from urllib.request import urlopen
import os
import math
from .core_apis import  get_project_geojson, save_project_geojson, get_project_details
import json
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsMapLayer, QgsRasterLayer, QgsVectorLayer
import qgis
from qgis.utils import iface
from qgis.core import *
import qgis.utils
import tempfile
import random

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

def catogorized_layer():
    layer = qgis.utils.iface.activeLayer()
    fni = layer.fields().indexFromName('class_name')
    issues = layer.uniqueValues(fni)

    #  color classifying based on class_name

    color_code = {'hotspot': '#001c63', 'diode_failure': '#42e9de', 'module_failure': '#2ecc71',
                  'string_failure': '#3ded2d', 'module_reverse_polarity': '#ff84dc',
                  'potential_induced_degradation': '#550487', 'vegetation': '#076e0a',
                  'tracker_malfunction': '#c50000', 'string_reverse_polarity': '#f531bd',
                  'dirt': '#b5b0b0', 'cracked_modules': '#9b9e33', 'table': '#ffff00'}

    # Applying color for based on issue type
    categories = []
    for issue in issues:
        # initialize the default symbol for this geometry type
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())

        # configure a symbol layer

        layer_style = {}
        layer_style['color'] = 'transparent'
        layer_style['line_width'] = 0.660000

        #  Applying colour to issues based on class name

        if color_code.get(issue):
            layer_style['line_color'] = color_code.get(issue)
        else:
            layer_style['line_color'] = random_color()

        # initialize the default symbol for this geometry type
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

        # replace default symbol layer with the configured one
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)

        # create renderer object
        category = QgsRendererCategory(issue, symbol, str(issue))
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
        catogorized_layer()

        # clear uid and name fields to avoid duplicate keys
        Clear_fields()







    # if not os.path.isdir(Bkup_path):
    #     os.makedirs(Bkup_path)
    # with open(geojson_path, "w") as fi:
    #     json.dump(geojson, fi)
    #
    # vlayer = QgsVectorLayer(geojson_path, project_name, "ogr")
    # QgsProject.instance().addMapLayer(vlayer)
    #
    # catogorized_layer()





    # symbol = QgsFillSymbol.createSimple({'line_color': "#0000FF", 'line_width': 0.660000, 'color': 'transparent'})
    # vlayer.renderer().setSymbol(symbol)
    # vlayer.triggerRepaint()


    # features = json.load(open(temp_json_path))["features"]
    # separated = {}
    # for feature in features:
    #     class_name = feature["properties"]["class_name"]
    #     class_list = separated.get(class_name, [])
    #     class_list.append(feature)
    #     separated[class_name] = class_list
    # template = {'type': 'FeatureCollection', 'features': []}
    # for class_name, features in separated.items():
    #     template["features"] = features
    #     o_path = geojson_path.replace(".json", "_{}.json".format(class_name))
    #     with open(o_path, "w") as fi:
    #         json.dump(template, fi)
    #     vlayer = QgsVectorLayer(o_path, project_name +f'_{class_name}', "ogr")
    #     QgsProject.instance().addMapLayer(vlayer)
    #     # colouring the layer
    #     symbol = QgsFillSymbol.createSimple({'line_color':"#0000FF", 'line_width':0.660000,'color': 'transparent'})
    #     vlayer.renderer().setSymbol(symbol)
    #     vlayer.triggerRepaint()



