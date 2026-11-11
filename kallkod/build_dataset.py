"""Assemble frozen, inspectable source data; no hidden API calls."""
import hashlib
import json
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',help='Mapp där de tre programfilerna ska skapas')
args=parser.parse_args()
OUT=Path(args.output).resolve() if args.output else ROOT.parent/'leverans'/'lagesvis_malmo'
OUT.mkdir(parents=True,exist_ok=True)
geo=json.loads((ROOT/'grid_geometry.json').read_text())
rows=json.loads((ROOT/'register.json').read_text())
car=json.loads((ROOT/'car_factors.json').read_text())
geoby={a['id']:a for a in geo['areas']}
profiles=[]
for r in rows:
    a=geoby[r['kod']]
    profiles.append(dict(id=r['kod'],name=a['name'],regso=a['regso'],
                         households=r['hh'],population=r['bef'],cars=r['bil'],income=r['income'],
                         eligible_population=r['bef']*287207/362133,
                         eligible_population_status='kommunal åldersandel 2023 överförd till DeSO 2024, inte lokal observation',
                         km_anchor=r['km'],km_gtfs=car['km_by_deso'][r['kod']],
                         centre_km=r['centreKm'],service_km=r['serviceKm'],node_km=r['transitKm'],
                         transit_supply=r['transitSupply'],land_m2=a['land_m2'],lat=a['lat'],lon=a['lon']))

def source(id, author,year,title,url,use,locator='',status='primary_published'):
    return dict(id=id,author=author,year=year,title=title,url=url,use=use,locator=locator,status=status,accessed='2026-11-11')

