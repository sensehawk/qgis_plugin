
from qgis.core import Qgis
from ..sensehawk_apis.core_apis import get_project_details

import os
import tempfile
import json


def images_bucket(report):
        for item in report:
            if item['report_type'] =='images':
                return item['datas'], item['service']
                
        return None


def imagetime( timelist):
    time = [str(i) for i in timelist]  
    return ':'.join(time)


def responejsonTogeojon(reports,thermliteobj):
    thermliteobj.projectText = thermliteobj.projectUid.text()
    if images_bucket(reports):
        imagebucket, service = images_bucket(reports)
        imagelist = [] 
        for key, value in imagebucket.items():
            imagelist.append({'type':"Feature",'geometry':{'type':'Point',
                                                                    'coordinates':[value['exif']['GPSLongitude'],
                                                                                   value["exif"]['GPSLatitude']]},
                                                                    'properties' :{'imageID':key,
                                                                                   'filename':value['filename'],
                                                                                   'camermodel':value['exif']['Make']+'_'+value['exif']['Model'],
                                                                                   'timestamp':value['exif']['GPSDateStamp']+' '+imagetime(value['exif']['GPSTimeStamp'])}})
        thermliteobj.awsinfo = service
        imagegeojson = {'type':"FeatureCollection", "features":imagelist}   
        geojson_path = os.path.join(tempfile.gettempdir(), f"{thermliteobj.projectText}point.geojson")
        with open(geojson_path, "w") as fi:
            json.dump(imagegeojson, fi)
        print(geojson_path)
        print(thermliteobj.awsinfo)
        return geojson_path
    else:
        thermliteobj.iface = thermliteobj.iface
        thermliteobj.tr = thermliteobj.tr
        thermliteobj.iface.messageBar().pushMessage(thermliteobj.tr('Image files not found for the current project uid'),Qgis.Warning)
        return False

def loadImageMetaData(task, thermliteobj):
    thermliteobj.projectText = thermliteobj.projectUid.text()
    thermliteobj.token = thermliteobj.core_token
    reports = get_project_details(thermliteobj.projectText, thermliteobj.token)['reports']
    geojson_path = responejsonTogeojon(reports, thermliteobj)
    if geojson_path:
        return {'geojson_path':geojson_path, "Download":task.description()}
    else:
        return None




    