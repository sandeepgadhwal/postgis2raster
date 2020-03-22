
import os
import traceback

try:
    from matplotlib import pyplot as plt
    import gdal
    import numpy as np
except Exception as e:
    exec1 = traceback.format_exc()
    print(exec1)
    print("""
        \nplease instal gdal numpy and matplotlib to use this module.
    """)

color_array = [
    [0., 0., 0., 0.],
    [0., 0., 0., 1.],
    [1., 1., 1., 1.]
]
color_array = np.array(color_array)

def visualize_image(image_path, imsize=5):
    # Read Image
    ds = gdal.Open(image_path)
    n_bands = ds.RasterCount
    image_array = ds.ReadAsArray()
    if n_bands == 1:
        image_array = image_array[None]
    band_names = ['Single Band Raster']
    
    print(f"Found {n_bands} bands in raster {image_path}")
    
    # If Image has multiple bands read the band names from the supporting csv
    if n_bands > 1:
        band_mapping_csv = image_path + ".classes_to_bands_mapping.csv"
        if os.path.exists(band_mapping_csv):
            with open(band_mapping_csv) as f:
                csv = [x.split(', ') for x in f.read().split('\n')]
            band_names = []
            for row in csv[1:-1]:
                band_names.append(row[1])
        else:
            band_names = [f"band_{x}" for x in range(0, n_bands)]
    
    # Start Plotting
    fig, axs = plt.subplots(n_bands, figsize=[imsize, imsize*n_bands])
    for i in range(0, n_bands):
        if n_bands == 1:
            ax = axs
        else:
            ax = axs[i]
        nodataval = ds.GetRasterBand(i+1).GetNoDataValue()
        arr = image_array[i]
        
        _arr = np.zeros_like(arr)
        _arr[arr == nodataval] = 0
        _arr[arr == arr[arr!=nodataval].min()] = 1
        _arr[arr == arr[arr!=nodataval].max()] = 2
        
        _arr = color_array[_arr.flatten()].reshape((*_arr.shape, 4))
        ax.imshow(_arr)
        ax.set_title(band_names[i])