sources=[
source('RVU_MALMO_2023','Region Skåne','2024','Så reser vi i Malmö stad Resvaneundersökning 2023',
       'https://utveckling.skane.se/siteassets/publikationer/kommunrapporter-2023-rvu/sa-reser-vi-i-malmo-stad-rvu-2023.pdf',
       'Personkilometer för samtliga sju huvudfärdmedel. Målpopulation 15–84 år; en undersökningsperiod, inte uppmätt årsresande.',
       'Tabell 2 s. 29; tabell 1 s. 5; definitioner s. 3 och viktning s. 6–7'),
source('SCB_POP','Statistiska centralbyrån','2025','Befolkningen ökade 2024 trots minskade födslar',
       'https://www.scb.se/pressmeddelande/befolkningen-okade-2024---trots-minskade-fodslar/',
       'Malmö 362 133 invånare 2023 och 365 644 år 2024. Kommunal andel av RVU:s ålderspopulation = 287 207/362 133.',
       'Tabell Folkmängd i de tio största kommunerna 2024'),
source('SCB_CARS','Statistiska centralbyrån och Trafikanalys','2026','TAB6589 Personbilar registrerade på folkbokförda personer',
       'https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__TK__TK1001__TK1001Z/PersBilarDesoN/',
       'DeSO 2025, bilar i trafik 2024 i användarens Vägvis-paket. Privatleasing och enskild firma ingår enligt paketets definition; arbetsgivarregistrerade förmånsbilar ingår inte.',
       '100 524 bilar i Malmö; inläst ur medföljande household-project.json','bundled_register'),
source('SCB_HH_POP','Statistiska centralbyrån','2026','TAB6568 hushåll och TAB6574 folkmängd',
       'https://www.statistikdatabasen.scb.se/Resources/PX/bulk/ssd/sv/',
       '172 941 hushåll och 365 644 invånare i Malmö, 209 DeSO, referensår 2024. Hushållsstorlek härleds som population/hushåll.',
       'Medföljande Vägvis household-project.json','bundled_register'),
source('SCB_INCOME','Statistiska centralbyrån','2026','TAB6684 Ekonomisk standard efter region',
       'https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__HE__HE0110__HE0110I/Tab3InkDesoRegso/',
       'Median ekonomisk standard, tusen kronor i 2024 års priser. Områdesegenskap, inte årslön eller enskilda hushålls inkomst.',
       'Medföljande Vägvis distance-indicators.json','bundled_register'),
source('SCB_DESO','Statistiska centralbyrån','u.å.','Geodata för demografiska statistikområden DeSO',
       'https://www.scb.se/vara-tjanster/oppna-data/oppna-geodata/demografiska-statistikomraden-deso/',
       '209 Malmö-DeSO ur användarens ursprungliga SCB-geometri 2025_v2. Indelning giltig 2025-01-01.',
       'Medföljande omraden.json','bundled_geography'),
source('VAGVIS','Vägvis','2026','Vägvis 2.3.1 GTFS användarlevererat modellpaket',
       '',
       'Bilinnehav, kommunankare och en valbar körsträckefördelning. Bilens bruttofaktor beräknades på nytt med paketets kod. Koefficienterna för lokal körsträcka är valda antaganden, inte skattade från observerade DeSO-körsträckor.',
       'Vagvis_2.3.1_GTFS_GitHub(1).zip; core.js, households.js, distance.js','user_supplied_model'),
source('GTFS','Samtrafiken och Skånetrafiken','2024','GTFS regional tidtabell för Skåne',
       'https://www.trafiklab.se/api/gtfs-datasets/gtfs-regional/',
       'Planerat utbud från paketets vecka 14–20 oktober 2024, 06–20, inom 500 meter fågelväg från 30 bostadsgatupunkter per DeSO. Ingen mätning av restid, pålitlighet eller årsmedel.',
       'Vägvis underlag/gtfs/indikatorer.json','bundled_planned_schedule'),
source('OSM','OpenStreetMap contributors','2026','OpenStreetMap geodata och landpolygoner',
       'https://www.openstreetmap.org/copyright',
       'Dagligvarubutiker och kollektivtrafiknoder, 2026 års geografiska proxyvärden i paketet, samt landmask. © OpenStreetMap contributors, ODbL.',
       'Längdviktade fågelvägsavstånd från bostadsgator; inte verifierad total servicetäckning.','bundled_geographic_proxy'),
source('OSM_LAND','OpenStreetMap contributors','u.å.','Land polygons',
       'https://osmdata.openstreetmap.de/data/land-polygons.html',
       'Kustmask. DeSO och rutor snittas mot masken i EPSG:3006. Inlandsvatten är kvar i landmasken. Analysytan är inte SCB:s officiella landareal.',
       'Medföljande land.json','bundled_geography'),
source('SKANE_SCOPE','Skånetrafiken','2025','Hållbarhetsprogram 2026–2030 version 5',
       'https://www.skanetrafiken.se/globalassets/dokumentbank/miljo/hallbarhetsprogram-2026-2030_210x297mm_6-mars-1.pdf',
       'Platsbaserat scope 1–3-medel 17,5 g CO2e/pkm för hela trafiken, basår 2024. Överförs som gemensam regional proxy till både buss och tåg; inte separata modalspecifika LCA-faktorer.',
       'S. 9; not 9 om tillverkning av nya tåg. Beslut 27 november 2025.'),
source('SKANE_WTW','Skånetrafiken','u.å.','Miljörapport företag 2025',
       'https://www.skanetrafiken.se/foretag/miljorapport-foretag/',
       'Beläggning 1,3 personer per bil används som överförd schablon. Sidans 5,04 g/pkm för kollektivtrafik gäller WTW och adderas inte till scope 1–3-faktorn.',
       'Beräkningssida; bilbeläggningen hänvisar vidare till Trivector Traffic 2010, inte lokal observation.'),
source('ADEME_WALK','ADEME Impact CO2','u.å.a','Empreinte carbone Marche',
       'https://impactco2.fr/outils/transport/marche','0 g CO2e/pkm inom fordon/energi-avgränsningen. Mat, skor och infrastruktur ingår inte.'),
source('ADEME_CYCLE','ADEME Impact CO2','u.å.b','Empreinte carbone Vélo mécanique',
       'https://impactco2.fr/outils/transport/velo','Publicerat referensvärde 0,17 g CO2e/pkm, tillverkning. Fransk källa överförs som referens, inte svensk uppmätt faktor.'),
source('ADEME_EBIKE','ADEME Impact CO2','u.å.c','Empreinte carbone Vélo à assistance électrique',
       'https://impactco2.fr/outils/transport/veloelectrique','Publicerat avrundat referensvärde 11 g CO2e/pkm inklusive tillverkning och användning. Andelen elcykel är ett separat användarantagande.'),
source('ADEME_AIR','ADEME Impact CO2','u.å.d','Empreinte carbone Avion trajet moyen',
       'https://impactco2.fr/outils/transport/avion-moyencourrier','Publicerat avrundat referensvärde 185 g CO2e/pkm, varav 83 g kondensstrimmor, för 1 000–2 000 km. Inkluderar energi och flygplan, inte flygplatser. Proxy för all flygning, inte observerad Malmö-mix.'),
source('MODELLVAL','Lägesvis Malmö','2026','Dokumenterade beräkningsval och antaganden','',
       'RVU-årsöverföring, geografisk fördelning, övrigt-faktor, lika indexvikter, framtidsscenario och antagandebaserade osäkerhetsfördelningar definieras i den öppna modellen. Inga regressionskoefficienter har skattats från dessa underlag.',status='explicit_model_choice')]

