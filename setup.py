from distutils.core import setup
setup(
  name = 'postgis2raster',
  packages = ['postgis2raster'],
  version = '0.1',
  license='MIT',
  description = 'This library helps user create raster files directly off postgis tables, rasterization and fishnet analysis.',
  author = 'SANDEEP KUMAR',
  author_email = 'sandeepgadhwal1@gmail.com',
  url = 'https://urbantalks.in',
  download_url = 'https://github.com/sandeepgadhwal/postgis2raster/archive/v_01.tar.gz',
  keywords = ['postgis', 'raster', 'fishnet'],
  install_requires=[
          'psycopg2',
          'pyproj',
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',    
    'Intended Audience :: GIS Analyst', 
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3', 
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
  ],
)