# from typing import List, Dict, Union, Literal, Any
# from pydantic import BaseModel, HttpUrl, Field, ConfigDict
# from pydantic.dataclasses import dataclass
#
# PROJECT_TYPE = Literal['terra', 'therm']
# TASK_TYPE = Literal['train', 'predict']
# MODEL_TARGET_TYPE = Literal['detection', 'segmentation', 'keypoint']
#
#
# class Polygon(BaseModel):
#     type: str = "Polygon"
#     coordinates: List[List[List[float]]]
#
#
# class MultiPolygon(Polygon):
#     type: str = "MultiPolygon"
#     coordinates: List[List[List[List[float]]]]
#
#
# class Point(BaseModel):
#     type: str = "Point"
#     coordinates: List[float]
#
#
# class FeatureProperty(BaseModel):
#     id: str = None
#
#     name: str = None
#     description: str = None
#     project: str
#     hierarchyProperties: str = None
#     dataProperties: str = None
#     extraProperties: Dict = {}
#
#     element: Union[HttpUrl, str, None] = None
#     workflow: str = None
#     workflowProgress: Dict = {}
#
#     class_name: str
#     class_id: int
#     uid: str
#
#     # https://stackoverflow.com/questions/70584730/how-to-use-a-reserved-keyword-in-pydantic-model
#     # user.dict(by_alias=True)
#     class_: str = Field(..., alias='class')
#
#
# class Feature(BaseModel):
#     type: str = "Feature"
#     properties: FeatureProperty
#     geometry: Union[Point, Polygon, MultiPolygon]
#
#
# class CRS(BaseModel):
#     type: str = "name"
#     properties: Dict = {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
#
#
# class GEOJSON(BaseModel):
#     type: str = "FeatureCollection"
#     name: str = None
#     crs: CRS = {}
#     features: List[Feature]
#
#
# class Payload(BaseModel):
#     model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')
#     project_uid: str
#     raster_url: str
#     geojson: GEOJSON
#     clip_boundary_class_name: str
#     project_type: PROJECT_TYPE
#     email_id: str
#     convert_to_magma: bool
#
#
# ##################
# # @dataclass
# class EarlyStopValue(BaseModel):
#     monitor: str = "val_loss"
#     patience: int = 5
#
#
# # @dataclass
# class PreProcessParams(BaseModel):
#     wallis: bool = False
#     grayscale: bool = False
#
#
# class DatasetParams(BaseModel):
#     model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')
#
#     name: str
#     format: str  # class names for Yolo
#     target_size: Union[int, List[int]] = 512
#     cache: bool = True
#     dataset_type: MODEL_TARGET_TYPE = "detection"
#
#
# class TrainingModel(BaseModel):
#     model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')
#     training: bool = True
#     model: str
#     type: str = "binary"
#     target: Union[str, List[str]]
#     batchsize: int = 16
#     epochs: int = 100
#     learning_rate: float = 0.01
#     early_stop_value: EarlyStopValue
#     preprocess: PreProcessParams
#
#
# class DependsTrainedModel(BaseModel):
#     models_type: str
#     target: str
#
#
# class KeyPointTrainingModel(TrainingModel):
#     depends_on: List[DependsTrainedModel]
#     target_size: List[int] = [64, 128]
#
# class ComponentShape(BaseModel):
#     """
#         feed the shape attribute inside function to filter out prediction if it exists else return as it is
#         Example: filter_by_shape for pole and module below:
#                 if module has shape below than calculated area, then ignore that prediction
#         components: {
#                 "pole": {
#                         "width": 50
#                         "height": 50,
#                         },
#
#                 "module": {
#                         "width": 150
#                         "height": 160
#                         }
#             }
#     """
#     width: float
#     height: float
#     width_diff: float
#     height_diff: float
#     area_diff: float
#
# class InferenceDetectionModel(BaseModel):
#     conf_score: float = 0.5
#     iou_score: float = 0.5
#     run_id: str = ""
#     filter_components_by_dimension_in_meter: Dict[str, ComponentShape] = {}
#
# class InferenceSegmentationModel(BaseModel):
#     conf_score: float = 0.5
#     run_id: str = ""
#
#
# class InferenceModel(BaseModel):
#     models_zip_url: str
#     detection: InferenceDetectionModel
#     segmentation: InferenceSegmentationModel
#     keypoint: InferenceSegmentationModel
#
# class ConfigModel(BaseModel):
#     #     model_config = ConfigDict(extra='forbid')
#     model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')
#
#     clip_raster: bool = False
#     normalized_gsd_value: float = 0.03
#
#     # global
#     project_uids: List[str]
#     val_project_uids: List[str]
#     test_project_uids: List[str] = []
#
#     MLFlowArtifactPath: str = "mlflow"
#     TFLogsPath: str = "training_graphs"
#
#     # project specific
#     BASE_PATH: str = "/app/data"
#     DATASET_PATH: str = "dataset"
#     MODEL_PATH: str = "models"
#     email: str
#
#     # Global value
#     class_maps: Dict
#     ml_service_map: Dict
#
#     # dataset
#     dataset: List[DatasetParams]
#
#     # task
#     detection: List[TrainingModel]
#     segmentation: List[TrainingModel]
#     keypoint: List[KeyPointTrainingModel]
#
# class InferenceConfigModel(BaseModel):
#     #     model_config = ConfigDict(extra='forbid')
#     model_config = ConfigDict(arbitrary_types_allowed=True, extra='forbid')
#
#     # global
#     project_uid: str
#
#     # project specific
#     email: str
#
#     # Global value
#     ortho_url: str
#
#     # Only, if keypoint dataset
#     geo_json: Union[str, Dict[Any, Any]]
#
#     inference: InferenceModel
#
# @dataclass
# class Bbox:
#     xmin: int
#     ymin: int
#     xmax: int
#     ymax: int
#     class_name: str
#
#
# @dataclass
# class OrthoClipBoxes:
#     index: int
#     image: Union[List[List[List[float]]], Any]
#     cx1: int
#     cy1: int
#     cx2: int
#     cy2: int
#     bboxes: List[Bbox]
#     keypoints: List[Bbox]
