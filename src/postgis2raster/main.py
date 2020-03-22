from .utils import project_xy, query_db, center_hw_to_polygon, get_class_query, get_srid
import math

# Highest Level Functions
def analysis_circle(
    table:str, 
    output_raster: str, 
    query_x: float='latitude', 
    query_y: float='longitude', 
    radius: float='meter', 
    cell_size: float='meter', 
    classes: list=None, 
    class_column: str='fclass',
    geom_column: str='wkb_geometry',
    positive: [int, list]=1,
    negative: [int, list]=0,
    nodata: int=254,
    out_srid: int=None,
    classes_to_bands: bool=False,
    connection: 'psycopg2 connection' = None
    ) -> bool:
    """
    creates a circle analysis raster

    Convert Feature to Raster with single band 
         _ _ _ _ _
        |1 1 0 0 0|
        |0 1 1 1 0|           
        |0 0 1 1 1|
        |0_0_0_1_1|

        OR

    Convert Feature to Raster with multiple bands bye setting paramter `classes_to_bands` = True
           band 1       band 2
          class 1      class 2
         _ _ _ _ _    _ _ _ _ _
        |1 1 0 0 0|  |0 1 1 1 0| 
        |0 1 1 1 0|  |0 1 1 1 0|           
        |0 0 1 1 1|  |0 0 0 1 1|
        |0_0_0_1_1|  |0_0_1_1_1| 
        
    -------------------------------
    classes: list of values from the class folder to look for.
    positive: int value for single band and multiple values for each class to be used in target raster's positive values.
    negative: int value for single band and multiple values for each class to be used in target raster's negative values.
    classes_to_bands: each class is in different band, a supporting file for class to band mapping will also be generated {output_raster}.txt.
    """

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
        positive=positive,
        negative=negative,
        circle=True,
        out_srid=out_srid,
        classes_to_bands=classes_to_bands,
        connection=connection
    )

