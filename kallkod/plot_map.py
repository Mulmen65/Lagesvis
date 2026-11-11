from pathlib import Path
import importlib.util,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap,Normalize

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent/'leverans/lagesvis_malmo'
spec=importlib.util.spec_from_file_location('lagesvis',PACKAGE/'streamlit_app.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data=m.load_data(PACKAGE/'lagesvis_data.json');result=m.calculate(data)
rows={r['id']:r for r in result['areas']};profiles={p['id']:p for p in data['profiles']}
geometry=json.loads((ROOT/'map_geometry_3006.json').read_text())
patches=[];left=[];right=[]
for cell in geometry:
    g=cell['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
    score=m.availability(data,result['config'],profiles[cell['deso']],cell['centre_km'])['score']
    for polygon in polys:
        coords=[];codes=[]
        for ring in polygon:
            coords.extend([(x/1000,y/1000) for x,y in ring])
            codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(ring)-2)+[PlotPath.CLOSEPOLY])
        patches.append(PathPatch(PlotPath(coords,codes)))
        left.append(score);right.append(rows[cell['deso']]['annual_ton_hh'])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.labelcolor':'#526964','text.color':'#183b3b'})
fig,axes=plt.subplots(1,2,figsize=(14,10),facecolor='#f5f5ef')
fig.subplots_adjust(left=.065,right=.96,bottom=.20,top=.80,wspace=.14)
fig.text(.065,.941,'Transportläge och resande i Malmö',fontsize=23,fontweight='bold',ha='left')
fig.text(.065,.899,'Lägesvis Malmö 1.0  ·  209 DeSO  ·  250-metersrutor  ·  referensår 2024',fontsize=12,color='#61756f')
fig.text(.065,.855,'Tillgänglighet och klimat är skilda mått. Hushållsprofilen följer boende i respektive DeSO.',fontsize=10.5,color='#526964')
cmaps=[LinearSegmentedColormap.from_list('access',['#e2eddb','#aac39f','#79a78b','#397e67','#103c38']),LinearSegmentedColormap.from_list('climate',['#377f68','#92b286','#c4ca94','#e0bb83','#ba745a'])]
vals=[left,right];norms=[Normalize(0,100),Normalize(min(right),max(right))]
for i,ax in enumerate(axes):
    coll=PatchCollection(patches,cmap=cmaps[i],norm=norms[i],edgecolor='white',linewidth=.11)
    coll.set_array(np.array(vals[i]));ax.add_collection(coll);ax.autoscale_view();ax.set_aspect('equal');ax.set_facecolor('#e8efee')
    ax.tick_params(labelsize=8,length=3,colors='#71827b');ax.ticklabel_format(useOffset=False,style='plain')
    for spine in ax.spines.values():spine.set_edgecolor('#ccd8d1')
    ax.set_xlabel('Östligt läge, km · SWEREF 99 TM',fontsize=8)
    if i==0:ax.set_ylabel('Nordligt läge, km · SWEREF 99 TM',fontsize=8)
    else:ax.tick_params(labelleft=False)
    ax.set_title(['Tillgänglighetsindex','Boendes beräknade klimatpåverkan'][i],fontsize=14,loc='left',pad=15,fontweight='bold')
    cb=fig.colorbar(coll,ax=ax,orientation='horizontal',fraction=.055,pad=.085,shrink=.95,aspect=35)
    cb.outline.set_visible(False);cb.ax.tick_params(labelsize=8,length=2)
    cb.set_label(['Relativt index 0–100 · högre = bättre utbud och närhet','ton CO₂e/(hushåll·år) · RVU-baserad screening'][i],fontsize=9,labelpad=7)
    xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
    ax.plot([xmin+1,xmin+3],[ymin+1,ymin+1],color='#37574d',linewidth=2.2)
    ax.text(xmin+2,ymin+1.4,'2 km',ha='center',fontsize=8,color='#37574d')
fig.text(.065,.132,'Rutorna visar områdesprofiler, inte uppmätta hushåll eller resor på 250-metersnivå.',fontsize=9.5,fontweight='bold',va='top')
fig.text(.065,.105,'Klimatberäkningen omfattar gång, cykel, bil, buss, tåg, flyg och övrigt. RVU gäller ålder 15–84 år.\nÅrsöverföring, geografisk fördelning och vissa faktorer är antaganden. Systemgränserna skiljer sig mellan färdmedel.',fontsize=9,color='#526964',linespacing=1.6,va='top')
fig.text(.065,.043,'Källor: SCB · Region Skåne RVU 2023 · GTFS/Skånetrafiken · OpenStreetMap · Vägvis 2.3.1 · ADEME\nGeometri: SCB DeSO 2025, kustavskild med © OpenStreetMap contributors, ODbL. Fullständiga källor och beräkningar finns i appen.',fontsize=8,color='#647970',linespacing=1.6,va='top')
path=PACKAGE/'Transportlage_Malmo.png';fig.savefig(path,dpi=190,facecolor=fig.get_facecolor());plt.close(fig)
print(path)
