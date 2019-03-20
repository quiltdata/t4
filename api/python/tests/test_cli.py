from unittest import TestCase

from t4 import main

create_parser = main.create_parser

class CommandLineTestCase(TestCase):
    """
    Base TestCase class, sets up a CLI parser
    """
    @classmethod
    def setUpClass(cls):
        parser = create_parser()
        cls.parser = parser

class T4CLITestCase(CommandLineTestCase):
    def test_t4_config(self):
        args = self.parser.parse_args(['config', 'https://foo.bar'])
        assert args.catalog_url == 'https://foo.bar'
        assert args.func == main.config_with_catalog_url
