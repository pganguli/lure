import copy
import unittest

from lure.config.configuration import Config

class TestConfigMethods(unittest.TestCase):

    def setUp(self):
        self.config = Config(config = {
            "k1a": "v1a",
            "k1b": {
                "k2a": {
                    "k3a": "v3a",
                    "k3b": "v3b",
                },
                "k2b": "v2b"
            },
            "k1c": {
                "k2c": {
                    "k3d": [
                        { "k4a": "v4a" },
                        { "k4b": "v4b"}
                    ],
                    "k3c": "v3c",
                }
            }
        })

    def test_merge_dicts(self):
        dict_to_merge = {
            "k1a": "v1a2",
            "k1b": {
                "k2a": {
                    "k3b": "v3b2"
                }
            },
            "k1c": {
                "k2c": {
                    "k3d": [
                        { "k4a": "v4a2" },
                        { "k4c": "v4c" }
                    ]
                }
            }
        }

        expected_merged_dict = {
            "k1a": "v1a2",
            "k1b": {
                "k2a": {
                    "k3a": "v3a",
                    "k3b": "v3b2"
                },
                "k2b": "v2b"
            },
            "k1c": {
                "k2c": {
                    "k3d": [
                        { "k4a": "v4a2" },
                        { "k4b": "v4b", "k4c": "v4c" }
                    ],
                    "k3c": "v3c"
                }
            }         
        }

        Config.merge_dicts(self.config.config, dict_to_merge)
        self.assertEqual(self.config.config, expected_merged_dict)

    def test_get_dict_permutations(self):
        l = [0, 5, 10, 20]
        self.config.config["k1c"]["k2c"]["k3c"] = l

        expected_dict = { i: copy.deepcopy(self.config.config) for i in l }
        for v in l:
            expected_dict[v]["k1c"]["k2c"]["k3c"] = v

        output = Config.get_dict_permutations(self.config.config)
        self.assertEqual(output, expected_dict)