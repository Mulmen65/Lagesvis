import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parent
PACKAGE=(ROOT.parent if (ROOT.parent/'lagesvis_data.json').exists() else ROOT.parent/'leverans/lagesvis_malmo')
spec=importlib.util.spec_from_file_location('lagesvis',PACKAGE/'streamlit_app.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class LagesvisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=m.load_data(PACKAGE/'lagesvis_data.json')
        cls.result=m.calculate(cls.data)

    def test_register_totals_and_actual_household_profiles(self):
        c=self.result['city']
        self.assertEqual((c['households'],c['population'],c['cars']),(172941,365644,100524))
        self.assertEqual(len(self.result['areas']),209)
        sizes={round(r['household_size'],4) for r in self.result['areas']}
        self.assertGreater(len(sizes),190)

    def test_all_seven_modes_present_and_other_not_dropped(self):
        self.assertEqual(set(self.result['city']['mode_pkm']),set(m.MODE_IDS))
        self.assertTrue(all(self.result['city']['mode_pkm'][mode]>0 for mode in m.MODE_IDS))
        self.assertEqual(self.result['city']['mode_tons']['walk'],0)
        self.assertGreater(self.result['city']['mode_tons']['other'],0)

    def test_rvu_totals_are_annualised_once_with_population_transfer(self):
        self.assertEqual(sum(self.data['rvu']['daily_pkm'].values()),10758200)
        expected=10758200*365*365644/362133
        self.assertAlmostEqual(sum(self.result['city']['mode_pkm'].values()),expected,places=4)

    def test_car_passengers_and_vehicle_km_not_double_counted(self):
        self.assertAlmostEqual(self.result['factors_kg_pkm']['car'],227.76447229300268/1.3/1000)
        other=m.calculate(self.data,{'occupancy':2.6})
        self.assertAlmostEqual(other['city']['mode_pkm']['car'],self.result['city']['mode_pkm']['car'])
        self.assertAlmostEqual(other['city']['mode_tons']['car']*2,self.result['city']['mode_tons']['car'])

    def test_kg_ton_and_household_weighted_city_mean(self):
        a=self.result['areas'][0]
        expected=sum(a['mode_pkm'][k]*self.result['factors_kg_pkm'][k] for k in m.MODE_IDS)/1000
        self.assertAlmostEqual(a['annual_ton'],expected)
        city_weighted=sum(a['annual_ton_hh']*a['households'] for a in self.result['areas'])/172941
        self.assertAlmostEqual(city_weighted,self.result['city']['annual_ton_hh'])

    def test_spatial_allocation_preserves_city_totals(self):
        allocated=m.calculate(self.data,{'allocation':'accessibility'})
        for key in m.MODE_IDS:
            self.assertAlmostEqual(self.result['city']['mode_pkm'][key],allocated['city']['mode_pkm'][key],places=4)
        self.assertAlmostEqual(self.result['city']['annual_ton'],allocated['city']['annual_ton'],places=6)
        self.assertGreater(max(abs(a['annual_ton_hh']-b['annual_ton_hh']) for a,b in zip(self.result['areas'],allocated['areas'])),.1)

    def test_gtfs_distance_anchor_remains_car_weighted(self):
        ps=self.data['profiles']
        value=sum(p['cars']*p['km_gtfs'] for p in ps)/sum(p['cars'] for p in ps)
        self.assertAlmostEqual(value,11892,places=7)

    def test_fifty_year_reference_and_one_year_boundary(self):
        self.assertAlmostEqual(self.result['city']['period_ton'],self.result['city']['annual_ton']*50,places=5)
        one=m.calculate(self.data,{'years':1})
        self.assertAlmostEqual(one['city']['period_ton'],one['city']['annual_ton'])
        self.assertEqual(self.result['series'][-1]['year'],2073)

    def test_future_activity_and_factors_interpolated_separately(self):
        c=m.validate_config(self.data,{'future_enabled':True,'target_year':2050,'activity_target':{'car':.5},'factor_target':{'car':.5}})
        self.assertEqual(m.year_multiplier(self.data,c,'car',2024),1)
        self.assertEqual(m.year_multiplier(self.data,c,'car',2037),.5625)
        self.assertEqual(m.year_multiplier(self.data,c,'car',2050),.25)
        self.assertEqual(m.year_multiplier(self.data,c,'car',2075),.25)

    def test_flight_nonco2_removed_once_without_dropping_activity(self):
        out=m.calculate(self.data,{'include_air_nonco2':False})
        self.assertAlmostEqual(out['factors_kg_pkm']['air'],.102)
        self.assertEqual(out['city']['mode_pkm']['air'],self.result['city']['mode_pkm']['air'])
        self.assertAlmostEqual(self.result['factors_kg_pkm']['air'],.185)

    def test_ebike_mix_is_explicit_and_zero_is_not_a_missing_share(self):
        out=m.calculate(self.data,{'ebike_share':1})
        self.assertEqual(out['factors_kg_pkm']['cycle'],.011)
        self.assertEqual(self.result['factors_kg_pkm']['cycle'],.00017)

    def test_other_factor_is_derived_from_active_land_modes(self):
        land=['walk','cycle','car','bus','rail']
        expected=sum(self.data['rvu']['daily_pkm'][k]*self.result['factors_kg_pkm'][k] for k in land)/sum(self.data['rvu']['daily_pkm'][k] for k in land)
        self.assertEqual(self.result['factors_kg_pkm']['other'],expected)
        self.assertEqual(m.calculate(self.data,{'other_method':'custom','other_g_pkm':0})['city']['mode_tons']['other'],0)

    def test_imported_zero_replaces_an_area_and_changes_city_total(self):
        row=dict(deso='1280C1010',mode='air',pkm_year=0,year=2024,source='Testkälla')
        out=m.calculate(self.data,None,[row])
        old=next(a for a in self.result['areas'] if a['id']==row['deso'])
        new=next(a for a in out['areas'] if a['id']==row['deso'])
        self.assertEqual(new['mode_pkm']['air'],0)
        self.assertAlmostEqual(self.result['city']['annual_ton']-out['city']['annual_ton'],old['mode_tons']['air'])

    def test_conflicting_duplicate_unknown_year_and_source_fail(self):
        row=dict(deso='1280C1010',mode='air',pkm_year=10,year=2024,source='Testkälla')
        for rows in [[row,row],[{**row,'year':2023}],[{**row,'deso':'X'}],[{**row,'source':''}],[{**row,'mode':'unknown'}]]:
            with self.assertRaises(ValueError):m.validate_overrides(self.data,rows)

    def test_bad_settings_fail_and_no_nan_propagation(self):
        for bad in [{'occupancy':0},{'years':1.5},{'car_g_vkm':float('nan')},{'future_enabled':1},{'unknown':1},{'factor_target':{'wrong':1}},{'index_weights':dict(supply=0,service=0,node=0,centre=0)}]:
            with self.assertRaises(ValueError):m.validate_config(self.data,bad)

    def test_missing_index_components_remain_missing(self):
        data={**self.data,'profiles':[dict(p,centre_km=None,service_km=None,node_km=None,transit_supply=None) for p in self.data['profiles']]}
        out=m.calculate(data)
        self.assertIsNone(out['city']['availability'])
        self.assertTrue(all(r['availability'] is None for r in out['areas']))

    def test_scenario_interval_zero_variance_and_seed_reproducibility(self):
        c={'draws':10,'local_cv':0,'demand_cv':0,'factor_cv':{m:0 for m in m.MODE_IDS}}
        # Use explicit module reference to avoid shadowing in the comprehension.
        out=m.calculate(self.data,c);u=m.simulate(self.data,out)
        self.assertAlmostEqual(u['city_annual']['p025'],out['city']['annual_ton'],places=6)
        self.assertAlmostEqual(u['city_period']['p975'],out['city']['period_ton'],places=5)
        a=m.calculate(self.data,{'draws':10})
        self.assertEqual(m.simulate(self.data,a),m.simulate(self.data,a))

    def test_grid_is_real_metric_geometry_and_no_fabricated_households(self):
        r=self.data['grid_receipt']
        self.assertEqual(r['unique_cells'],2772)
        self.assertEqual(r['cell_fragments'],4468)
        self.assertEqual(r['cell_size_m'],250)
        self.assertLess(abs(r['closure_error_m2']),.1)
        self.assertTrue(all(c['easting']%250==0 and c['northing']%250==0 for c in self.data['cells']))
        self.assertTrue(all('households' not in c and 'population' not in c for c in self.data['cells']))
        self.assertEqual({c['deso'] for c in self.data['cells']},{p['id'] for p in self.data['profiles']})

    def test_export_escapes_spreadsheet_formulas_and_script_endings(self):
        self.assertIn("'=1",m.csv_bytes([dict(value='=1')]).decode('utf-8'))
        self.assertNotIn('</script>',m.safe_json({'a':'</script><script>alert(1)</script>'}))

    def test_python_and_javascript_match_in_scenarios_and_simulation(self):
        cases=[{},dict(allocation='accessibility',occupancy=1.8,ebike_share=.3,include_air_nonco2=False),
               dict(start_year=2030,years=25,future_enabled=True,target_year=2040,activity_target={'car':.7,'rail':1.2},factor_target={'air':.8,'car':.3})]
        payload=[]
        for cfg in cases:
            py=m.calculate(self.data,cfg);payload.append({'config':cfg,'python':py})
        c=m.calculate(self.data,{'draws':25});sim=m.simulate(self.data,c)
        path=ROOT/'parity_inputs.json';path.write_text(json.dumps({'cases':payload,'simulation':sim,'sim_config':{'draws':25}},ensure_ascii=False))
        js=r'''const fs=require('fs'),assert=require('assert'),M=require(process.argv[1]),D=JSON.parse(fs.readFileSync(process.argv[2])),P=JSON.parse(fs.readFileSync(process.argv[3]));let n=0;function compare(a,b,path=''){if(typeof a==='number'){assert.ok(Math.abs(a-b)<=Math.max(1e-7,Math.abs(a)*2e-11),path+': '+a+' vs '+b);n++;}else if(a===null||typeof a!=='object'){assert.strictEqual(a,b,path);}else{assert.deepStrictEqual(Object.keys(a).sort(),Object.keys(b).sort(),path);for(const k of Object.keys(a))compare(a[k],b[k],path+'/'+k);}}for(const c of P.cases)compare(c.python,M.calculate(D,c.config));compare(P.simulation,M.simulate(D,M.calculate(D,P.sim_config)));console.log('Python/JavaScript numeric comparisons:',n);'''
        result=subprocess.run(['node','-e',js,str(ROOT/'model.js'),str(PACKAGE/'lagesvis_data.json'),str(path)],cwd=ROOT.parent,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        print(result.stdout.strip())


if __name__=='__main__':unittest.main(verbosity=2)
