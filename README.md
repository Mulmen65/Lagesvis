# Lägesvis Malmö 1.0

En fristående karta och Pythonmodell för transportläge och boendes resande i Malmö.

Appen visar hela kommunen med 250 × 250 meters rutor och DeSO som referenslager. Hushållsprofilen följer dagens boende i respektive DeSO. Alla sju huvudfärdmedelsgrupper i Malmörapportens resvaneundersökning ingår: gång, cykel, bil, buss, tåg, flyg och övrigt. Resultat visas per år och för en valbar period. Standardperioden är 50 år.

Gränssnittet följer Vägvis mörkgröna meny, färger, resultatkort och kartupplägg. Vägvis och Road2Zero behöver inte ändras.

## Börja med kartan direkt

1. Packa upp ZIP-filen på datorn.
2. Dubbelklicka på **Lagesvis_Malmo.html**.
3. Välj kartlager, DeSO eller 250 m och jämför olika områden.

HTML-filen innehåller data, beräkningar och kartbibliotek. Den behöver varken Python eller Streamlit. Beräkningarna fungerar utan internet. OpenStreetMap-bakgrund kan aktiveras när internet finns; den är avstängd från början när HTML-filen öppnas direkt från datorn.

**Transportlage_Malmo.png** är en separat kartbild som visar tillgänglighetsindex och beräknad klimatpåverkan per hushåll sida vid sida.

## Publicera i GitHub och Streamlit

Det behövs bara **tre programfiler**, direkt i repositoryts rot:

- `streamlit_app.py`
- `lagesvis_data.json`
- `requirements.txt`

Gör så här:

1. Skapa ett **nytt** GitHub-repository, exempelvis `lagesvis-malmo`.
2. Välj **Add file → Upload files**.
3. Ladda upp de tre programfilerna ovan. Ladda upp filerna, inte hela ZIP-filen. Inga undermappar behövs.
4. Välj **Commit changes**.
5. Skapa en app i Streamlit Community Cloud och välj ditt repository och grenen `main`.
6. Ange **Main file path: `streamlit_app.py`**. Välj Python **3.12** i inställningarna och publicera.

Det finns inga GitHub Actions, inga Workflows och ingen API-nyckel att konfigurera. Data för grundkartan är redan med. Alla filer som behöver laddas upp är mindre än 25 MB.

README, kartbild, fristående HTML och den extra källkodsfilen är till för användning och granskning; de behöver inte laddas upp för att Streamlit-appen ska fungera.

## Så används appen

**Översikt** visar ett relativt tillgänglighetsindex, klimatpåverkan per hushåll och år, områdessummeringar och vald period. De två resultaten har olika innebörd. Indexet beskriver utbud och närhet; klimatet påverkas även av vilka hushåll som bor där.

**Karta & områden** låter dig växla mellan 250-metersrutor och DeSO. Välj exempelvis klimat per hushåll, klimat per invånare, kollektivtrafikutbud, bilinnehav, hushållsstorlek eller ekonomisk standard. Klicka i kartan eller välj ett område i listan för att se dess profil.

**Resultat & jämförelse** visar färdmedlens bidrag, en tidsserie, en tabell över samtliga DeSO och två områden sida vid sida. Här kan ett antagandebaserat scenariointervall beräknas med Monte Carlo. Det är inte ett statistiskt konfidensintervall från resvaneundersökningen.

**Antaganden & scenario** innehåller alla aktiva förval. Ändra värden och klicka på **Tillämpa och beräkna**. Utvecklingsscenariot är avstängt från början. Då är periodresultatet det oförändrade årsresultatet multiplicerat med antalet år. När scenariot aktiveras kan resande och klimatfaktor förändras separat mot ett målår. Exempelknappens värden är illustrativa antaganden, inte officiella prognoser.

**Underlag & datakvalitet** redovisar vad som är observerat, överfört och antaget. Här finns kompletteringsmall, import och export.

