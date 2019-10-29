import pytest

from CityJSON_Blender_parser import get_scene_name

class TestFunctions:
    """A class to test all the functions (that's all we have!)"""

    def test_scene_name(self):
        """Test the scene name is formatted correctly"""

        assert get_scene_name(1) == "LoD 1"
        assert get_scene_name(2) == "LoD 2"
        assert get_scene_name("2.1") == "LoD 2.1"