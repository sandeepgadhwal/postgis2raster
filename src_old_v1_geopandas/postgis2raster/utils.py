from shapely.geometry import Point, Polygon
from shapely.ops import transform
import pyproj
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import gdal
from .config import host, port, database, user, password
from osgeo import gdal, osr
import numpy as np
import os


#__all__ = ['project_xy', 'get_class_query', 'select_by_location_circle', 'get_srid', 'get_engine']

def get_engine():
    #create_engine('protocol://username:password@host:port/databse_name') 
    con_string = f"""postgresql://{user}:{password}@{host}:{port}/{database}"""
    return create_engine(con_string)

connection = get_engine() 

def project_xy(x: float, y: float, source_srs: int, target_srs: int):
    return pyproj.transform(pyproj.Proj(init=f'epsg:{source_srs}'), pyproj.Proj(init=f'epsg:{target_srs}'), x, y)

def get_class_query(classes, class_column):
    class_query = "1=1"
    if classes is not None:
        classes_string = "', '".join(classes)
        class_query = f"""
            {class_column} IN ('{classes_string}')
        """
    return class_query

def select_by_location(table: str, selection_geometry_syntax: str, classes: list=None, class_column: str='fclass', geom_column: str='wkb_geometry') -> gpd.GeoDataFrame:
    class_query = get_class_query(classes, class_column)
    table_srid = get_srid(table, geom_column=geom_column) 
    query = f"""
        WITH q AS (
            {selection_geometry_syntax}
        ),
        q1 AS (
            SELECT 
                ST_Transform(q.geom, {table_srid}) AS geom 
            FROM q
        ),
        q2 AS (
            SELECT
                p.{geom_column} as geom
            FROM 
                public.{table} p,
                q1
            WHERE 
                ST_Intersects(
                    p.wkb_geometry, 
                    q1.geom
                )
                AND
                {class_query}
            LIMIT 1000
        )
        
        SELECT
            geom 
        FROM q2
    """
    df = gpd.GeoDataFrame.from_postgis(query, connection, geom_col='geom' )
    return df


def select_by_location_circle(table: str, query_x: float, query_y: float, radius: float, classes: list=None, class_column: str='fclass', geom_column: str='wkb_geometry'):
    selection_geometry_syntax = f"""
        WITH q AS (
            SELECT ST_SetSRID(
                ST_Point( {str(query_x)}, {str(query_y)} ), 
                4326
            ) as geom
        ),
        q1 AS (
            SELECT ST_Buffer(ST_Transform(q.geom, 3857), {radius}) as geom
            FROM q
        )
        SELECT 
            q1.geom 
        FROM q1
    """
    return select_by_location(
        table=table, 
        selection_geometry_syntax=selection_geometry_syntax, 
        classes=classes, 
        class_column= class_column, 
        geom_column= geom_column
    )


def select_by_location_polygon(table: str, query_x: float, query_y: float, height: float, width: float, classes: list=None, class_column: str='fclass', geom_column: str='wkb_geometry'):
    px, py = project_xy(
        x=query_x,
        y=query_y,
        source_srs=4326,
        target_srs=3857
    )

    x_left, y_lower, x_right, y_upper = center_hw_to_polygon(
        x=px, 
        y=py, 
        height=height, 
        width=width
    )

    selection_geometry_syntax = f"""
        SELECT ST_GeomFromText('POLYGON(({x_left} {y_lower}, {x_left} {y_upper}, {x_right} {y_upper}, {x_right} {y_lower}, {x_left} {y_lower}))', 3857) as geom
    """
    return select_by_location(
        table=table, 
        selection_geometry_syntax=selection_geometry_syntax, 
        classes=classes, 
        class_column= class_column, 
        geom_column= geom_column
    )


def get_srid(table_name: str, geom_column='wkb_geometry'):
    query = f"""
        SELECT FIND_SRID('public', '{table_name}', '{geom_column}') as srid;
    """
    srid = pd.read_sql(query, connection).srid.values[0]
    return srid

def center_hw_to_polygon(x, y, height, width):
    x_left = x - width/2
    x_right = x_left + width
    y_lower = y - height/2
    y_upper = y_lower + height
    return x_left, y_lower, x_right, y_upper