mode_names=dict(walk='Gång',cycle='Cykel inklusive elcykel',car='Bil inklusive förare och passagerare',bus='Buss',rail='Tåg',air='Flyg',other='Övriga färdmedel')
daily=dict(walk=89900,cycle=538800,car=3615000,bus=1068100,rail=3611400,air=1720700,other=114300)
mode_ids=list(mode_names)
defaults=dict(start_year=2024,years=50,target_year=2050,days_per_year=365,season_factor=1.0,excluded_age_addition=0.0,
              allocation='register',occupancy=1.3,car_g_vkm=car['factors_g_vkm']['total'],
              cycle_g_pkm=.17,ebike_g_pkm=11.0,ebike_share=0.0,bus_g_pkm=17.5,rail_g_pkm=17.5,
              air_g_pkm=185.0,air_nonco2_fraction=83/185,include_air_nonco2=True,
              other_method='land_average',other_g_pkm=0.0,air_income_beta=0.0,transit_beta=.5,service_beta=.25,
              future_enabled=False,activity_target={m:1.0 for m in mode_ids},factor_target={m:1.0 for m in mode_ids},
              activity_scale={m:1.0 for m in mode_ids},index_weights=dict(supply=1.0,service=1.0,node=1.0,centre=1.0),
              draws=500,seed=20261111,demand_cv=.20,local_cv=.25,
              factor_cv=dict(walk=0.0,cycle=.5,car=.2,bus=.4,rail=.4,air=.35,other=.75))
assets_source=json.loads((ROOT/'source_assets.json').read_text())
css=assets_source['kallkod/source/style.css']
data=dict(schema='lagesvis-data-1',version='1.0.0',name='Lägesvis Malmö',packaged='2026-11-11',base_year=2024,deso_version='2025',
          profiles=profiles,areas=geo['areas'],cells=geo['cells'],grid_receipt=geo['receipt'],
          rvu=dict(year=2023,survey_population=287207,total_population=362133,daily_pkm=daily,
                   trips_per_day=dict(walk=56300,cycle=142100,car=156600,bus=101700,rail=61400,air=1500,other=7900),
                   scope='15–84 år, huvudfärdmedel, septemberundersökning. Årsberäkning kräver överföring.'),
          modes=[dict(id=m,name=mode_names[m]) for m in mode_ids],sources=sources,defaults=defaults,
          car_factor_receipt=car,distance_status='Antagna koefficienter; kommunvärde 11 892 km per bil; valbar GTFS-fördelning.',
          source_hashes=(json.loads((ROOT/'source_hashes.json').read_text()) if (ROOT/'source_hashes.json').exists() else {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT.parent/'upload').glob('*') if p.suffix.lower() in ['.zip','.docx']}),
          licences=dict(code='MIT',leaflet=assets_source['licenser/Leaflet.txt'],vagvis=assets_source['LICENSE.txt'],
                        geography='SCB open data; OSM-derived land intersections and geographic proxies: © OpenStreetMap contributors, ODbL 1.0, https://opendatacommons.org/licenses/odbl/1-0/'),
          assets=dict(leaflet_css=css[:css.index(':root')],leaflet_js=assets_source['kallkod/source/leaflet.js']))
for cell in data['cells']:
    lat1=cell['lat']*3.141592653589793/180;lat2=55.6052*3.141592653589793/180
    from math import sin,cos,asin,sqrt
    dlat=lat2-lat1;dlon=(13.0-cell['lon'])*3.141592653589793/180
    cell['centre_km']=6371.0088*2*asin(min(1,sqrt(sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlon/2)**2)))
for key,file in [('shell','ui.html'),('css','style.css'),('model_js','model.js'),('ui_js','ui.js'),('method_html','method.html')]:
    path=ROOT/file
    data['assets'][key]=path.read_text() if path.exists() else ''
(OUT/'lagesvis_data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
(OUT/'streamlit_app.py').write_text((ROOT/'streamlit_app.py').read_text())
(OUT/'requirements.txt').write_text('streamlit==1.50.0\n')
print('Built',OUT, 'profiles',len(profiles),'cells',len(data['cells']))
