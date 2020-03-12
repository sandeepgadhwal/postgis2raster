import geopandas as gpd
from shapely.geometry import Point
from .utils import select_by_location_polygon, fishnet_helper_rectangle, parameterize_fishnet, save_raster

# Highest Level Functions
def analysis_circle(table:str, output_raster: str, query_x: float='latitude', query_y: float='longitude', radius: float='meter', cell_size: float='meter', classes: list=None, class_column: str='fclass', geom_column: str='wkb_geometry') -> bool:
    height = width = radius*2
    return analysis_polygon(
        table=table,
        output_raster = output_raster,
        query_x=query_x,
        query_y=query_y,
        height=height,
        width=width,
        cell_size=cell_size,
        classes=classes,
        class_column=class_column,
        geom_column=geom_column,
        circle=True
    )


def analysis_polygon(table:str, output_raster: str, query_x: float='latitude', query_y: float='longitude', height: float='meter', width: float='meter', cell_size: float='meter', classes: list=None, class_column: str='fclass', geom_column: str='wkb_geometry', circle=False) -> bool:
    
    df = select_by_location_polygon(
        table=table,
        query_x=query_x,
        query_y=query_y,
        height=height,
        width=width,
        classes=classes,
        class_column=class_column,
        geom_column=geom_column,
    )

    f_df = fishnet_helper_rectangle(
        center_x=query_x,
        center_y=query_y,
        height=height,
        width=width,
        grid_cell_size=cell_size
    )

    p_df = parameterize_fishnet(f_df, df)

    if circle:
        query_df = gpd.GeoDataFrame(geometry=[Point(query_x, query_y)], crs={"init": "epsg:4326"})
        radius = (height / 2) - cell_size
        query_df = query_df.to_crs(epsg=3857).buffer(radius).to_crs(epsg=4326)

        con = ~p_df.intersects(query_df.geometry[0])
        p_df.loc[con, 'pxvalue'] = 99

    return save_raster(str(output_raster), p_df)