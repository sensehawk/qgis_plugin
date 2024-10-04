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
        table_lonlat = table.geometry().asPolygon()[0] 
        self.raw_utm_coords = table_vertex(table_lonlat)  #[[x,y],[x,y]]
        tb1, _, tb3, *_ = self.raw_utm_coords
        self.raw_utm_x = (tb1[0] + tb3[0])/2
        self.raw_utm_y = (tb1[1] + tb3[1])/2
        

def row_wise_sortedTables(tableslist, top, bottom): 
    sorted_row = []
    for table in tableslist:
        centriod_utmy =  table.utm_y
        if centriod_utmy < top and centriod_utmy >= bottom-1:
            sorted_row.append(table)
    return sorted_row

def update_TableRowAndColumn(sorted_row, vlayer, current_row, projectuid):
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
        vlayer.updateFeature(rs_tables.feature) 


def table_numbering(featuresobjlist, vlayer, projectuid):
    tableslist = [table for table in featuresobjlist if table.feature['class_name'] == 'table' ]
    current_row = 1
    while len(tableslist) > 0:
        sorted_tables = sorted(tableslist, key=lambda x : x.utm_y, reverse=True) 
        topmost_table = sorted_tables[0] 
        north_top = np.max(np.array(topmost_table.utm_coords), axis=0)[1] 
        north_bottom = np.min(np.array(topmost_table.utm_coords), axis=0)[1] 
        sorted_row = row_wise_sortedTables(tableslist, north_top, north_bottom)
        update_TableRowAndColumn(sorted_row, vlayer, current_row, projectuid)
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
        tb1, _, tb3, *_ = table_utm_x_y
        xutm = (tb1[0] + tb3[0])/2
        yutm = (tb1[1] + tb3[1])/2
        setattr(feature, 'utm_coords', table_utm_x_y)
        setattr(feature,'utm_x',xutm)
        setattr(feature,'utm_y',yutm)
        
def polygon_area(utm_coords):
       # Ensure the first point is repeated at the end
       utm_coords = np.vstack([utm_coords, utm_coords[0]])
       x = utm_coords[:, 0]
       y = utm_coords[:, 1]
       
       # Apply the Shoelace formula
       area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
       return area
        
def update_issue_Row_column(project_uid, featuresobjlist, vlayer, height, width):
    tablelist = [table for table in featuresobjlist if table.feature['class_name'] == 'table' and table.issue_obj]
    module_area = height * width
    for table in tablelist:
        parentTableIssueObj = [issue for issue in table.issue_obj]
        abjx = width/2
        abjy = height/2
        leftTop_y = max(table.utm_coords, key=lambda x: x[1])[1]
        leftTop_x = min(table.utm_coords, key=lambda x: x[0])[0]
        issue_num = 1
        for issueObj in parentTableIssueObj:
            # num of module affected caluculation 
            issue_area = polygon_area(issueObj.utm_coords)
            num_module_affected = abs(round(issue_area / module_area ))

            x = (issueObj.utm_x-leftTop_x)/width
            y = (leftTop_y-issueObj.utm_y)/height
            column = ceil(x)
            row = ceil(y)
            if row < abjy: row = 1
            if column < abjx: column =1
            issueObj.feature['row']= row 
            issueObj.feature['column'] = column
            issueObj.feature['uid'] = f"{project_uid}-{issueObj.feature['table_row']}:{issueObj.feature['table_column']}~{issue_num}"
            issueObj.feature['name'] = f"{project_uid}-{issueObj.feature['table_row']}:{issueObj.feature['table_column']}~{issue_num}"
            issueObj.feature['idx'] = issue_num
            issueObj.feature['num_modules_affected'] = num_module_affected
            issue_num += 1
            vlayer.updateFeature(issueObj.feature)