# Fishnet
def create_fishnet(x_left: 'longitude', y_lower: 'latitude', x_right: 'longitude', y_upper: 'latitude', grid_cell_size: 'float meters', crs=3857) -> gpd.GeoDataFrame:
    #x1, y1 = project_xy(16.55268272, 40.82717010, 4326, 3857)
    row_idx = 0
    geom_store = []
    attribute_store = []
    y1 = y_upper
    while y1 > y_lower:
        row_idx+=1
        col_idx = 0
        _y1 = y1 - grid_cell_size
        x1 = x_left
        while x1 < x_right:
            col_idx+=1  
            _x1 = x1 + grid_cell_size

            # Get Geometry
            coords = [(x1, y1), (x1, _y1), (_x1, _y1), (_x1, y1), (x1, y1)]
            geom = Polygon(coords)
            geom_store.append(geom)

            # Get Attributes
            row = {
                "row": row_idx,
                "col": col_idx
            }
            attribute_store.append(row)

            # 
            x1 = _x1
        y1 = _y1
    df = gpd.GeoDataFrame(attribute_store, geometry=geom_store, crs={'init': f"epsg:{crs}"})
    return df


def fishnet_helper_rectangle(center_x: 'longitude', center_y: 'latitude', height: 'float meters', width: 'float meters', grid_cell_size: 'float meters') -> gpd.GeoDataFrame:
    px, py = project_xy(
        x=center_x,
        y=center_y,
        source_srs=4326,
        target_srs=3857
    )

    x_left, y_lower, x_right, y_upper = center_hw_to_polygon(
        x=px, 
        y=py, 
        height=height, 
        width=width
    )

    fishnet_df = create_fishnet(
        x_left=x_left,
        y_lower=y_lower,
        x_right=x_right,
        y_upper=y_upper,
        grid_cell_size=grid_cell_size,
        crs=3857
    )
    return fishnet_df.to_crs(epsg=4326)

    
def fishnet_helper_circle(center_x: 'longitude', center_y: 'latitude', radius: 'float meters', grid_cell_size: 'float meters') -> gpd.GeoDataFrame:
    return fishnet_helper_rectangle(
        center_x=center_x, 
        center_y=center_y, 
        height=radius, 
        width=radius,
        grid_cell_size=grid_cell_size
    )
    

def parameterize_fishnet(fishnet_df: gpd.GeoDataFrame, parameter_df: gpd.GeoDataFrame):
    
    # Create pixel value column
    fishnet_df['pxvalue'] = 0

    joined_df = gpd.sjoin(fishnet_df, parameter_df, how="left", op='intersects')
    joined_df = joined_df[~joined_df.index_right.isna()]
    joined_df = joined_df.reset_index()
    joined_df['left_idx'] = joined_df['index']
    joined_df = joined_df[['left_idx']]
    joined_df = joined_df.drop_duplicates(subset=['left_idx'])
    fishnet_df.loc[joined_df.left_idx.values, 'pxvalue'] = 1

    return fishnet_df


def save_raster(raster_path: str, parameterized_fishnet_df: gpd.GeoDataFrame) -> bool:
    
    if not '.tif' in raster_path.lower():
        raster_path+='.tif'

    # Get Array from fishnet
    nrows = int(parameterized_fishnet_df.row.max())
    ncols = int(parameterized_fishnet_df.col.max())
    arr = parameterized_fishnet_df.pxvalue.values.reshape(nrows, ncols)

    # Not needed fixed at the gridding function
    # Flip array rows from (0, n) -> (n, 0) because in dataframe rows start from bottom and here we need to start them from top
    # arr = np.flip(arr)

    xmin, ymin, xmax, ymax = parameterized_fishnet_df.geometry.total_bounds

    # Cell Size
    xres = (xmax-xmin)/float(ncols)
    yres = (ymax-ymin)/float(nrows) 

    geotransform = (xmin, xres, 0, ymax, 0, -yres)

    # Create TIFF
    driver = gdal.GetDriverByName('GTiff')
    output_raster = driver.Create(raster_path, ncols, nrows, 1 , gdal.GDT_Byte)  # Open the file
    output_raster.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    output_raster.SetProjection(srs.ExportToWkt())
    band = output_raster.GetRasterBand(1)
    band.SetNoDataValue(99)
    band.WriteArray(arr)
    output_raster.FlushCache()

    return True



