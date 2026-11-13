"""Lägesvis Malmö 1.0 — independent Python model and Streamlit entry point.

Python 3.11+; the calculation engine and HTML export use only the standard
library. Streamlit is imported only by main(). No network or keys are needed
for calculations. See the bundled source/assumption register and manual.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import mean

VERSION = "1.1.0"
MODE_IDS = ("walk", "cycle", "car", "bus", "rail", "air", "other")
DATA_NAME = "lagesvis_data.json"


def fail(message):
    raise ValueError(message)


def finite(value, label, low=0, high=1e15):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        fail(f"{label}: ange ett ändligt tal mellan {low} och {high}.")
    return value


def defaults(data):
    return copy.deepcopy(data["defaults"])


def validate_config(data, raw=None):
    c = defaults(data)
    if raw is not None:
        if not isinstance(raw, dict):
            fail("Inställningarna ska vara ett objekt.")
        if set(raw) - set(c):
            fail("Okända inställningar: " + ", ".join(sorted(set(raw)-set(c))))
        for key, value in raw.items():
            if isinstance(c[key], dict):
                if not isinstance(value, dict) or set(value) - set(c[key]):
                    fail("Okända delinställningar för " + key)
                c[key].update(value)
            else:
                c[key] = value
    checks = [("start_year", 2024, 2100), ("years", 1, 100), ("target_year", 2025, 2200),
              ("days_per_year", 1, 366), ("season_factor", 0, 5), ("excluded_age_addition", 0, 3),
              ("occupancy", 1, 8), ("car_g_vkm", 0, 3000), ("cycle_g_pkm", 0, 1000),
              ("ebike_g_pkm", 0, 1000), ("ebike_share", 0, 1), ("bus_g_pkm", 0, 3000),
              ("rail_g_pkm", 0, 3000), ("air_g_pkm", 0, 3000), ("air_nonco2_fraction", 0, 1),
              ("other_g_pkm", 0, 3000), ("air_income_beta", -2, 2), ("transit_beta", -2, 2),
              ("service_beta", -2, 2), ("draws", 0, 3000), ("seed", 0, 4294967295),
              ("demand_cv", 0, 2), ("local_cv", 0, 2)]
    for key, lo, hi in checks:
        finite(c[key], key, lo, hi)
    for key in ["start_year", "years", "target_year", "draws", "seed"]:
        if int(c[key]) != c[key]:
            fail(key + " ska vara ett heltal.")
    if c["target_year"] <= data["base_year"]:
        fail("Målåret ska vara senare än basåret.")
    if c["allocation"] not in ("register", "accessibility"):
        fail("Okänd geografisk fördelningsmetod.")
    if c["other_method"] not in ("land_average", "custom"):
        fail("Okänd faktor för övriga färdmedel.")
    for key in ["future_enabled", "include_air_nonco2", "include_air"]:
        if not isinstance(c[key], bool):
            fail(key + " ska vara true eller false.")
    for name in ["activity_target", "factor_target", "factor_cv", "activity_scale"]:
        if set(c[name]) != set(MODE_IDS):
            fail(name + " måste innehålla samtliga färdmedel.")
        for mode, value in c[name].items():
            finite(value, name + ":" + mode, 0, 5 if name != "activity_scale" else 10)
    if set(c["index_weights"]) != {"supply", "service", "node", "centre"}:
        fail("Indexvikterna har fel komponenter.")
    for key, value in c["index_weights"].items():
        finite(value, "index_weights:" + key, 0, 100)
    if sum(c["index_weights"].values()) <= 0:
        fail("Minst en indexvikt måste vara större än noll.")
    return validate_mobility_config(data, c)


def validate_data(data):
    if data.get("version") != VERSION:
        fail("Program och datafil ska båda vara version " + VERSION + ". Ersätt streamlit_app.py och lagesvis_data.json tillsammans.")
    if data.get("schema") != "lagesvis-data-1":
        fail("Datafilens schema stöds inte.")
    if data.get("base_year") != 2024 or data.get("deso_version") != "2025":
        fail("Detta modellpaket gäller basår 2024 och DeSO 2025.")
    ids = set()
    for p in data["profiles"]:
        if p["id"] in ids or not p["id"].startswith("1280"):
            fail("Dubbel eller främmande DeSO-kod.")
        ids.add(p["id"])
        for key in ["households", "population", "cars", "eligible_population", "km_anchor", "km_gtfs", "land_m2"]:
            finite(p[key], p["id"] + ":" + key)
        if p["eligible_population"] > p["population"] or not p["land_m2"]:
            fail("Ålderspopulation eller landyta är ogiltig.")
        for key in ["transit_weekday", "transit_weekend", "transit_morning", "transit_evening", "transit_served_share"]:
            if p.get(key) is not None:
                finite(p[key],p["id"]+":"+key,0,1 if key=="transit_served_share" else 100000)
        for key in ["income", "centre_km", "service_km", "node_km", "transit_supply"]:
            if p[key] is not None:
                finite(p[key], p["id"] + ":" + key)
    if len(ids) != 209:
        fail("Förväntade exakt 209 Malmö-DeSO.")
    if not all(sum(p[key] for p in data["profiles"]) > 0 for key in ["population", "households", "eligible_population"]):
        fail("Kommunen ska ha en positiv folkmängd, hushållsvolym och ålderspopulation.")
    if set(data["rvu"]["daily_pkm"]) != set(MODE_IDS):
        fail("RVU-underlaget saknar färdmedel.")
    for mode in MODE_IDS:
        finite(data["rvu"]["daily_pkm"][mode], "RVU " + mode)
    if not data["rvu"]["survey_population"]:
        fail("RVU:s undersökningspopulation saknas.")
    return data


def validate_overrides(data, overrides=None):
    out, seen = [], set()
    codes = {p["id"] for p in data["profiles"]}
    for row in overrides or []:
        if not isinstance(row, dict):
            fail("Varje kompletteringsrad måste vara ett objekt.")
        required = {"deso", "mode", "pkm_year", "year", "source"}
        if set(row) != required:
            fail("En komplettering ska ha deso, mode, pkm_year, year och source.")
        if row["deso"] not in codes or row["mode"] not in MODE_IDS:
            fail("Komplettering: okänd DeSO eller färdmedelskod.")
        key = (row["deso"], row["mode"])
        if key in seen:
            fail("Dubbelt värde för " + "/".join(key))
        seen.add(key)
        if row["year"] != data["base_year"]:
            fail("Kompletteringar ska avse basår 2024; år blandas inte automatiskt.")
        finite(row["pkm_year"], "Personkilometer per år")
        if not isinstance(row["source"], str) or not row["source"].strip():
            fail("Kompletteringens källa saknas.")
        out.append(dict(row))
    return out


def normalise(weights, total):
    if any(not math.isfinite(x) or x < 0 for x in weights):
        fail("Ogiltig geografisk vikt.")
    sum_w = sum(weights)
    if sum_w == 0:
        if total:
            fail("Positivt resande saknar geografiska fördelningsvikter.")
        return [0.0] * len(weights)
    return [total * w / sum_w for w in weights]


def percentile(value, references):
    refs = [x for x in references if x is not None]
    if value is None or not refs:
        return None
    if len(refs) == 1:
        return 50.0
    less = sum(x < value for x in refs)
    equal = sum(x == value for x in refs)
    return 100 * (less + (equal - 1) / 2) / (len(refs) - 1)


def availability(data, c, profile, centre_km=None):
    raw = dict(supply=profile["transit_supply"], service=profile["service_km"],
               node=profile["node_km"], centre=profile["centre_km"] if centre_km is None else centre_km)
    keymap = dict(supply="transit_supply", service="service_km", node="node_km", centre="centre_km")
    parts = {}
    for key, value in raw.items():
        sign = 1 if key == "supply" else -1
        references = [sign*p[keymap[key]] if p[keymap[key]] is not None else None for p in data["profiles"]]
        # A new grid point may lie outside the DeSO-centre reference range.
        score = percentile(sign*value if value is not None else None, references)
        parts[key] = max(0, min(100, score)) if score is not None else None
    use = [(score, c["index_weights"][key]) for key, score in parts.items() if score is not None and c["index_weights"][key] > 0]
    score = sum(s*w for s,w in use) / sum(w for _,w in use) if use else None
    return dict(score=score, parts=parts, available=len(use), total=sum(v > 0 for v in c["index_weights"].values()))


def factors(data, c):
    ef = dict(walk=0.0,
              cycle=((1-c["ebike_share"])*c["cycle_g_pkm"] + c["ebike_share"]*c["ebike_g_pkm"])/1000,
              car=c["car_g_vkm"]/c["occupancy"]/1000,
              bus=c["bus_g_pkm"]/1000, rail=c["rail_g_pkm"]/1000,
              air=c["air_g_pkm"]/1000 * (1 if c["include_air_nonco2"] else 1-c["air_nonco2_fraction"]))
    land = ("walk", "cycle", "car", "bus", "rail")
    ef["other"] = (sum(data["rvu"]["daily_pkm"][m]*ef[m] for m in land) /
                   sum(data["rvu"]["daily_pkm"][m] for m in land)) if c["other_method"] == "land_average" else c["other_g_pkm"]/1000
    return ef


def baseline_activity(data, c, overrides):
    ps = data["profiles"]
    eligible = sum(p["eligible_population"] for p in ps)
    scale = c["days_per_year"]*c["season_factor"]*eligible/data["rvu"]["survey_population"]*(1+c["excluded_age_addition"])
    weighted_income = sum(p["eligible_population"]*(p["income"] or 0) for p in ps)/eligible
    out = {}
    for mode in MODE_IDS:
        w = []
        for p in ps:
            pop = p["eligible_population"]
            if mode == "car":
                weight = p["cars"]*(p["km_gtfs"] if c["allocation"] == "accessibility" else p["km_anchor"])
            elif c["allocation"] == "accessibility" and mode in ("bus", "rail"):
                weight = pop * (1+(p["transit_supply"] or 0))**c["transit_beta"]
            elif c["allocation"] == "accessibility" and mode in ("walk", "cycle"):
                weight = pop * (1+(p["service_km"] or 0))**(-c["service_beta"])
            elif mode == "air" and c["air_income_beta"] and p["income"] and weighted_income:
                weight = pop*(p["income"]/weighted_income)**c["air_income_beta"]
            else:
                weight = pop
            w.append(weight)
        total = data["rvu"]["daily_pkm"][mode]*scale*c["activity_scale"][mode]
        out[mode] = normalise(w, total)
    idx = {p["id"]: i for i,p in enumerate(ps)}
    for row in overrides:
        out[row["mode"]][idx[row["deso"]]] = row["pkm_year"]
    # Scope is applied after imports so excluded flights cannot reappear.
    # Overrides remain stored, allowing the same project to be toggled back.
    if not c["include_air"]:
        out["air"] = [0.0] * len(ps)
    return out


def year_multiplier(data, c, mode, year):
    if not c["future_enabled"]:
        return 1.0
    fraction = min(1, max(0, (year-data["base_year"])/(c["target_year"]-data["base_year"])))
    activity = 1 + (c["activity_target"][mode]-1)*fraction
    factor = 1 + (c["factor_target"][mode]-1)*fraction
    return activity*factor


def horizon_weights(data, c):
    return {mode: sum(year_multiplier(data,c,mode,year) for year in range(c["start_year"],c["start_year"]+c["years"])) for mode in MODE_IDS}


"""Transparent extensions. No inferred route times or causal elasticities."""
ROUTE_FIELDS = {"deso", "destination", "purpose", "walk_min", "cycle_min", "transit_min", "car_min", "jobs", "year", "period", "kind", "source"}


def household_car_reference(work_age, smallhouse, rental, single):
    values = (work_age, smallhouse, rental, single)
    if all(x is None for x in values):
        return None
    if any(x is None for x in values):
        fail("Planprofilen behöver samtliga fyra andelar; saknade värden ersätts inte.")
    for label, value in zip(("20–64 år", "Småhus", "Hyresrätter", "Singelhushåll"), values):
        finite(value, label + " som andel 0–1", 0, 1)
    value = 1.148 - .310*work_age + .434*smallhouse - .239*rental - .901*single
    return dict(cars_per_household=value if value >= 0 else None,
                raw_prediction=value, negative_prediction=value < 0,
                status="Överförd regression från 109 Malmö-delområden, inte validerad på DeSO eller nya bostadsprojekt",
                source="Kerttu (2025), bilaga 3, PDF-sida 5")


def validate_mobility_config(data, c):
    if not isinstance(c["mobility_enabled"], bool):
        fail("mobility_enabled ska vara true eller false.")
    ids = {p["id"] for p in data["profiles"]}
    if c["mobility_target"] != "all" and c["mobility_target"] not in ids:
        fail("Välj hela Malmö eller en befintlig DeSO för mobilitetsscenariot.")
    for k in ["mobility_car_reduction", "mobility_walk_share", "mobility_cycle_share", "mobility_bus_share", "mobility_rail_share"]:
        finite(c[k], k, 0, 1)
    if abs(sum(c["mobility_"+m+"_share"] for m in ("walk", "cycle", "bus", "rail"))-1) > 1e-9:
        fail("Fördelningen av överflyttade personkilometer ska summera till 100 procent.")
    for k in ["mobility_source", "planning_source"]:
        if not isinstance(c[k], str) or len(c[k]) > 4000:
            fail(k + " ska vara en text på högst 4 000 tecken.")
    if c["mobility_enabled"] and c["mobility_car_reduction"] and not c["mobility_source"].strip():
        fail("Dokumentera källa eller eget antagande för mobilitetsscenariot.")
    estimate = household_car_reference(*(c["planning_"+k] for k in ("work_age", "smallhouse", "rental", "single")))
    if estimate and not c["planning_source"].strip():
        fail("Ange källa eller eget antagande för planprofilens andelar.")
    return c


def validate_routes(data, rows=None):
    if rows is None:
        return []
    if not isinstance(rows, list) or len(rows) > 100000:
        fail("Restidsunderlaget ska vara en lista med högst 100 000 rader.")
    ids = {p["id"] for p in data["profiles"]}
    seen, contexts, out, definitions = set(), set(), [], {}
    for r in rows:
        if not isinstance(r, dict) or set(r) != ROUTE_FIELDS:
            fail("Restidsraden har fel kolumner. Använd den medföljande CSV-mallen.")
        if r["deso"] not in ids:
            fail("Restidsrad: okänd DeSO 2025 i Malmö.")
        for key in ["destination", "period", "source"]:
            if not isinstance(r[key], str) or not r[key].strip() or len(r[key]) > 1000:
                fail("Restidsrad: " + key + " saknas eller är för lång.")
        if r["purpose"] not in ("service", "node", "job_cell", "other") or r["kind"] not in ("observed", "modelled", "scenario"):
            fail("Restidsrad: okänd målpunktstyp eller datastatus.")
        finite(r["year"], "Restidsår", 2000, 2100)
        if int(r["year"]) != r["year"]:
            fail("Restidsår ska vara ett heltal.")
        contexts.add((r["year"], r["period"], r["kind"]))
        if len(contexts) != 1:
            fail("Blanda inte år, tidsfönster eller datastatus i samma restidsunderlag.")
        key = (r["deso"], r["destination"])
        if key in seen:
            fail("Dubbla restider för " + "/".join(key))
        seen.add(key)
        for field in ["walk_min", "cycle_min", "transit_min", "car_min"]:
            if r[field] is not None:
                finite(r[field], field, 0, 1440)
        if all(r[field] is None for field in ["walk_min", "cycle_min", "transit_min", "car_min"]):
            fail("Restidsraden behöver minst en dokumenterad restid.")
        if r["jobs"] is not None:
            finite(r["jobs"], "Arbetsplatser", 0, 10000000)
            if r["purpose"] != "job_cell":
                fail("Arbetsplatsantal anges endast för disjunkta job_cell-målpunkter.")
        definition = (r["purpose"], r["jobs"])
        if r["destination"] in definitions and definitions[r["destination"]] != definition:
            fail("Samma målpunkt har motstridig typ eller arbetsplatsantal.")
        definitions[r["destination"]] = definition
        out.append(dict(r))
    return out


def route_summaries(data, rows):
    out = {}
    for p in data["profiles"]:
        rs = [r for r in rows if r["deso"] == p["id"]]
        ratios = {m:[r[m+"_min"]/r["car_min"] for r in rs if r[m+"_min"] is not None and r["car_min"] is not None and r["car_min"] > 0] for m in ("transit", "cycle")}
        jobs = [r for r in rs if r["purpose"] == "job_cell" and r["jobs"] is not None and r["transit_min"] is not None]
        def median(xs):
            s = sorted(xs); n = len(s)
            return (s[(n-1)//2]+s[n//2])/2 if n else None
        out[p["id"]] = dict(route_count=len(rs),
            transit_car_ratio=median(ratios["transit"]),cycle_car_ratio=median(ratios["cycle"]),
            ratio_pairs=len(ratios["transit"]),
            jobs_15_min=sum(r["jobs"] for r in jobs if r["transit_min"] <= 15) if jobs else None,
            jobs_30_min=sum(r["jobs"] for r in jobs if r["transit_min"] <= 30) if jobs else None,
            job_cells=len(jobs),
            route_year=rs[0]["year"] if rs else None,route_period=rs[0]["period"] if rs else None,
            route_kind=rs[0]["kind"] if rs else None)
    return out


def apply_mobility(data, c, original):
    activity = {m:list(values) for m,values in original.items()}
    removed = 0.0
    if c["mobility_enabled"]:
        for i,p in enumerate(data["profiles"]):
            if c["mobility_target"] not in ("all", p["id"]):
                continue
            shift = original["car"][i]*c["mobility_car_reduction"]
            activity["car"][i] -= shift
            removed += shift
            for mode in ("walk", "cycle", "bus", "rail"):
                activity[mode][i] += shift*c["mobility_"+mode+"_share"]
    balance = sum(sum(activity[m])-sum(original[m]) for m in MODE_IDS)
    if abs(balance) > max(1e-5, removed*1e-10):
        raise ArithmeticError("Mobilitetsscenariots personkilometer stämmer inte.")
    return activity, dict(enabled=c["mobility_enabled"],target=c["mobility_target"],
        removed_car_pkm=removed,pkm_balance_error=balance,source=c["mobility_source"],
        status="Användarvalt scenario med bevarade personkilometer, inte skattad effekt av parkering eller tillgänglighet")


def calculate(data, raw_config=None, raw_overrides=None, raw_routes=None):
    c = validate_config(data, raw_config)
    overrides = validate_overrides(data, raw_overrides)
    ef = factors(data,c)
    original_activity = baseline_activity(data,c,overrides)
    activity, mobility = apply_mobility(data,c,original_activity)
    routes = validate_routes(data, raw_routes)
    route_by = route_summaries(data, routes)
    horizon = horizon_weights(data,c)
    result = []
    for i,p in enumerate(data["profiles"]):
        mode_tons = {m: activity[m][i]*ef[m]/1000 for m in MODE_IDS}
        base_ton = sum(mode_tons.values())
        year_tons = {m: mode_tons[m]*year_multiplier(data,c,m,c["start_year"]) for m in MODE_IDS}
        annual = sum(year_tons.values())
        period = sum(mode_tons[m]*horizon[m] for m in MODE_IDS)
        accessible = availability(data,c,p)
        result.append(dict(id=p["id"],name=p["name"],households=p["households"],population=p["population"],
                           cars=p["cars"],household_size=p["population"]/p["households"] if p["households"] else None,
                           cars_per_household=p["cars"]/p["households"] if p["households"] else None,
                           base_ton=base_ton,annual_ton=annual,period_ton=period,
                           annual_ton_hh=annual/p["households"] if p["households"] else None,
                           annual_ton_person=annual/p["population"] if p["population"] else None,
                           period_ton_hh=period/p["households"] if p["households"] else None,
                           mode_pkm={m:activity[m][i] for m in MODE_IDS},mode_tons=year_tons,
                           availability=accessible["score"],index_coverage=accessible["available"]/accessible["total"] if accessible["total"] else None,
                           income=p["income"],centre_km=p["centre_km"],service_km=p["service_km"],node_km=p["node_km"],transit_supply=p["transit_supply"],
                           land_ha=p["land_m2"]/10000,km_anchor=p["km_anchor"],km_gtfs=p["km_gtfs"]))
    for i, row in enumerate(result):
        p = data["profiles"][i]
        row["population_density_ha"] = p["population"]/(p["land_m2"]/10000)
        row["household_density_ha"] = p["households"]/(p["land_m2"]/10000)
        for key in ["transit_weekday", "transit_weekend", "transit_morning", "transit_evening", "transit_served_share"]:
            row[key] = p.get(key)
        row["allocated_car_km_per_registered_car"] = activity["car"][i]/c["occupancy"]/p["cars"] if p["cars"] else None
        row["reference_annual_ton"] = sum(original_activity[m][i]*ef[m]*year_multiplier(data,c,m,c["start_year"])/1000 for m in MODE_IDS)
        row["scenario_delta_ton"] = row["annual_ton"]-row["reference_annual_ton"]
        row.update(route_by[p["id"]])
    city = dict(annual_ton=sum(r["annual_ton"] for r in result),period_ton=sum(r["period_ton"] for r in result),
                base_ton=sum(r["base_ton"] for r in result),households=sum(p["households"] for p in data["profiles"]),
                population=sum(p["population"] for p in data["profiles"]),cars=sum(p["cars"] for p in data["profiles"]))
    city["reference_annual_ton"] = sum(r["reference_annual_ton"] for r in result)
    city["scenario_delta_ton"] = city["annual_ton"]-city["reference_annual_ton"]
    city["population_density_ha"] = city["population"]/(sum(p["land_m2"] for p in data["profiles"])/10000)
    city["route_areas"] = sum(r["route_count"]>0 for r in result)
    city["annual_ton_hh"] = city["annual_ton"]/city["households"]
    city["annual_ton_person"] = city["annual_ton"]/city["population"]
    city["period_ton_hh"] = city["period_ton"]/city["households"]
    index_households = sum(r["households"] for r in result if r["availability"] is not None)
    city["availability"] = sum(r["availability"]*r["households"] for r in result if r["availability"] is not None)/index_households if index_households else None
    city["mode_tons"] = {m: sum(r["mode_tons"][m] for r in result) for m in MODE_IDS}
    city["mode_pkm"] = {m: sum(r["mode_pkm"][m] for r in result) for m in MODE_IDS}
    series = [dict(year=year,ton=sum(sum(r["mode_pkm"][m] for r in result)*ef[m]*year_multiplier(data,c,m,year)/1000 for m in MODE_IDS))
              for year in range(c["start_year"],c["start_year"]+c["years"])]
    if not math.isclose(sum(x["ton"] for x in series),city["period_ton"],rel_tol=1e-10,abs_tol=1e-5):
        raise ArithmeticError("Årsserien stämmer inte med periodens summa.")
    return dict(version=VERSION,config=c,overrides=overrides,route_data=routes,mobility=mobility,planning_reference=household_car_reference(*(c["planning_"+k] for k in ("work_age", "smallhouse", "rental", "single"))),factors_kg_pkm=ef,areas=result,city=city,series=series,
                scope="RVU-baserad screening för ålder 15–84 år med eventuellt antaget ålderstillägg; " + ("flyg inkluderat" if c["include_air"] else "flyg exkluderat") + ("; användarvalt mobilitetsscenario" if c["mobility_enabled"] else "") + ". Blandade systemgränser; inte fullständig cradle-to-cradle-LCA.",
                units=dict(annual_ton="ton CO2e/år",period_ton="ton CO2e under vald period",annual_ton_hh="ton CO2e/(hushåll·år)",annual_ton_person="ton CO2e/(invånare·år)",period_ton_hh="ton CO2e/hushåll under vald period",mode_pkm="personkm/basår 2024",factors_kg_pkm="kg CO2e/personkm"),
                source_sha256=data["source_hashes"],input_year=2024,geography="DeSO 2025 / 250 m visningsrutor EPSG:3006")


class Random:
    """Mulberry32 + uncached Box–Muller; same operation order as model.js."""
    def __init__(self, seed):
        self.state = seed & 0xffffffff

    def uniform(self):
        self.state = (self.state + 0x6d2b79f5) & 0xffffffff
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xffffffff
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xffffffff)) & 0xffffffff
        return ((t ^ (t >> 14)) & 0xffffffff)/4294967296

    def lognormal(self, cv):
        if not cv:
            return 1.0
        sigma = math.sqrt(math.log1p(cv*cv))
        z = math.sqrt(-2*math.log(max(self.uniform(),1e-15)))*math.cos(2*math.pi*self.uniform())
        return math.exp(sigma*z-.5*sigma*sigma)


def quantile(values, p):
    s = sorted(values)
    i = (len(s)-1)*p
    lo = math.floor(i)
    return s[lo] + (s[min(lo+1,len(s)-1)]-s[lo])*(i-lo)


def simulate(data, result):
    c = result["config"]
    n = c["draws"]
    if not n:
        return None
    rng = Random(c["seed"])
    length = len(result["areas"])
    annual_draws = [[] for _ in range(length)]
    period_draws = [[] for _ in range(length)]
    city_annual, city_period = [], []
    horizon = horizon_weights(data,c)
    year_factors = {m:year_multiplier(data,c,m,c["start_year"]) for m in MODE_IDS}
    for _ in range(n):
        annual = [0.0]*length
        period = [0.0]*length
        for mode in MODE_IDS:
            common = rng.lognormal(c["demand_cv"])*rng.lognormal(c["factor_cv"][mode])
            base = [r["mode_pkm"][mode] for r in result["areas"]]
            total = sum(base)
            perturbed = normalise([value*rng.lognormal(c["local_cv"]) for value in base],total)
            for i,value in enumerate(perturbed):
                tons = value*result["factors_kg_pkm"][mode]*common/1000
                annual[i] += tons*year_factors[mode]
                period[i] += tons*horizon[mode]
        for i in range(length):
            annual_draws[i].append(annual[i]); period_draws[i].append(period[i])
        city_annual.append(sum(annual)); city_period.append(sum(period))
    stats = lambda xs: dict(p025=quantile(xs,.025),p975=quantile(xs,.975),mean=mean(xs))
    return dict(label="Antagandebaserat scenariointervall, inte statistiskt konfidensintervall",draws=n,seed=c["seed"],
                city_annual=stats(city_annual),city_period=stats(city_period),
                areas={r["id"]:dict(annual=stats(annual_draws[i]),period=stats(period_draws[i])) for i,r in enumerate(result["areas"])},
                correlation="Gemensam aktivitets- och faktorvariation per färdmedel för hela staden; lokal variation omnormaliseras per färdmedel; samma osäkra relativa nivå över alla framtida år.")


def csv_bytes(rows):
    if not rows:
        return b""
    out = io.StringIO()
    fields = list(rows[0])
    writer = csv.DictWriter(out,fieldnames=fields,delimiter=";")
    writer.writeheader()
    for row in rows:
        cleaned = {}
        for key,value in row.items():
            if value is None:
                value = ""
            elif isinstance(value,(dict,list)):
                value = json.dumps(value,ensure_ascii=False)
            elif isinstance(value,str) and value[:1] in ("=","+","-","@"):
                value = "'"+value
            cleaned[key] = value
        writer.writerow(cleaned)
    return ("\ufeff"+out.getvalue()).encode("utf-8")


def result_csv(result):
    rows = []
    for r in result["areas"]:
        row = {key:value for key,value in r.items() if key not in ("mode_pkm","mode_tons")}
        row.update({"pkm_base2024_"+m:r["mode_pkm"][m] for m in MODE_IDS})
        row.update({"ton_"+m:r["mode_tons"][m] for m in MODE_IDS})
        row.update(analysis_year=result["config"]["start_year"],period_years=result["config"]["years"],
                   scope=result["scope"],units=result["units"],factors_kg_pkm=result["factors_kg_pkm"],
                   model_config=result["config"],source_sha256=result["source_sha256"])
        rows.append(row)
    return csv_bytes(rows)


def safe_json(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":"),allow_nan=False).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")


def html_app(data, result):
    a = data["assets"]
    payload = {k:v for k,v in data.items() if k != "assets"}
    template = a["shell"]
    replacements = {"__APP_CSS__":a["css"],"__LEAFLET_CSS__":a["leaflet_css"],"__LEAFLET_JS__":a["leaflet_js"],
                    "__APP_DATA__":safe_json(payload),"__PY_BASELINE__":safe_json(result),
                    "__MODEL_JS__":a["model_js"],"__UI_JS__":a["ui_js"],"__METHOD_HTML__":a["method_html"]}
    for marker,value in replacements.items():
        if marker not in template:
            fail("Gränssnittets mall saknar " + marker)
        template = template.replace(marker,value)
    return template


def load_data(path=None):
    path = Path(path) if path else Path(__file__).with_name(DATA_NAME)
    return validate_data(json.loads(path.read_text(encoding="utf-8")))


def main():
    import streamlit as st
    import streamlit.components.v1 as components
    st.set_page_config(page_title="Lägesvis Malmö",page_icon="◈",layout="wide",initial_sidebar_state="collapsed")
    st.markdown('''<style>[data-testid="stHeader"],footer{display:none}.block-container{padding:0!important;max-width:none!important}[data-testid="stMainBlockContainer"]{padding:0!important}iframe{height:100vh!important;min-height:0!important;width:100%!important;border:0!important}.stApp{background:#f5f5ef}[data-testid="stMain"]{overflow:hidden}</style>''',unsafe_allow_html=True)
    try:
        data = load_data()
        baseline = calculate(data)
    except (OSError,ValueError,KeyError) as exc:
        st.error("Appens underlag kunde inte läsas: " + str(exc))
        st.stop()
    components.html(html_app(data,baseline),height=1000,scrolling=False)


def cli():
    parser = argparse.ArgumentParser(description="Lägesvis Malmö: Pythonberäkning och fristående karta")
    parser.add_argument("--html",help="Spara en interaktiv HTML-karta")
    parser.add_argument("--resultat",help="Spara beräkningsresultat som JSON")
    parser.add_argument("--csv",help="Spara DeSO-resultat som CSV")
    parser.add_argument("--projekt",help="Öppna inställningar och kompletteringar från appens projekt-JSON")
    parser.add_argument("--simulera",action="store_true",help="Inkludera antagandebaserat scenariointervall")
    args = parser.parse_args()
    data = load_data()
    config = overrides = routes = None
    if args.projekt:
        project = json.loads(Path(args.projekt).read_text(encoding="utf-8-sig"))
        if project.get("schema") != "lagesvis-project-1":
            fail("Projektfilens schema stöds inte.")
        if project.get("base_year") != data["base_year"]:
            fail("Projektfilens basår stöds inte.")
        config,overrides,routes = project["config"],project.get("overrides",[]),project.get("route_data",[])
    result = calculate(data,config,overrides,routes)
    if args.simulera:
        result["uncertainty"] = simulate(data,result)
    if args.html:
        Path(args.html).write_text(html_app(data,result),encoding="utf-8")
    if args.resultat:
        Path(args.resultat).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    if args.csv:
        Path(args.csv).write_bytes(result_csv(result))
    print(json.dumps({"version":VERSION,"city":result["city"],"files":[v for v in [args.html,args.resultat,args.csv] if v]},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    import sys
    if any(arg.startswith("--") for arg in sys.argv[1:]):
        cli()
    else:
        main()
