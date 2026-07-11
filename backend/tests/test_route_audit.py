"""Regression tests for the static route audit parser."""

import unittest

from audit import route_declarations


class RouteAuditParserTests(unittest.TestCase):
    def test_route_declarations_collects_api_route_methods(self):
        source = '''
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "healthy"}
'''

        routes = route_declarations(source)

        self.assertIn(("GET", "/health"), routes)
        self.assertIn(("HEAD", "/health"), routes)


if __name__ == "__main__":
    unittest.main()
