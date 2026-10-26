from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "traceability_checker",
    ROOT / "scripts" / "check-traceability.py",
)
assert SPEC is not None and SPEC.loader is not None
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
CONFIG = json.loads((ROOT / "traceability.json").read_text(encoding="utf-8"))


class ReadmeLinkTests(unittest.TestCase):
    def test_exact_markdown_and_html_links_are_accepted(self):
        readme = (
            f"[MKLab portal]({CONFIG['portal_url']})\n"
            f"[Open app]({CONFIG['overview_url']})"
        )
        self.assertEqual([], checker.check_readme(readme, CONFIG))
        html = (
            f'<a href="{CONFIG["portal_url"]}">MKLab portal</a> '
            f'<a href="{CONFIG["overview_url"]}">Open app</a>'
        )
        self.assertEqual([], checker.check_readme(html, CONFIG))

    def test_linked_image_is_a_visible_clickable_markdown_link(self):
        readme = (
            f"[![Portal badge](https://img.example/badge.svg)]"
            f"({CONFIG['portal_url']}) [Open app]({CONFIG['overview_url']})"
        )
        self.assertEqual([], checker.check_readme(readme, CONFIG))

    def test_spoofed_or_extended_urls_are_rejected(self):
        readme = (
            f"[Portal]({CONFIG['portal_url']}attacker.example) "
            f"[App]({CONFIG['overview_url']}?redirect=attacker.example)"
        )
        self.assertEqual(2, len(checker.check_readme(readme, CONFIG)))

    def test_comments_code_and_hidden_markup_do_not_count(self):
        readme = f"""<!-- [portal]({CONFIG["portal_url"]}) -->
```md
[app]({CONFIG["overview_url"]})
```
`[portal]({CONFIG["portal_url"]})`
<div hidden><a href="{CONFIG["portal_url"]}">hidden portal</a></div>
<p style="display: none"><a href="{CONFIG["overview_url"]}">hidden app</a></p>
<span aria-hidden="true"><a href="{CONFIG["portal_url"]}">hidden portal</a></span>
<script><a href="{CONFIG["overview_url"]}">not visible</a></script>
<a data-href="{CONFIG["portal_url"]}">not an href</a>"""
        self.assertEqual(2, len(checker.check_readme(readme, CONFIG)))

    def test_html_attributes_and_anchor_text_cannot_smuggle_markdown(self):
        readme = (
            f'<span data-value="[portal]({CONFIG["portal_url"]})">text</span> '
            f'<a href="https://attacker.example">'
            f"[Portal]({CONFIG['portal_url']})</a> "
            f'<a href="{CONFIG["overview_url"]}" hidden>'
            f"[app]({CONFIG['overview_url']})</a>"
        )
        self.assertEqual(2, len(checker.check_readme(readme, CONFIG)))

    def test_collapsed_details_content_is_not_a_visible_link(self):
        readme = (
            "<details><summary>More</summary>"
            f"[Portal]({CONFIG['portal_url']})</details> "
            f"[App]({CONFIG['overview_url']})"
        )
        errors = checker.check_readme(readme, CONFIG)
        self.assertEqual(1, len(errors))
        self.assertIn("portal", errors[0])

    def test_empty_visible_link_text_is_rejected(self):
        readme = f"[]({CONFIG['portal_url']}) [App]({CONFIG['overview_url']})"
        self.assertEqual(1, len(checker.check_readme(readme, CONFIG)))


