# Källkod och kontroller för Lägesvis Malmö 1.0

Detta är granskningsunderlag. Streamlit-appen behöver bara de tre programfilerna i huvudpaketet. Inga Workflows används.

Packa vid behov upp detta arkiv i samma mapp som huvudpaketet. Då hamnar granskningsfilerna i `kallkod/`.

- `streamlit_app.py`: den fristående Pythonmotorn och Streamlit-starten, samma kod som huvudfilen.
- `model.js`: webbläsarens motsvarande beräkningsmotor.
- `ui.html`, `ui.js`, `style.css`, `method.html`: läsbara gränssnitts- och metodfiler. Dessa är inbäddade i huvudpaketets datafil.
- `test_lagesvis.py`: 20 modelltester inklusive jämförelse av Python och JavaScript. Den jämförelsen behöver Node.js. Kör från huvudpaketets mapp: `python kallkod/test_lagesvis.py`.
- `KONTROLLER.json`: kontrollresultat och uttryckliga verifieringsbegränsningar.
- `grid_geometry.json`: färdiga rutor och kustklippta DeSO samt geometrikvitto.
- `deso_wgs84.geojson`, `land_wgs84.geojson`: geografiska källutdrag ur användarens modellpaket.
- `register.json`: områdesdata från samma paket. Variablernas status beskrivs i metod och källregister.
- `car_factors.json`: fryst kvitto på bilfaktor och valbar körsträckefördelning.
- `core.js`, `households.js`, `distance.js`, `scenarios.js` och deras JSON-indata: ursprunglig Vägvis-kod och underlag som behövs för att reproducera bilkvittot. Ursprungliga MIT-villkor gäller.

För att återskapa bilkvittot: `node kallkod/build_car_reference.cjs`.

För att bygga om rutnätet krävs GDAL:s Pythonpaket `osgeo`. Kör `python kallkod/build_grid.py` med en Pythonmiljö som har GDAL installerat. Rutnätet beräknas i EPSG:3006 och snittas mot landmasken. Normal användning av appen behöver inte GDAL.

För att paketera om data och gränssnitt efter källkodsändringar: `python kallkod/build_dataset.py --output .`. Då skrivs huvudpaketets tre programfiler med granskningsmappens versioner. En separat HTML-karta skapas sedan med `python streamlit_app.py --html Lagesvis_Malmo.html`.

`project_map_geometry.py` och `plot_map.py` skapar den fristående kartbilden; de är utvecklingsverktyg och behöver GDAL respektive Matplotlib och NumPy. Kartbilden är en separat visualisering av samma beräkningsdata.

En riktig grafisk webbläsarkontroll och komplett Streamlit-publicering kunde inte genomföras i leveransmiljön. Domän- och API-kontraktstest av gränssnittet ska inte förväxlas med sådana kontroller. Kartbilden är visuellt granskad.

Data och kod behåller sina olika licenser. OSM-härledda geografier: ODbL 1.0. Leaflet: BSD-2-Clause. Ny modellkod: MIT. Se medföljande licenser och appens källregister.
