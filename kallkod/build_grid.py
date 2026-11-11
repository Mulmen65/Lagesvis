"""Build real 250 m EPSG:3006 cells clipped to SCB DeSO and the OSM coast.

Build-time dependency: GDAL/OGR Python bindings. The delivered app does not
need GDAL because it reads the verified precomputed geometry.
"""
import json
import math
from pathlib import Path
from osgeo import ogr, osr

ogr.UseExceptions()
ROOT = Path(__file__).resolve().parent
repairs = []
source = osr.SpatialReference(); source.ImportFromEPSG(4326)
metric = osr.SpatialReference(); metric.ImportFromEPSG(3006)
for sr in [source, metric]:
    sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
forward = osr.CoordinateTransformation(source, metric)
back = osr.CoordinateTransformation(metric, source)


def geom(obj, label):
    result = ogr.CreateGeometryFromJson(json.dumps(obj))
    result.AssignSpatialReference(source)
    result.Transform(forward)
    if not result.IsValid():
        repairs.append(label)
        return result.MakeValid()
    return result


def polygons(g):
    kind = g.GetGeometryName()
    if kind == 'POLYGON':
        return [g.Clone()]
    result = []
    for i in range(g.GetGeometryCount()):
        result.extend(polygons(g.GetGeometryRef(i)))
    return result


def polygon_only(g):
    result = ogr.Geometry(ogr.wkbMultiPolygon)
    for p in polygons(g):
        result.AddGeometry(p)
    return result


def to_wgs(g):
    g = g.Clone()
    g.Transform(back)
    return json.loads(g.ExportToJson(['COORDINATE_PRECISION=7']))


def rect(e, n):
    return ogr.CreateGeometryFromWkt(f'POLYGON(({e} {n},{e+250} {n},{e+250} {n+250},{e} {n+250},{e} {n}))')


land_features = json.loads((ROOT / 'land_wgs84.geojson').read_text())['features']
land = geom(land_features[0]['geometry'], 'OSM land feature 0')
for f in land_features[1:]:
    land = land.Union(geom(f['geometry'], 'OSM land feature'))
deso = json.loads((ROOT / 'deso_wgs84.geojson').read_text())['features']
areas, cells = [], []
source_area = cell_area = 0
for f in deso:
    code = f['properties']['id']
    original = geom(f['geometry'], code)
    clipped = polygon_only(original.Intersection(land))
    if clipped.IsEmpty():
        raise ValueError('DeSO without land: ' + code)
    area = clipped.GetArea()
    source_area += area
    point = clipped.PointOnSurface()
    point.Transform(back)
    areas.append({'id': code, 'name': f['properties']['regsoName'],
                  'regso': f['properties']['regso'], 'land_m2': area,
                  'lat': point.GetY(), 'lon': point.GetX(),
                  'geometry': to_wgs(clipped.SimplifyPreserveTopology(.4))})
    minx, maxx, miny, maxy = clipped.GetEnvelope()
    for e in range(math.floor(minx / 250) * 250, math.floor(maxx / 250) * 250 + 1, 250):
        for n in range(math.floor(miny / 250) * 250, math.floor(maxy / 250) * 250 + 1, 250):
            part = polygon_only(clipped.Intersection(rect(e, n)))
            area = part.GetArea()
            if area <= .0001:
                continue
            cell_area += area
            p = part.PointOnSurface(); p.Transform(back)
            cell_id = f'E{e}_N{n}'
            cells.append({'id': cell_id + '_' + code, 'cell_id': cell_id,
                          'deso': code, 'easting': e, 'northing': n,
                          'land_m2': area, 'lat': p.GetY(), 'lon': p.GetX(),
                          'geometry': to_wgs(part.SimplifyPreserveTopology(.2))})
    print(code, 'land ha', round(clipped.GetArea()/10000, 2), flush=True)

receipt = {'crs': 'EPSG:3006', 'cell_size_m': 250,
           'grid_origin': 'Multiples of 250 m in EPSG:3006',
           'source': 'SCB DeSO 2025_v2 intersected with supplied OSM land polygons',
           'cell_boundary_policy': 'Split cells at DeSO boundaries; no population interpolation',
           'household_and_population_counts_per_cell': None,
           'areas': len(areas), 'unique_cells': len({c['cell_id'] for c in cells}),
           'cell_fragments': len(cells), 'land_m2': source_area,
           'repaired_source_geometries': repairs,
           'sum_fragment_m2': cell_area, 'closure_error_m2': cell_area-source_area,
           'display_simplification_m': .2, 'area_before_display_simplification': True}
assert len(areas) == 209
assert abs(cell_area-source_area) < .1
(ROOT / 'grid_geometry.json').write_text(json.dumps({'areas': areas, 'cells': cells, 'receipt': receipt}, ensure_ascii=False, separators=(',', ':')))
print(json.dumps(receipt, indent=2))