**Metod & källor**, även nåbar genom knappen längst ned, beskriver formler, enheter, systemgränser, samtliga schabloner och Harvard-referenser. Inställningarna i den aktuella körningen visas också.

## Spara egna inställningar

Klicka på **Spara projekt**. Då hämtas en JSON-fil med inställningar, kompletterade resevolymer och anteckningar. Använd **Öppna projekt** för att återgå till samma scenario. En omladdning av appen återställer annars grundinställningarna.

Under **Underlag & datakvalitet** går det även att ladda ned en interaktiv HTML-karta med egna inställningar. Projekt-JSON kan användas både i webbkartan och i Pythonberäkningen.

## Viktiga gränser för den första versionen

### Rutnätets upplösning är inte datans upplösning

Geometrin är ett verkligt 250-metersrutnät i SWEREF 99 TM, klippt mot SCB:s DeSO och kustlinjen. Det finns 2 772 unika rutor och 4 468 DeSO-avskilda fragment.

Hushåll, folkmängd, bilar, inkomst och resandeprofil finns på **DeSO-nivå**. Klimatvärdet per hushåll är därför samma inom ett DeSO även när rutorna visas. Tillgänglighetsindexets centrumavstånd beräknas från varje rutfragments analyspunkt; dess övriga komponenter är DeSO-medel. Appen hittar inte på hushållsantal per ruta och beräknar inga rutbaserade kommunsummor.

### Dagens boende följs, men uppgifterna avser olika år

Hushåll, folkmängd, bilinnehav och ekonomisk standard har referensår 2024. Gränserna är DeSO 2025. RVU gäller 2023 och kollektivtrafikutbudet en planerad vecka i oktober 2024. Serviceavstånd och geografiska ursprungspunkter är proxyer från 2026 års underlag. Detta är inte en komplett observation av transportförhållandena 2026.

Hushållsstorlek och bilinnehav varierar mellan områden. Modellen använder däremot inte en påhittad lokal åldersfördelning, upplåtelseform, parkeringstillgång eller arbetsplatstillgänglighet. Sådant harmoniserat underlag saknas i bilagorna.

### Alla RVU-färdmedel ingår, men alla åldrar är inte observerade

RVU gäller personer 15–84 år. Gruppens kommunala befolkningsandel överförs som proxy till varje DeSO. Barn under 15 och personer över 84 har inte fått en egen resandeskattning i standardfallet. Ett särskilt procentuellt tillägg kan väljas, men det är ett antagande.

Elcykel ingår i cykelgruppen. Övrigt behåller de resor som inte särredovisas i den använda tabellen. Fördelningen mellan moped, MC, färja, elsparkcykel, taxi och andra färdmedel kan inte rekonstrueras ur tabellen. Dessa får inga extra påhittade volymer. Ospecificerat resande behålls och dess faktor redovisas som proxy.

### Geografisk fördelning är inte en validerad beteendeprognos

I standardläget fördelas bilens personkilometer med registrerade bilar och kommunens körsträckeankare som vikter. Övriga färdmedel fördelas med ålderspopulationens proxy. Det valbara tillgänglighetsläget använder Vägvis antagna körsträckesamband samt öppet valda samband för övriga färdmedel. Kommunens grundvolym per färdmedel bevaras. Inga regressionskoefficienter har skattats från observerad DeSO-körsträcka.

Låga utsläpp kan bero på begränsade resurser och resmöjligheter. Resultaten visar inte den kausala effekten av att flytta samma hushåll eller att bygga nya bostäder på en viss plats.

### Klimatfaktorerna har olika systemgränser

