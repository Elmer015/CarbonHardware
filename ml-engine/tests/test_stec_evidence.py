import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml-engine" / "carbon"))

from stec import (
    STECDieComponent,
    STECIncompleteError,
    calculate_market_based_stec,
    calculate_multi_die_stec,
    calculate_stec,
)
from stec_evidence import load_evidence, resolve_processor_stec


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class StecMarketAndMultiDieTests(unittest.TestCase):
    def test_market_based_requires_sourced_contract(self):
        with self.assertRaises(STECIncompleteError):
            calculate_market_based_stec(
                die_area_mm2=100, node_nm=28, market_based_factor_g_co2e_per_kwh=0,
                contract_type="", factor_source="", foundry="TSMC",
                manufacturing_region="Taiwan", manufacturing_year=2022,
            )
        result = calculate_market_based_stec(
            die_area_mm2=100, node_nm=28, market_based_factor_g_co2e_per_kwh=0,
            contract_type="PPA", factor_source="test disclosure", foundry="TSMC",
            manufacturing_region="Taiwan", manufacturing_year=2022,
        )
        self.assertEqual(result.attribution, "market-based")
        self.assertAlmostEqual(result.stec_kg_co2e, 0.6)

    def test_multi_die_sums_each_die_with_its_own_node_and_region(self):
        total = calculate_multi_die_stec([
            STECDieComponent("CCD", 100, 7, "Taiwan", 2022, 561),
            STECDieComponent("IOD", 100, 12, "United States", 2022, 367),
        ])
        ccd = calculate_stec(die_area_mm2=100, node_nm=7, grid_intensity_g_co2e_per_kwh=561, manufacturing_region="Taiwan", manufacturing_year=2022)
        iod = calculate_stec(die_area_mm2=100, node_nm=12, grid_intensity_g_co2e_per_kwh=367, manufacturing_region="United States", manufacturing_year=2022)
        self.assertAlmostEqual(total.stec_kg_co2e, ccd.stec_kg_co2e + iod.stec_kg_co2e)
        self.assertEqual(iod.assumptions["explicit_proxy_node"], "12")


class StecEvidenceResolverTests(unittest.TestCase):
    def setUp(self):
        load_evidence.cache_clear()
        self.tmp = tempfile.TemporaryDirectory()
        directory = Path(self.tmp.name)
        write(directory / "grid.csv", "entity,code,year,co2_intensity__gco2_kwh\nTaiwan,TWN,2020,500\nUnited States,USA,2020,400\nIreland,IRL,2020,300\nWorld,OWID_WRL,2020,450\n")
        write(directory / "fab-rules.csv", "vendor,type,node_nm,candidate_regions,foundry,confidence,basis\nIntel,CPU,*,United States;Ireland,Intel,unresolved,test rule\nAMD,CPU,7,Taiwan,TSMC,medium,test rule\n")
        write(directory / "fab-provenance.csv", "vendor,type,product,process_node_nm,manufacturing_region,foundry,confidence,source\nNVIDIA,GPU,Sourced GPU,7,Taiwan,TSMC,high,whitepaper\n")
        write(directory / "chiplets.csv", "product,die_role,die_count,die_area_mm2,node_nm,manufacturing_region,foundry,confidence,source\nChiplet CPU,CCD,2,50,7,Taiwan,TSMC,medium,paper\nChiplet CPU,IOD,1,100,12,United States,GlobalFoundries,medium,paper\n")
        write(directory / "manufacturing-years.csv", "product,release_year,manufacturing_year,source\n")
        write(directory / "yields.csv", "process_node_nm,foundry,year,yield_factor,source\n7,TSMC,2020,0.8,yield study\n")
        write(directory / "market-factors.csv", "foundry,year,market_based_factor_g_co2e_per_kwh,contract_type,source\nTSMC,2020,100,PPA,ESG report\n")
        self.evidence = load_evidence(str(directory), str(directory / "grid.csv"))

    def tearDown(self):
        self.tmp.cleanup()
        load_evidence.cache_clear()

    def processor(self, name, vendor, kind, node=7, area=100):
        return {"name": name, "vendor": vendor, "type": kind, "processSizeNm": node, "dieAreaMm2": area, "releaseYear": 2020}

    def test_product_level_provenance_gives_point_with_yield_and_market_based(self):
        result = resolve_processor_stec(self.processor("Sourced GPU", "NVIDIA", "GPU"), evidence=self.evidence)
        self.assertEqual((result["status"], result["location"]["level"]), ("point", "product_sourced"))
        region = result["regions"][0]
        self.assertTrue(region["yield"]["applied"])
        expected = (200 + 500 + 500 * 1.52) / 1000 / 0.8
        self.assertAlmostEqual(result["stecKgCo2e"], expected)
        self.assertEqual(region["marketBased"]["status"], "computed")
        self.assertAlmostEqual(region["marketBased"]["stecKgCo2e"], (200 + 500 + 100 * 1.52) / 1000 / 0.8)
        self.assertEqual(result["manufacturingYearStatus"], "release_year_proxy")

    def test_unresolved_fab_rule_gives_range_not_point(self):
        result = resolve_processor_stec(self.processor("Some Xeon", "Intel", "CPU", node=14), evidence=self.evidence)
        self.assertEqual(result["status"], "range")
        self.assertIsNone(result["stecKgCo2e"])
        self.assertLess(result["stecMinKgCo2e"], result["stecMaxKgCo2e"])

    def test_user_region_and_year_override(self):
        result = resolve_processor_stec(self.processor("Some Xeon", "Intel", "CPU", node=14), manufacturing_region="Ireland", manufacturing_year=2020, evidence=self.evidence)
        self.assertEqual((result["status"], result["location"]["level"], result["manufacturingYearStatus"]), ("point", "user_input", "user_input"))
        missing_ci = resolve_processor_stec(self.processor("Some Xeon", "Intel", "CPU", node=14), manufacturing_region="Ireland", manufacturing_year=1999, evidence=self.evidence)
        self.assertEqual(missing_ci["status"], "incomplete")
        self.assertIsNone(missing_ci["stecKgCo2e"])

    def test_chiplet_products_sum_dies(self):
        result = resolve_processor_stec(self.processor("Chiplet CPU", "AMD", "CPU", area=100), evidence=self.evidence)
        self.assertTrue(result["chiplet"]["applied"])
        self.assertEqual(result["location"]["level"], "chiplet_sourced")
        ccd = 2 * (200 + 500 + 500 * 1.52) * 0.5 / 1000 / 0.8
        iod = (125 + 500 + 400 * 1.2) * 1.0 / 1000
        self.assertAlmostEqual(result["stecKgCo2e"], ccd + iod)
        self.assertEqual(result["chiplet"]["totalDieAreaMm2"], 200)


if __name__ == "__main__":
    unittest.main()
