import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from openpyxl import load_workbook

import org_ghas_report as report


def response(data=None, status=200, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(data).encode()
    result.url = "https://api.github.com/test"
    result.headers.update(headers or {})
    return result


def http_error(status):
    return requests.HTTPError("API access denied", response=response({}, status))


class ReportTests(unittest.TestCase):
    def test_csv_bom_dedup_custom_header_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orgs.csv"
            path.write_text("\ufeffTeam,GitHub Organization\nA, octo-org \nB,OCTO-ORG\n\nC,second\n",
                            encoding="utf-8")
            self.assertEqual(report.read_organizations(path, "GitHub Organization"),
                             ["octo-org", "second"])
            path.write_text("octo-org\nsecond\n", encoding="utf-8")
            self.assertEqual(report.read_organizations(path), ["octo-org", "second"])
            path.write_text("organization\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no organizations"):
                report.read_organizations(path)
            path.write_text("organization\nhttps://github.com/octo\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid"):
                report.read_organizations(path)

    def test_pagination_rate_limit_and_access_failure(self):
        api = report.GitHub("test-token", "https://api.github.com")
        api.session.get = Mock(side_effect=[
            response({}, 429, {"Retry-After": "1"}),
            response([{"name": "a"}], headers={
                "Link": '<https://api.github.com/orgs/octo/repos?page=2>; rel="next"'
            }),
            response([{"name": "b"}]),
            response({}, 403),
        ])
        with patch.object(report.time, "sleep") as sleep:
            self.assertEqual(list(api.items("orgs/octo/repos", type="private")),
                             [{"name": "a"}, {"name": "b"}])
            sleep.assert_called_once_with(1)
        self.assertEqual(api.session.get.call_args_list[2].kwargs["params"], {})
        self.assertIn("page=2", api.session.get.call_args_list[2].args[0])
        with self.assertRaises(requests.HTTPError):
            api.get("denied")
        api.session.close()

    def make_api(self):
        api = Mock()
        repos = [
            {"full_name": "octo/active", "private": True, "permissions": {"admin": True},
             "security_and_analysis": {"secret_scanning": {"status": "enabled"}}},
            {"full_name": "octo/idle", "private": True, "permissions": {"admin": True},
             "security_and_analysis": {"secret_scanning": {"status": "disabled"}}},
            {"full_name": "octo/public", "private": False},
            {"full_name": "octo/internal", "private": True, "visibility": "internal"},
        ]

        def items(path, **params):
            if path.endswith("/repos"):
                return iter(repos)
            closed = {
                "code-scanning": ["fixed", "dismissed"],
                "secret-scanning": ["resolved"],
                "dependabot": ["fixed", "dismissed", "auto_dismissed"],
            }
            endpoint = path.split("/")[2]
            expected_filter = (
                "closed" if endpoint == "code-scanning"
                else ",".join(sorted(closed[endpoint]))
            )
            self.assertIn(params["state"], ("open", expected_filter))
            states = ["open"] if params["state"] == "open" else closed[endpoint]
            return iter([
                {"state": state, "repository": {"full_name": name}}
                for name in ("octo/active", "octo/public", "octo/internal")
                for state in states
            ])

        def get(path, params=None):
            if path.endswith("/analyses"):
                return response([{"id": 1}] if "/active/" in path else [])
            if "/idle/" in path:
                raise http_error(404)
            return response(None, 204)

        api.items.side_effect = items
        api.get.side_effect = get
        return api

    def test_private_scope_coverage_all_closed_states_and_totals(self):
        api = self.make_api()
        errors = []
        row = report.collect_org(api, "octo", errors)
        self.assertEqual(errors, [])
        self.assertEqual(row["Private Repo Count"], 2)
        for feature in ("Code Scanning", "Secret Scanning", "Dependabot"):
            self.assertEqual(row[f"{feature} Coverage"], 0.5)
            self.assertEqual(row[f"{feature} Open"], 1)
        self.assertEqual(row["Code Scanning Closed"], 2)
        self.assertEqual(row["Secret Scanning Closed"], 1)
        self.assertEqual(row["Dependabot Closed"], 3)
        self.assertEqual(row["Total Open Alerts"], 3)
        self.assertEqual(row["Total Closed Alerts"], 6)
        self.assertEqual(row["Autofix Enabled Repo Count"], "N/A")

    def test_code_scanning_403_without_advanced_security_counts_as_disabled(self):
        api = self.make_api()
        original_get = api.get.side_effect

        def get(path, params=None):
            if path.endswith("/analyses") and "/idle/" in path:
                raise requests.HTTPError("denied", response=response(
                    {"message": "Advanced Security must be enabled for this repository "
                                "to use code scanning."}, 403))
            return original_get(path, params)

        api.get.side_effect = get
        errors = []
        row = report.collect_org(api, "octo", errors)
        self.assertEqual(errors, [])
        self.assertEqual(row["Code Scanning Coverage"], 0.5)

    def test_dependabot_fallback_for_non_admin_security_manager(self):
        api = Mock()
        repo = {"permissions": {"admin": False}}

        def get(path, params=None):
            if path.endswith("/vulnerability-alerts"):
                raise http_error(404)
            if "/off/" in path or "/archived/" in path:
                message = ("Dependabot alerts are disabled for this repository."
                           if "/off/" in path else
                           "Dependabot alerts are not available for archived repositories.")
                raise requests.HTTPError("denied", response=response({"message": message}, 403))
            if "/denied/" in path:
                raise http_error(403)
            return response([])

        api.get.side_effect = get
        self.assertTrue(report.dependabot_enabled(api, "repos/o/on", repo))
        self.assertFalse(report.dependabot_enabled(api, "repos/o/off", repo))
        self.assertFalse(report.dependabot_enabled(api, "repos/o/archived", repo))
        with self.assertRaises(requests.HTTPError):
            report.dependabot_enabled(api, "repos/o/denied", repo)

    def test_unknown_settings_and_alert_failures_are_not_zero(self):
        api = self.make_api()
        original_items = api.items.side_effect

        def items(path, **params):
            if path.endswith("/repos"):
                return iter([{"full_name": "octo/active", "private": True}])
            if "secret-scanning" in path:
                raise http_error(403)
            return original_items(path, **params)

        api.items.side_effect = items
        api.get.side_effect = http_error(404)
        errors = []
        with contextlib.redirect_stderr(io.StringIO()):
            row = report.collect_org(api, "octo", errors)
        for header in ("Code Scanning Coverage", "Secret Scanning Coverage",
                       "Dependabot Coverage", "Secret Scanning Open",
                       "Total Open Alerts", "Total Closed Alerts"):
            self.assertEqual(row[header], "N/A", header)
        self.assertEqual(row["Code Scanning Open"], 1)
        self.assertEqual(len(errors), 4)

    def test_empty_org_and_failed_inventory(self):
        api = Mock()
        api.items.return_value = iter([])
        errors = []
        row = report.collect_org(api, "octo", errors)
        self.assertEqual(row["Private Repo Count"], 0)
        self.assertEqual(row["Total Closed Alerts"], 0)
        self.assertEqual(row["Code Scanning Coverage"], 0.0)
        api.get.assert_not_called()
        api.items.side_effect = http_error(404)
        with contextlib.redirect_stderr(io.StringIO()):
            row = report.collect_org(api, "missing", errors)
        self.assertEqual(row["Private Repo Count"], "N/A")
        self.assertEqual(len(errors), 1)

    def test_cli_writes_workbook_and_preserves_partial_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orgs.csv"
            output = Path(directory) / "report.xlsx"
            source.write_text("organization\nocto\nmissing\nbroken\n", encoding="utf-8")
            api = self.make_api()
            original_items = api.items.side_effect

            def items(path, **params):
                if path.startswith("orgs/missing/"):
                    raise http_error(404)
                if path.startswith("orgs/broken/"):
                    raise RuntimeError("unexpected")
                return original_items(path, **params)

            api.items.side_effect = items
            with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}), \
                    patch.object(report, "GitHub", return_value=api), \
                    patch("sys.argv", ["report", str(source), "-o", str(output)]), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(report.main(), 1)
            workbook = load_workbook(output)
            sheet = workbook["GHAS Format"]
            self.assertEqual([cell.value for cell in sheet[2]], report.HEADERS)
            self.assertEqual(sheet["I1"].value, "Code Scanning (all tools)")
            self.assertEqual(sheet["O1"].value, "All Alert Types")
            self.assertIn("I1:J1", {str(r) for r in sheet.merged_cells.ranges})
            self.assertEqual(sheet.freeze_panes, "B3")
            self.assertEqual(sheet.max_column, 16)
            self.assertEqual(sheet.max_row, 5)
            self.assertEqual(sheet["C3"].value, 0.5)
            self.assertEqual(sheet["C3"].number_format, "0.0%")
            self.assertEqual(sheet["O3"].value, "=I3+K3+M3")
            self.assertEqual(sheet["P3"].value, "=J3+L3+N3")
            self.assertEqual(sheet["B4"].value, "N/A")
            self.assertEqual(sheet["P4"].value, "N/A")
            self.assertEqual(sheet["A5"].value, "broken")
            self.assertEqual(sheet["B5"].value, "N/A")
            self.assertEqual(workbook["Errors"].max_row, 3)
            self.assertIn("Notes", workbook.sheetnames)
            workbook.close()
            api.session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
