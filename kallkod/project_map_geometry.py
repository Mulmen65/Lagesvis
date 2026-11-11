import json
from pathlib import Path
from osgeo import ogr,osr
ROOT=Path(__file__).resolve().parent
a=osr.SpatialReference();a.ImportFromEPSG(4326)
b=osr.SpatialReference();b.ImportFromEPSG(3006)
for sr in [a,b]:sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
t=osr.CoordinateTransformation(a,b)
data=json.loads((ROOT.parent/'leverans/lagesvis_malmo/lagesvis_data.json').read_text())
out=[]
for cell in data['cells']:
    g=ogr.CreateGeometryFromJson(json.dumps(cell['geometry']));g.Transform(t)
    out.append(dict(id=cell['id'],deso=cell['deso'],centre_km=cell['centre_km'],geometry=json.loads(g.ExportToJson())))
(ROOT/'map_geometry_3006.json').write_text(json.dumps(out,separators=(',',':')))
