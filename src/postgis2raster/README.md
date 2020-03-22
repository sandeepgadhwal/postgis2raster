# postgis2raster
converts postgis vector geometry to Gdal Rasters 

# Eaxmple of Fishnets

## Single Band Circle
```python
postgis2raster.analysis_circle(
    table='mytable',
    output_raster='myimage.tif',
    query_x=16.55268272,
    query_y=40.82717010,
    radius=2500,
    cell_size=30
)
```
![Single band circle](https://raw.githubusercontent.com/sandeepgadhwal/postgis2raster/images/single_band_circle.png)

#

## Multi Band Circle
```python
postgis2raster.analysis_circle(
    table='mytable',
    output_raster='myimage.tif',
    query_x=16.55268272,
    query_y=40.82717010,
    radius=2500,
    cell_size=30,
    classes_to_bands=True
)
```
![Multi band circle](https://raw.githubusercontent.com/sandeepgadhwal/postgis2raster/images/multi_band_circle.png)

#

## Single Band Polygon
```python
postgis2raster.analysis_polygon(
    table='mytable',
    output_raster='myimage.tif',
    query_x=16.55268272,
    query_y=40.82717010,
    height=5000,
    width=5000,
    cell_size=30
)
```
![Single band circle](https://raw.githubusercontent.com/sandeepgadhwal/postgis2raster/images/single_band_polygon.png)


```python
postgis2raster.analysis_circle(
    table='mytable',
    output_raster='myimage.tif',
    query_x=16.55268272,
    query_y=40.82717010,
    height=5000,
    width=5000,
    cell_size=30,
    classes_to_bands=True
)
```
![Multi band circle](https://raw.githubusercontent.com/sandeepgadhwal/postgis2raster/images/multi_band_polygon.png)

