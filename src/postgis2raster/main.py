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
    positive: int=1,
    negative: int=0,
    nodata: int=254,
    out_srid: int=None
    ) -> bool:

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
        out_srid=out_srid
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
    circle=False
    ) -> bool:
    #

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

    raster_template_sql = f""" 
        SELECT ST_SetBandNoDataValue(ST_MakeEmptyRaster({n_cols}, {n_rows}, {x_left_t}, {y_upper_t}, {cell_size_t}, {cell_size_t}, {0}, {0}, {table_srid}), {nodata})
    """

    if circle:
        selection_geom_sql = f"""
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
        selection_geom_sql = f"""
            SELECT ST_GeomFromText('POLYGON(({x_left_t} {y_lower_t}, {x_left_t} {y_upper_t}, {x_right_t} {y_upper_t}, {x_right_t} {y_lower_t}, {x_left_t} {y_lower_t}))', {table_srid})
        """

    # Convert Feature to SQL
    feature_to_raster_sql = f"""
        WITH q AS (
            {selection_geom_sql} AS geom
        ),

        features AS (            
            SELECT                 
                t.wkb_geometry AS geom            
            FROM                 
                public.{table} t,                
                q            
            WHERE                 
                ST_Intersects(q.geom, t.wkb_geometry)                
                AND                
                {class_query}        
        ),

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
        ),

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
        ),

        q_point AS (
            SELECT
                ST_Collect(ST_Centroid(q_poly.geom)) as geom
            FROM 
                q_poly
        ),

        raster_w_values AS (
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
        ),

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
        
    """.replace('\n', '')

    raster = query_db(feature_to_raster_sql)[0][0]

    # Write Raster
    if not '.tif' in output_raster.lower():
        output_raster+='.tif'
        
    with open(output_raster, 'wb') as f:
        f.write(bytes(raster))

    return True


def analysis_polygon1(
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
    out_srid: int=4326,
    circle=False
    ) -> bool:
    #

    class_query = get_class_query(classes, class_column)
    table_srid = get_srid(table, geom_column=geom_column) 
    
    
    #
    x, y = project_xy(query_x, query_y, 4326, 3857)
    x_left, y_lower, x_right, y_upper = center_hw_to_polygon(x, y, height, width)
    # x_left_d, y_lower_d = project_xy(x_left, y_lower, 3857, 4326)
    # x_right_d, y_upper_d = project_xy(x_right, y_upper, 3857, 4326)

    # # Find Grid size in degrees
    # cell_size_d = (((x_right_d - x_left_d) / (x_right - x_left)) + ((y_upper_d - y_lower_d) / (y_upper - y_lower))) *.5*cell_size

    # Dimension of Raster
    n_rows = math.ceil((x_right - x_left) / cell_size)
    n_cols = math.ceil((y_upper - y_lower) / cell_size)

    raster_template_sql = f""" 
        SELECT ST_SetBandNoDataValue(ST_MakeEmptyRaster({n_cols}, {n_rows}, {x_left}, {y_upper}, {cell_size}, {cell_size}, {0}, {0}, 3857), {nodata})
    """

    if circle:
        selection_geom_sql = f"""
            WITH a AS (
                SELECT 
                    ST_SetSRID(ST_Point({query_x}, {query_y}), 4326) AS geom
            ),

            b AS (
                SELECT 
                    ST_Buffer(ST_Transform(a.geom, 3857), {height/2}) AS geom
                FROM a
            ),

            c AS (
                SELECT
                    ST_Difference(ST_Envelope(ST_Buffer(b.geom, {cell_size})), b.geom) as geom
                FROM b
            )

            SELECT
                ST_Transform(b.geom, {table_srid}) as geom,
                ST_Transform(c.geom, 3857) AS geom_out
            FROM
                b,
                c

        """
        postprocessing_sql = f"""
            SELECT 
                ST_SetValue(
                    grid.ras,
                    q.geom_out,
                    {nodata}
                ) as ras
            FROM 
                grid,
                q
        """
        postprocessing_sql = f"""
            SELECT 
                ST_SetValue(
                    grid.ras,
                    q.geom_out,
                    {nodata}
                ) as ras
            FROM 
                grid,
                q
        """
        postprocessing_sql = f"""
            SELECT 
                grid.ras
            FROM
                grid
        """
    else: # POlygon
        print('polygon')
        selection_geom_sql = f"""
            WITH a AS (
                SELECT ST_GeomFromText('POLYGON(({x_left} {y_lower}, {x_left} {y_upper}, {x_right} {y_upper}, {x_right} {y_lower}, {x_left} {y_lower}))', 3857) as geom
            )

            SELECT ST_Transform(a.geom, {table_srid}) as geom
            FROM a
        """

        postprocessing_sql = f"""
            SELECT 
                grid.ras
            FROM
                grid
        """


    # Convert Feature to SQL
    feature_to_raster_sql = f"""
        WITH q AS (
            {selection_geom_sql}
        ),
        
        features AS (
            SELECT 
                ST_Transform(ST_Intersection(t.wkb_geometry, q.geom), 3857) AS geom
            FROM 
                public.{table} t,
                q
            WHERE 
                ST_Intersects(t.wkb_geometry, q.geom)
                AND
                {class_query}
        ),

        grid1 AS (
            SELECT 
                ST_UNION(
                    ST_AsRaster(
                        features.geom, 
                        ({raster_template_sql}), 
                        '8BUI'::text, 
                        {positive}, 
                        {nodata}, 
                        true
                    ),
                    'MAX'
                ) AS ras

            FROM features
        ),

        grid AS (
            SELECT ST_MapAlgebra(
                grid1.ras,
                1,
                '8BUI'::text,
                '[rast1.val]'::text ,
                {negative}
            ) as ras
            FROM grid1
        ),

        to_raster1 AS (
            {postprocessing_sql}
        ),

        to_raster AS (
            SELECT ST_UNION(
                ST_Transform(
                    to_raster1.ras,
                    {out_srid}
                ),   
                'MAX'
            ) AS ras
            FROM to_raster1
        )

        SELECT 
            ST_AsTIFF(
                to_raster.ras,
                'LZW'
            )
        FROM to_raster, grid, q
        
    """.replace('\n', '')

    # Convert Feature to SQL
    feature_to_raster_sql = f"""
    WITH q AS (                        
        {selection_geom_sql}              
    ),                

    features AS (            
        SELECT                 
            ST_Transform(ST_Intersection(t.wkb_geometry, q.geom), 3857) 
            AS geom            
        FROM                 
            public.{table} t,                
            q            
        WHERE                 
            ST_Intersects(t.wkb_geometry, q.geom)                
            AND                
            {class_query}        
    ),

    grid1 AS (
        SELECT ST_AsRaster(
            ST_Collect(features.geom),                         
            {cell_size},                         
            {cell_size},                         
            '8BUI'::text,                         
            {positive},                         
            {nodata},                         
            {x_left},                         
            {y_upper},                         
            0,                        
            0,                        
            True                 
        ) as ras
        FROM features
    ),

    base_raster AS (
        SELECT ST_AsRaster(
            ST_Collect(ST_Transform(q.geom, 3857)),                         
            {cell_size},                         
            {cell_size},                         
            '8BUI'::text,                         
            {negative},                         
            {nodata},                         
            {x_left},                         
            {y_upper},                         
            0,                        
            0,                        
            True                 
        ) as ras
        FROM q
    ),

    grid AS (
        SELECT ST_MapAlgebra(
            grid1.ras,
            1,
            base_raster.ras,
            1,
            '[rast1.val]+[rast2.val]'::text ,
            '8BUI'::text,
            'UNION'::text,
            null,
            null,
            {nodata}
        ) as ras
        FROM 
            grid1,
            base_raster
    ),

    to_raster1 AS (
        {postprocessing_sql}
    ),

    to_raster AS (
        SELECT
            ST_Transform(
                to_raster1.ras,
                {out_srid}
            ) as ras
        FROM to_raster1
    )

    SELECT 
        ST_AsTIFF(
            to_raster.ras
        )
    FROM to_raster

    """.replace('\n', '')


    # # Convert Feature to SQL
    # feature_to_raster_sql = f"""
    #     WITH q AS (
    #         {selection_geom_sql}
    #     ),
        
    #     features AS (
    #         SELECT 
    #             ST_Transform(ST_Intersection(t.wkb_geometry, q.geom), 3857) AS geom
    #         FROM 
    #             public.{table} t,
    #             q
    #         WHERE 
    #             ST_Intersects(t.wkb_geometry, q.geom)
    #             AND
    #             {class_query}
    #     ),

    #     grid1 AS (
    #         SELECT 
    #             ST_AsRaster(
    #                 ST_Collect(features.geom), 
    #                 {cell_size},
    #                 {cell_size},
    #                 '8BUI'::text, 
    #                 {positive}, 
    #                 {nodata},
    #                 {x_left},
    #                 {y_upper}, 
    #                 0,
    #                 0,
    #                 true
    #             ) AS ras
    #         FROM features
    #     ),

    #     grid AS (
    #         SELECT ST_MapAlgebra(
    #             grid1.ras,
    #             1,
    #             '8BUI'::text,
    #             '[rast1.val]'::text ,
    #             {negative}
    #         ) as ras
    #         FROM grid1
    #     ),

    #     to_raster1 AS (
    #         {postprocessing_sql}
    #     ),

    #     to_raster AS (
    #         SELECT
    #             ST_UNION(
    #                 ST_Transform(
    #                     to_raster1.ras,
    #                     {out_srid}
    #                 ),
    #                 'MAX'
    #             ) AS ras
    #         FROM to_raster1
    #     )

    #     SELECT 
    #         ST_AsTIFF(
    #             to_raster.ras,
    #             'LZW'
    #         )
    #     FROM to_raster, grid, q
        
    # """.replace('\n', '')

    print(feature_to_raster_sql)

    raster = query_db(feature_to_raster_sql)[0][0]

    # Write Raster
    if not '.tif' in output_raster.lower():
        output_raster+='.tif'
        
    with open(output_raster, 'wb') as f:
        f.write(bytes(raster))

    return True
