from qgis.core import QgsTask, QgsApplication, Qgis, QgsRasterLayer
from .sensehawk_apis.terra_apis import get_terra_classmaps
from .sensehawk_apis.core_apis import get_ortho_tiles_url
from .utils import combined_geojson, load_vectors, get_project_details
import requests
from .constants import CLIP_FUNCTION_URL


def loadTask(task, load_window):
    load_window.project_type = load_window.projectType.currentText().lower()
    load_window.logger('Loading SenseHawk {} project...'.format(load_window.project_type))
    load_window.project_uid = load_window.projectUid.text()
    load_window.logger('UID specified: {}'.format(load_window.project_uid))
    if not load_window.project_uid:
        load_window.logger('Please specify project UID', level=Qgis.Warning)
        return False

    # Get project details from core
    load_window.project_details = get_project_details(load_window.project_uid, load_window.core_token)
    if not load_window.project_details:
        load_window.logger('Project not found', level=Qgis.Warning)
        return False

    # Get the class maps for vectors from terra / therm
    if load_window.project_type == "terra":
        load_window.class_maps, load_window.class_groups = get_terra_classmaps(load_window.project_details, load_window.core_token)

    # Get base url for ortho tiles
    base_orthotiles_url = get_ortho_tiles_url(load_window.project_uid, load_window.core_token)

    # Get metadata from the base url
    ortho_tiles_details = requests.request("GET", base_orthotiles_url).json()
    ortho_bounds = ortho_tiles_details["bounds"]
    load_window.bounds = ortho_bounds

    zmax = ortho_tiles_details["maxzoom"]
    zmin = ortho_tiles_details["center"][-1]

    orthotiles_url = "type=xyz&url=" + \
                     base_orthotiles_url + "/{z}/{x}/{y}.png" + \
                     "&zmax={}&zmin={}".format(zmax, zmin)
    load_window.logger("Ortho tiles url: {}...".format(orthotiles_url))

    # Load ortho tiles from url
    rlayer = QgsRasterLayer(orthotiles_url, load_window.project_uid + "_ortho", 'wms')

    # Load vectors
    try:
        vlayers, load_window.geojson_paths, load_window.loaded_feature_count = load_vectors(load_window.project_details,
                                                                     load_window.project_type, load_window.class_maps,
                                                                     load_window.class_groups,
                                                                     load_window.bounds, load_window.core_token, load_window.logger)

    except Exception as e:
        load_window.logger(str(e), level=Qgis.Warning)
        return False

    # Set load_successful variable to True
    load_window.logger("Load successful...")
    load_window.load_successful = True
    return {'load_window': load_window,
            'rlayer': rlayer,
            'vlayers': vlayers,
            'task': task.description()}


class clipRequest(QgsTask):
    """
    Sends clip request to the AWS lambda clip function
    """

    def __init__(self, logger, project_details, geojson_paths, class_maps):
        super(clipRequest, self).__init__()
        self.logger, self.project_details, self.geojson_paths, self.class_maps = logger, project_details, \
            geojson_paths, class_maps

    def run(self):
        self.logger("Clip task started...")
        clip_boundary_class_name = None
        # Get the class_name for clip_boundary
        for i in self.class_maps.items():
            if i[1].get("name") == "clip_boundary":
                clip_boundary_class_name = i[0]
        if not clip_boundary_class_name:
            self.logger("Please add clip_boundary feature type in Terra...", level=Qgis.Warning)
            return False
        # Combine all geojsons that were split at load
        geojson = combined_geojson(self.geojson_paths)
        all_clip_feature_names = []

        for f in geojson["features"]:
            properties = f["properties"]
            if properties["class_name"] == clip_boundary_class_name:
                name = properties.get("name", None)
                all_clip_feature_names.append(name)
        n_clip_features = len(all_clip_feature_names)
        n_unique_clip_names = len(list(set(all_clip_feature_names)))

        # If there are no unique clip feature names or if any of them has None
        if n_clip_features != n_unique_clip_names or None in all_clip_feature_names:
            self.logger("Please provide unique name property to all clip_boundary features before clipping...",
                   level=Qgis.Warning)
            return False
        try:
            ortho_report_object = [r for r in self.project_details["reports"] if r.get("report_type", None) == "ortho"][0]
        except Exception:
            self.logger("No ortho found for project...", level=Qgis.Warning)
            return False
        ortho_url = get_report_url(ortho_report_object)
        request_body = {"project_uid": self.project_details.get("uid", None),
                        "raster_url": ortho_url,
                        "geojson": geojson,
                        "clip_boundary_class_name": clip_boundary_class_name}

        requests.post(CLIP_FUNCTION_URL, json=request_body)
        self.logger("Clipping request sent...")
        return True

    def finished(self, result):
        if not result:
            self.logger("Clip request failed...")