- **Bil:** Vägvis bruttofaktor 227,764 g CO₂e/fordonskm dividerad med vald beläggning. Den separata återvinningskrediten dras inte av. Slutskedeposten i referensen är noll och infrastruktur ingår inte.
- **Buss och tåg:** samma regionala proxy, Skånetrafikens 17,5 g CO₂e/personkm, scope 1–3, basår 2024. Det är inte separata uppmätta faktorer för respektive färdmedel och inte nödvändigtvis giltigt för resor med andra operatörer eller i andra regioner.
- **Gång:** noll inom fordons- och energiavgränsningen. Mat och annan mänsklig konsumtion ingår inte för något färdmedel.
- **Cykel:** ADEME:s publicerade tillverkningsreferens 0,17 g/personkm. Elcykelreferens 11 g/personkm. Andelen elcykel är inte observerad; standard noll betyder att mekanisk cykel används som referens.
- **Flyg:** ADEME:s avrundade referens 185 g/personkm för 1 000–2 000 km, inklusive höghöjdseffekt. Den används som proxy för hela flygvolymen. Ingen extra höghöjdsmultiplikator läggs till.
- **Övrigt:** härlett personkilometerviktat genomsnitt av de aktiva landfärdmedelsfaktorerna, alternativt en egen faktor. Detta är ett imputationsantagande, inte en publicerad faktor för varje ospecificerat färdmedel.

Totalen är därför en **livscykelrelaterad screening med blandade systemgränser**, inte en harmoniserad fullständig cradle-to-cradle-LCA eller stadens verifierade utsläppsbokslut. Den ska inte jämföras direkt med territoriella utsläpp från vägtrafiken i Malmö.

## Beräkningskedjan

1. Malmö-RVU:s personkilometer per dygn omräknas till ett modellår. Standard är 365 dagar och säsongsfaktor 1. En kommunal åldersandel överförs till 2024 års folkmängd.
2. Varje färdmedels kommunvolym fördelas över DeSO med angivna vikter. Egna kompletteringar ersätter valda DeSO-/färdmedelsvärden.
3. Personkilometer multipliceras med kg CO₂e/personkm och divideras med 1 000 för att ge ton CO₂e.
4. Per-hushållsresultat divideras med respektive områdes faktiska hushållsantal. Per-invånarresultat divideras med folkmängden.
5. Årsutsläppen summeras över den valda perioden, med oförändrade nivåer eller användarens utvecklingsscenario.

Bilens RVU-personkilometer och Vägvis absoluta fordonskilometer läggs inte ihop. Beläggningen används en gång för att omvandla bilens faktor från fordonskilometer till personkilometer.

## Komplettera observerade resevolymer

Hämta mallen i appen och fyll i de rader du har underlag för:

```text
deso;mode;pkm_year;year;source
1280C1010;bus;100000;2024;Beskriv källan och avgränsningen
```

Exemplet visar formatet; värdet 100000 är inte en observation.

Använd färdmedelskoderna `walk`, `cycle`, `car`, `bus`, `rail`, `air`, `other`. Volymen ska vara personkilometer per **år för hela DeSO-området**, inte fordonskilometer eller kilometer per person. År ska vara 2024. Noll är tillåtet som ett uttryckligt värde. Tomma mallrader ignoreras. Dubbla nycklar och saknad källa ger fel.

DeSO-resultat kan exporteras som CSV och kartlager som GeoJSON. En beräknings-JSON innehåller fullständiga inställningar och källor. Dessa är jämförelseunderlag för GIS, Vägvis och Road2Zero; en automatisk importadapter till de andra modellernas projektformat ingår inte.

## Kör Pythonberäkningen utan Streamlit

Beräkningsmotorn använder bara Pythons standardbibliotek. Kör i mappen med de tre programfilerna:

```bash
python streamlit_app.py --resultat resultat.json --csv resultat.csv
```

Med ett sparat projekt:

```bash
python streamlit_app.py --projekt Lagesvis_projekt.json --resultat resultat.json --simulera
```

Skapa en ny fristående HTML-karta:

```bash
python streamlit_app.py --projekt Lagesvis_projekt.json --html Min_karta.html
```

För att köra Streamlit lokalt behöver du först installera paketet:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Kontroll av leveransen

