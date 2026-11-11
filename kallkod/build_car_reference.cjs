/* Reproduce the frozen car factor and GTFS distance from supplied Vägvis code. */
'use strict';
const fs=require('fs'),path=require('path'),ROOT=__dirname;
const V=require('./core.js'),H=require('./households.js');
const read=name=>JSON.parse(fs.readFileSync(path.join(ROOT,name),'utf8'));
const hp=read('household_project.json'),om=read('all_areas_packed.json'),dist=read('distance_indicators.json');
const project=V.unpackProject(hp,om);project.distanceData=dist;
const local=H.deterministic(project,{...hp.config,household:{kmMode:'local'}});
const gtfs=H.deterministic(project,{...hp.config,household:{kmMode:'deso_gtfs'}});
const out={factors_g_vkm:local.factors,distance_configuration:gtfs.c.household.distanceModel,km_by_deso:Object.fromEntries(gtfs.prep.rows.filter(r=>r.kk==='1280').map(r=>[r.kod,r.resolvedKm]))};
fs.writeFileSync(path.join(ROOT,'car_factors.json'),JSON.stringify(out,null,2));
console.log('Car factor g CO2e/vehicle-km:',out.factors_g_vkm.total);
