"""BG-01 regression: the Graph and Intelligence API modules import on every supported Python."""

import importlib
import pkgutil

from django.db.models import Model
from django.test import SimpleTestCase

import app.business_graph
import app.business_intelligence


class ModuleImportTests(SimpleTestCase):
    def test_every_graph_and_intelligence_module_imports(self):
        for package in (app.business_graph, app.business_intelligence):
            for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                if ".tests" in info.name:
                    continue
                with self.subTest(module=info.name):
                    importlib.import_module(info.name)

    def test_supported_entity_models_are_django_models(self):
        from app.business_graph.projection import SUPPORTED_ENTITY_MODELS

        self.assertEqual(len(SUPPORTED_ENTITY_MODELS), 14)
        for entity_type, model in SUPPORTED_ENTITY_MODELS.items():
            with self.subTest(entity_type=entity_type):
                self.assertTrue(issubclass(model, Model))