20 automatiserade modelltester har godkänts. De omfattar registersummeringar, alla sju färdmedel, årsomräkning, person-/fordonskilometer, kg–ton, faktorer, hushållsprofiler, kommunbevarande geografisk fördelning, tidsgränser, framtidsscenario, kompletteringar, noll och saknat, samt reproducerbar simulering. Python och JavaScript har jämförts i 23 718 numeriska resultat, inklusive scenarier och Monte Carlo.

Gränssnittets sex sidfunktioner, anrop till kartbiblioteket, parameterändring, simulering, filimport och export har kontrollerats med en simulerad DOM och Leaflet-API. Detta ersätter inte en grafisk webbläsarkontroll. En sådan kontroll kunde inte genomföras på grund av körmiljöns begränsning av webbläsarprocesser. Streamlit kunde inte installeras i leveransmiljön, så publiceringen har inte testats från början till slut där. Den separata kartbilden har däremot granskats visuellt.

## Källor och referenser

Fullständig Harvard-referenslista, källornas lokalisering, faktorer och antaganden finns i appens **Metod & källor** och i beräkningsexporten. De centrala referenserna är:

Region Skåne (2024). *Så reser vi i Malmö stad. Resvaneundersökning 2023*. Tabell 2, s. 29, samt metod och ålderspopulation. https://utveckling.skane.se/siteassets/publikationer/kommunrapporter-2023-rvu/sa-reser-vi-i-malmo-stad-rvu-2023.pdf (Hämtad 11 november 2026).

Statistiska centralbyrån (2025). *Befolkningen ökade 2024 trots minskade födslar*. https://www.scb.se/pressmeddelande/befolkningen-okade-2024---trots-minskade-fodslar/ (Hämtad 11 november 2026).

Statistiska centralbyrån och Trafikanalys (2026). *TAB6589 personbilar registrerade på folkbokförda personer*. År 2024, DeSO 2025. Inläst ur användarlevererat Vägvis-paket.

Statistiska centralbyrån (2026). *TAB6568 hushåll, TAB6574 folkmängd och TAB6684 ekonomisk standard*. År 2024, DeSO 2025. Inlästa ur användarlevererat Vägvis-paket.

Vägvis (2026). *Vägvis 2.3.1 GTFS GitHub*. Användarlevererat modellpaket. Kod och data har använts för att räkna fram bilens referensfaktor och den valbara körsträckefördelningen. Originalfilens kontrollsumma ingår i datafilen.

Skånetrafiken (2025). *Hållbarhetsprogram 2026–2030, version 5*, s. 9. Beslutat 27 november 2025. https://www.skanetrafiken.se/globalassets/dokumentbank/miljo/hallbarhetsprogram-2026-2030_210x297mm_6-mars-1.pdf (Hämtad 11 november 2026).

Skånetrafiken (u.å.). *Miljörapport företag 2025*. https://www.skanetrafiken.se/foretag/miljorapport-foretag/ (Hämtad 11 november 2026).

ADEME Impact CO₂ (u.å.a–d). *Marche; Vélo mécanique; Vélo à assistance électrique; Avion trajet moyen*. https://impactco2.fr/outils/transport/marche ; https://impactco2.fr/outils/transport/velo ; https://impactco2.fr/outils/transport/veloelectrique ; https://impactco2.fr/outils/transport/avion-moyencourrier (Hämtade 11 november 2026).

Samtrafiken och Skånetrafiken (2024). *GTFS regional tidtabell för Skåne*. Veckan 14–20 oktober 2024, bearbetad i Vägvis-paketet.

OpenStreetMap contributors (2026). *Geografiska serviceproxyer och landpolygoner*. https://www.openstreetmap.org/copyright och https://osmdata.openstreetmap.de/data/land-polygons.html. Medföljande underlag, © OpenStreetMap contributors, ODbL.

## Licenser

Ny Python- och JavaScriptkod: MIT. SCB:s geodata har källangivelse i metadata. OpenStreetMap-landmask och härledda geografiska underlag: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Leaflet: BSD-2-Clause. Vägvis kod som används för referensberäkning: MIT. Medföljande licenstexter finns i datafilen och i appens metodvy. Paketet innehåller inga API-nycklar.
