"""End-to-end CLI and error-contract smoke tests (no network)."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run_cli(payload):
    return subprocess.run([sys.executable, "-m", "eg_shopping"],
                          cwd=ROOT, input=json.dumps(payload),
                          capture_output=True, text=True, check=False)


class CliContract(unittest.TestCase):
    def test_documented_price_fixture_is_executable(self):
        request = json.loads((ROOT / "examples/compare_request.json").read_text())
        process = run_cli(request)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["targetObservationId"], "T")
        self.assertIn("RED_SAME_BIO_CHEAPER", result["signals"])
        self.assertIn("GREY_MAY_BE_CHEAPER", result["signals"])
        self.assertEqual(result["alternatives"][0]["priceDifferenceCents"], -20)
        self.assertIsNone(result["alternatives"][0]["checkoutCents"])
        self.assertTrue(result["incomplete"])

    def test_cli_bad_operation_reports_json_error_not_silent_success(self):
        process = run_cli({"operation": "bookPurchase", "amount": 100})
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, "")
        error = json.loads(process.stderr)
        self.assertEqual(error["error"]["code"], "INVALID_SNAPSHOT")

    def test_cli_bad_date_reports_error_without_bogus_price(self):
        request = json.loads((ROOT / "examples/compare_request.json").read_text())
        request["shoppingDate"] = "2026-13-99"
        process = run_cli(request)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stderr)["error"]["code"],
                         "INVALID_SNAPSHOT")

    def test_cli_need_projection_does_not_mutate_host(self):
        request = {"operation": "projectNeeds",
                   "snapshot": {"asOf": "2026-10-31", "stock": [],
                                "demands": [{"eventId": "D1",
                                             "foodTypeId": "oats",
                                             "dueDate": "2026-10-31",
                                             "quantity": {"amount": 100, "unit": "g",
                                                          "basis": "NET", "confirmed": True},
                                             "kind": "PREPARATION_RAW"}]}}
        process = run_cli(request)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["horizons"]["1"]["totals"][0]["quantityToBuy"], 100)
        self.assertEqual(result["sideEffects"], [])


if __name__ == "__main__":
    unittest.main()
