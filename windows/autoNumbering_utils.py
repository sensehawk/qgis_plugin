import math
from math import ceil
from .packages.utm import from_latlon
import numpy as np



def topmost_table(sorted_tables):
    for ttable in sorted_tables:
            topmost_table = None
            if ttable.feature['class_name'] == 'table':
                topmost_table = ttable
                break
    return topmost_table

def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.
    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy

def table_vertex(qgspoints):
    fourpoint = []
    for vpoint in qgspoints:
        x, y = vpoint.x(), vpoint.y()
        utmy, utmx = from_latlon(y, x)[:2]
        if [utmy,utmx] not in fourpoint:
            fourpoint.append([utmy,utmx])
    return fourpoint 

class Table:
    def __init__(self, table): # table =>  Qgsfeature object => fields, geometry, attributes
        self.feature = table
        self.uid = table['uid']
        self.raw_lonlat_x, self.raw_lonlat_y = table.geometry().centroid().asPoint().x(), table.geometry().centroid().asPoint().y()
        self.raw_utm_x , self.raw_utm_y = from_latlon(self.raw_lonlat_y, self.raw_lonlat_x)[:2]
        table_lonlat = table.geometry().asPolygon()[0] 
        self.raw_utm_coords = table_vertex(table_lonlat)  #[[x,y],[x,y]]
        

def row_wise_sortedTables(tableslist, top, bottom): 
    sorted_row = []
    for table in tableslist:
        centriod_utmy =  table.utm_y
        if centriod_utmy < top and centriod_utmy >= bottom-1:
            sorted_row.append(table)
    return sorted_row

def update_TableRowAndColumn(sorted_row, Vlayer, current_row, projectuid):
    x_sorted = sorted(sorted_row, key=lambda x: x.utm_x, reverse=False)
    t_column = 1
    t_row = current_row
    for rs_tables in x_sorted:
        try:
            rs_tables.feature['table_row'] = t_row
            rs_tables.feature['table_column'] = t_column
            rs_tables.feature['row'] = t_row
            rs_tables.feature['column'] = t_column
        except KeyError:
            rs_tables.feature['table_row'] = t_row
            rs_tables.feature['table_column'] = t_column
            rs_tables.feature['row'] = t_row
            rs_tables.feature['column'] = t_column
        rs_tables.feature['uid'] = f"{projectuid}-{rs_tables.feature['table_row']}:{rs_tables.feature['table_column']}"
        rs_tables.feature['name'] = f"{projectuid}-{rs_tables.feature['table_row']}:{rs_tables.feature['table_column']}"
        rs_tables.feature['idx'] = t_column
        t_column += 1
        Vlayer.updateFeature(rs_tables.feature) 


def table_numbering(featuresobjlist, Vlayer, projectuid):
    tableslist = [table for table in featuresobjlist if table.feature['class_name'] == 'table' ]
    current_row = 1
    while len(tableslist) > 0:
        sorted_tables = sorted(tableslist, key=lambda x : x.utm_y, reverse=True) 
        topmost_table = sorted_tables[0] 
        N_top = np.max(np.array(topmost_table.utm_coords), axis=0)[1] 
        N_bottom = np.min(np.array(topmost_table.utm_coords), axis=0)[1] 
        sorted_row = row_wise_sortedTables(tableslist, N_top, N_bottom)
        update_TableRowAndColumn(sorted_row, Vlayer, current_row, projectuid)
        current_row += 1
        for usedObj in sorted_row:
            tableslist.remove(usedObj)


def update_issue_tRow_tColumn(featuresobjlist, vlayer):
    tablelist = [table for table in featuresobjlist if table.feature['class_name'] == 'table']
    issuelist = [issue for issue in featuresobjlist if issue.feature['class_name'] != 'table']
    for table in tablelist:
        issueObjlist = []
        for issue in issuelist:
            centriod = issue.feature.geometry().centroid() # centriod =>QgsGeometry
            if table.feature.geometry().contains(centriod): # Check if issue centroid falls within table coords
                issue.feature['table_column'] = table.feature['table_column']
                issue.feature['table_row'] = table.feature['table_row']
                vlayer.updateFeature(issue.feature)
                issueObjlist.append(issue)
        setattr(table,'issue_obj',issueObjlist) # Adding list of issues falling with in table to current table obj 

def update_rotated_coords(featuresobjlist,anchor_point, angle):
    for feature in featuresobjlist:
        table_utm_x_y  = []
        for v in feature.raw_utm_coords:
            rtx, rty = rotate(anchor_point, v , math.radians(angle))
            table_utm_x_y.append([rtx,rty])
        xutm, yutm = np.mean(np.array(table_utm_x_y), axis=0) # Centriod of rotated table
        setattr(feature, 'utm_coords', table_utm_x_y)
        setattr(feature,'utm_x',xutm)
        setattr(feature,'utm_y',yutm)
        
        
def update_issue_Row_column(project_uid, featuresobjlist, Vlayer, Height, Width, angle):
    tablelist = [table for table in featuresobjlist if table.feature['class_name'] == 'table' and table.issue_obj]
    for table in tablelist:
        parentTableIssueObj = [issue for issue in table.issue_obj]
        abjx = Width/2
        abjy = Height/2
        leftTop_y = max(table.utm_coords, key=lambda x: x[1])[1]
        leftTop_x = min(table.utm_coords, key=lambda x: x[0])[0]
        issue_num = 1
        for IssueObj in parentTableIssueObj:
            x = (IssueObj.utm_x-leftTop_x)/Width
            y = (leftTop_y-IssueObj.utm_y)/Height
            column = ceil(x)
            row = ceil(y)
            if row < abjy: row = 1
            if column < abjx: column =1
            IssueObj.feature['row']= row 
            IssueObj.feature['column'] = column
            IssueObj.feature['uid'] = f"{project_uid}-{IssueObj.feature['table_row']}:{IssueObj.feature['table_column']}~{issue_num}"
            IssueObj.feature['name'] = f"{project_uid}-{IssueObj.feature['table_row']}:{IssueObj.feature['table_column']}~{issue_num}"
            IssueObj.feature['idx'] = issue_num
            issue_num += 1
            Vlayer.updateFeature(IssueObj.feature)