class MappingTests(unittest.TestCase):
    def test_code_pinned_identity_matches_single_repo_config(self):
        self.assertEqual([], checker.validate_config(CONFIG))
        self.assertEqual(checker.EXPECTED, CONFIG)
        self.assertEqual(checker.EXPECTED["repository"], CONFIG["repository"])

    def test_repo_and_hostname_changes_are_rejected(self):
        for key, value in (
            ("app_id", "99"),
            ("repository", "mohammadrezwankhan/some-other-repo"),
            ("overview_url", "https://attacker.example/"),
            ("runtime_url", "https://attacker.example/run/"),
            ("metadata_url", "https://attacker.example/app.json"),
        ):
            with self.subTest(key=key):
                candidate = dict(CONFIG)
                candidate[key] = value
                self.assertTrue(checker.validate_config(candidate))

    def test_extra_mapping_fields_are_rejected(self):
        candidate = dict(CONFIG, private_manifest="must-not-be-copied")
        self.assertTrue(checker.validate_config(candidate))

    def test_github_identity_homepage_branch_and_visibility_are_exact(self):
        good = {
            "full_name": CONFIG["repository"],
            "default_branch": CONFIG["default_branch"],
            "homepage": CONFIG["overview_url"],
            "private": False,
        }
        self.assertEqual([], checker.validate_github_metadata(good, CONFIG))
        for key, value in (
            ("full_name", "mohammadrezwankhan/spoofed"),
            ("default_branch", "other"),
            ("homepage", CONFIG["overview_url"] + "?redirect=evil"),
            ("private", True),
        ):
            with self.subTest(key=key):
                candidate = dict(good)
                candidate[key] = value
                self.assertTrue(checker.validate_github_metadata(candidate, CONFIG))

    def test_live_check_requires_all_pages_and_exact_source_anchor(self):
        requested: list[str] = []
        bodies = {
            CONFIG["portal_url"]: "<html>portal</html>",
            CONFIG["overview_url"]: (
                f'<a href="{checker.REPOSITORY_URL}">Public source repository</a>'
            ),
            CONFIG["runtime_url"]: "<html>runtime</html>",
            CONFIG["metadata_url"]: json.dumps(
                {
                    "url": CONFIG["overview_url"],
                    "applicationUrl": CONFIG["runtime_url"],
                    "publicSource": checker.REPOSITORY_URL,
                }
            ),
            checker.REPOSITORY_URL: "<html>GitHub repository</html>",
        }

        def get_url(url: str):
            requested.append(url)
            return 200, bodies[url]

        metadata = {
            "full_name": CONFIG["repository"],
            "default_branch": CONFIG["default_branch"],
            "homepage": CONFIG["overview_url"],
            "private": False,
        }
        errors = checker.check_live(
            CONFIG,
            get_url=get_url,
            get_repo=lambda _repo, _token: metadata,
            token="test-token",
        )
        self.assertEqual([], errors)
        self.assertEqual(set(bodies), set(requested))

    def test_live_check_rejects_hidden_anchor_and_app_json_spoof(self):
        bodies = {
            CONFIG["portal_url"]: "ok",
            CONFIG["overview_url"]: (
                f'<div hidden><a href="{checker.REPOSITORY_URL}">'
                "hidden source</a></div>"
            ),
            CONFIG["runtime_url"]: "ok",
            CONFIG["metadata_url"]: json.dumps(
                {
                    "url": CONFIG["overview_url"],
                    "applicationUrl": CONFIG["runtime_url"],
                    "publicSource": "https://github.com/mohammadrezwankhan/spoofed",
                }
            ),
            checker.REPOSITORY_URL: "ok",
        }
        metadata = {
            "full_name": CONFIG["repository"],
            "default_branch": CONFIG["default_branch"],
            "homepage": CONFIG["overview_url"],
            "private": False,
        }
        errors = checker.check_live(
            CONFIG,
            get_url=lambda url: (200, bodies[url]),
            get_repo=lambda _repo, _token: metadata,
            token="test-token",
        )
        self.assertTrue(any("source anchor" in error for error in errors))
        self.assertTrue(any("publicSource" in error for error in errors))

    def test_private_mapping_skips_anonymous_repo_and_checks_api_visibility(self):
        private_config = dict(CONFIG, source_visibility="private")
        private_expected = dict(checker.EXPECTED, source_visibility="private")
        self.assertEqual(
            [],
            checker.validate_config(private_config, expected=private_expected),
        )
        requested: list[str] = []
        bodies = {
            private_config["portal_url"]: "<html>portal</html>",
            private_config["overview_url"]: "<html>source not shown</html>",
            private_config["runtime_url"]: "<html>runtime</html>",
            private_config["metadata_url"]: json.dumps(
                {
                    "url": private_config["overview_url"],
                    "runtime": private_config["runtime_url"],
                }
            ),
        }
        metadata = {
            "full_name": private_config["repository"],
            "default_branch": private_config["default_branch"],
            "homepage": private_config["overview_url"],
            "private": True,
        }

        def get_url(url: str):
            requested.append(url)
            return 200, bodies[url]

        errors = checker.check_live(
            private_config,
            get_url=get_url,
            get_repo=lambda _repo, _token: metadata,
            token="read-only-test-token",
        )
        self.assertEqual([], errors)
        self.assertNotIn(checker.REPOSITORY_URL, requested)
        self.assertEqual(set(bodies), set(requested))

        legacy = {"url": private_config["overview_url"]}
        bodies[private_config["metadata_url"]] = json.dumps(legacy)
        bodies[private_config["overview_url"]] = (
            '<a href="' + private_config["runtime_url"] + '">Open app</a>'
        )
        self.assertEqual(
            [],
            checker.check_live(
                private_config,
                get_url=get_url,
                get_repo=lambda _repo, _token: metadata,
                token="test-token",
            ),
        )
        bodies[private_config["overview_url"]] = "<p>No runtime link</p>"
        self.assertTrue(
            any(
                "overview must visibly link" in error
                for error in checker.check_live(
                    private_config,
                    get_url=get_url,
                    get_repo=lambda _repo, _token: metadata,
                    token="test-token",
                )
            )
        )
        conflicting = json.loads(bodies[private_config["metadata_url"]])
        conflicting["applicationUrl"] = "https://wrong.example/runtime/"
        bodies[private_config["metadata_url"]] = json.dumps(conflicting)
        errors = checker.check_live(
            private_config,
            get_url=get_url,
            get_repo=lambda _repo, _token: metadata,
            token="read-only-test-token",
        )
        self.assertTrue(any("applicationUrl" in error for error in errors))

    def test_private_mapping_rejects_url_leaks_in_public_pages(self):
        private_config = dict(CONFIG, source_visibility="private")
        bodies = {
            private_config["portal_url"]: "ok",
            private_config["overview_url"]: (
                f'<a href="{checker.REPOSITORY_URL}">leaked</a>'
            ),
            private_config["runtime_url"]: "ok",
            private_config["metadata_url"]: json.dumps(
                {
                    "url": private_config["overview_url"],
                    "applicationUrl": private_config["runtime_url"],
                }
            ),
        }
        metadata = {
            "full_name": private_config["repository"],
            "default_branch": private_config["default_branch"],
            "homepage": private_config["overview_url"],
            "private": True,
        }
        errors = checker.check_live(
            private_config,
            get_url=lambda url: (200, bodies[url]),
            get_repo=lambda _repo, _token: metadata,
            token="read-only-test-token",
        )
        self.assertTrue(
            any("private repository URL is leaked" in error for error in errors)
        )

    def test_live_check_fails_closed_without_gh_token(self):
        errors = checker.check_live(
            CONFIG,
            get_url=lambda _url: (200, ""),
            token="",
        )
        self.assertTrue(any("GH_TOKEN is required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