def analysis_polygon(
    table:str, 
    output_raster: str, 
    query_x: float='latitude', 
    query_y: float='longitude', 
    height: float='meter', 
    width: float='meter', 
    cell_size: float='meter', 
    classes: list=None, 
    class_column: str='fclass', 
    geom_column: str='wkb_geometry', 
    positive: int=1,
    negative: int=0,
    nodata: int=254,
    out_srid: int=None,
    circle: bool=False,
    classes_to_bands: bool=False,
    connection: 'psycopg2 connection' = None
    ) -> bool:
    """
    creates a polygon analysis raster

    Convert Feature to Raster with single band 
         _ _ _ _ _
        |1 1 0 0 0|
        |0 1 1 1 0|           
        |0 0 1 1 1|
        |0_0_0_1_1|

        OR
        
    Convert Feature to Raster with multiple bands bye setting paramter `classes_to_bands` = True
           band 1       band 2
          class 1      class 2
         _ _ _ _ _    _ _ _ _ _
        |1 1 0 0 0|  |0 1 1 1 0| 
        |0 1 1 1 0|  |0 1 1 1 0|           
        |0 0 1 1 1|  |0 0 0 1 1|
        |0_0_0_1_1|  |0_0_1_1_1|

    -------------------------------
    classes: list of values from the class folder to look for.
    positive: int value for single band and multiple values for each class to be used in target raster's positive values.
    negative: int value for single band and multiple values for each class to be used in target raster's negative values.
    classes_to_bands: each class is in different band, a supporting file for class to band mapping will also be generated {output_raster}_classes_to_bands_mapping.txt.

    """
    #
    #   
        
    if not '.tif' in output_raster.lower():
        output_raster+='.tif'

    class_query = get_class_query(classes, class_column)
    table_srid = get_srid(table, geom_column=geom_column) 

    if out_srid is None:
        out_srid = table_srid
    
    # Convert Lat Long to Meter coordinates in 3857 for calculations as height width are in meters
    x, y = project_xy(query_x, query_y, 4326, 3857)
    x_left, y_lower, x_right, y_upper = center_hw_to_polygon(x, y, height, width)

    # Dimension of Raster
    n_rows = math.ceil((x_right - x_left) / cell_size)
    n_cols = math.ceil((y_upper - y_lower) / cell_size)

    # Find Coordinates in degrees
    # x_left_d, y_lower_d = project_xy(x_left, y_lower, 3857, 4326)
    # x_right_d, y_upper_d = project_xy(x_right, y_upper, 3857, 4326)

    # Find Grid size in degrees
    # cell_size_d = (((x_right_d - x_left_d) / (x_right - x_left)) + ((y_upper_d - y_lower_d) / (y_upper - y_lower))) *.5*cell_size


    # Convert query coordinates to table srid
    x_left_t, y_lower_t = project_xy(x_left, y_lower, 3857, table_srid)
    x_right_t, y_upper_t = project_xy(x_right, y_upper, 3857, table_srid)

    # Find Grid size in table srid units
    cell_size_t = (((x_right_t - x_left_t) / (x_right - x_left)) + ((y_upper_t - y_lower_t) / (y_upper - y_lower))) *.5*cell_size

    # Based on input selection type create selection query
    if circle:
        selection_geom_query = f"""
            WITH a AS (
                SELECT 
                    ST_SetSRID(ST_Point({query_x}, {query_y}), 4326) AS geom
            ),

            b AS (
                SELECT 
                    ST_Buffer(ST_Transform(a.geom, 3857), {height/2}) AS geom
                FROM a
            )

            SELECT
                ST_Transform(geom, {table_srid}) as geom
            FROM b

        """
    else: # POlygon
        selection_geom_query = f"""
            SELECT ST_GeomFromText('POLYGON(({x_left_t} {y_lower_t}, {x_left_t} {y_upper_t}, {x_right_t} {y_upper_t}, {x_right_t} {y_lower_t}, {x_left_t} {y_lower_t}))', {table_srid})
        """

    # Rasterization template query 
    raster_template_sql = f""" 
        SELECT ST_SetBandNoDataValue(ST_MakeEmptyRaster({n_cols}, {n_rows}, {x_left_t}, {y_upper_t}, {cell_size_t}, {cell_size_t}, {0}, {0}, {table_srid}), {nodata})
    """

    # Selection Query and empty raster for fishnet
    selection_query = f"""
        q AS (
            {selection_geom_query} AS geom
        )
    """

    # Rasterize Selection query
    selection_query_rasterize = f"""
        q_ras AS (
            SELECT
                ST_Union(
                    ST_AsRaster(
                        q.geom,
                        ({raster_template_sql}),
                        '8BUI'::text, 
                        {negative}, 
                        {nodata}
                    ),
                    'Max'
                ) AS ras
            FROM q
        )
    """

    # Use the Selection query to select features from source table
    features_selection_query = f"""
        features AS (            
            SELECT                 
                t.{geom_column} AS geom,
                t.{class_column} as class
            FROM                 
                public.{table} t,                
                q            
            WHERE                 
                ST_Intersects(q.geom, t.{geom_column})                
                AND                
                {class_query}        
        )
    """

    # Fishnet from raster band 1
    fishnet_query = f"""
        q_poly AS (
            SELECT  
                (pp).geom AS geom
            FROM 
                (
                    SELECT ST_PixelAsPolygons(
                        q_ras.ras, 
                        1
                    ) pp
                    FROM q_ras
                ) a, 
                features f
            WHERE 
                ST_Intersects(f.geom, (pp).geom)   
        )
    """

    # Fishnet to point query
    fishnet_to_point_query = f"""
        q_point AS (
            SELECT
                ST_Collect(ST_Centroid(q_poly.geom)) as geom
            FROM 
                q_poly
        )
    """

    # Updated values of rasterized selection query with positive values from fishnet points
    update_selection_raster_query = f"""raster_w_values AS (
        SELECT 
            ST_SetValue(
                q_ras.ras,
                1,
                q_point.geom,
                {positive}
            ) AS ras
        FROM
            q_ras,
            q_point
    )
    """

    if classes_to_bands:
        #
        classes_in_selection_query = f"""
            WITH {selection_query}
            SELECT 
                t.{class_column} as class,
                COUNT(t.{class_column}) as num_features
            FROM 
                public.{table} t,                
                q            
            WHERE                 
                ST_Intersects(q.geom, t.{geom_column})                
                AND                
                {class_query}
            GROUP BY
                {class_column}
        """
        classes_in_selection = query_db(classes_in_selection_query)
        csv_file = f"{output_raster}.classes_to_bands_mapping.csv"
        with open(csv_file, 'w') as f:
            f.write('S.no, class, number of features, raster_band_idx\n')
            for i, row in enumerate(classes_in_selection):
                line = f"{i+1}, {row[0]}, {row[1]}, {i}\n"
                f.write(line)

        num_bands = len(classes_in_selection)        
        datatype_array = ", ".join(num_bands*["'8BUI'::text"])
        negative_val_array = num_bands*[negative]
        nodata_val_array = num_bands*[nodata]

        
        fishnet_to_point_query_store = []
        update_selection_raster_query_setvalue = "q_ras.ras"
        update_selection_raster_query_from = "q_ras"
        for i, row in enumerate(classes_in_selection):
            idx = i+1
            _fishnet_to_point_query = f"""
                q_point_{idx} AS (
                    SELECT
                        ST_Collect(ST_Centroid(q_poly.geom)) AS geom,
                        {idx} AS idx
                    FROM 
                        q_poly,
                        features f
                    WHERE
                        ST_Intersects(q_poly.geom, f.geom)
                        AND
                        f.class = '{row[0]}'
                )
            """
            fishnet_to_point_query_store.append(_fishnet_to_point_query)

            _positive = positive
            if type(positive) == list:
                _positive = positive[i]
            
            update_selection_raster_query_setvalue = f"""
                ST_SetValue(
                    {update_selection_raster_query_setvalue},
                    {idx},
                    q_point_{idx}.geom,
                    {_positive}
                )
            """
            update_selection_raster_query_from += f", q_point_{idx}"

        fishnet_to_point_query = ",\n".join(fishnet_to_point_query_store)

        update_selection_raster_query = f"""
            raster_w_values AS (
                SELECT 
                    {update_selection_raster_query_setvalue} AS ras
                FROM
                    {update_selection_raster_query_from}
            )
        """
        selection_query_rasterize = f"""
            q_ras AS (
                SELECT
                    ST_Union(
                        ST_AsRaster(
                            q.geom,
                            ({raster_template_sql}),
                            ARRAY[{datatype_array}], 
                            ARRAY{negative_val_array}, 
                            ARRAY{nodata_val_array}
                        ),
                        'Max'
                    ) AS ras
                FROM q
            )
        """

    out_raster_sql = f"""
        {selection_query},
        
        {features_selection_query},

        {selection_query_rasterize},

        {fishnet_query},

        {fishnet_to_point_query},

        {update_selection_raster_query}
    """

    feature_to_raster_sql = f"""
        WITH {out_raster_sql},

        out_raster AS (
            SELECT
                ST_Transform(
                    r.ras,
                    {out_srid}
                ) AS ras
            FROM
                raster_w_values r
        )

        SELECT 
            ST_AsTIFF(
                out_raster.ras,
                'LZW'
            )
        FROM out_raster
    """

    #print(feature_to_raster_sql.replace('\n', ''))

    raster = query_db(feature_to_raster_sql, connection=connection)[0][0]

    # Write Raster
        
    with open(output_raster, 'wb') as f:
        f.write(bytes(raster))

    return True
