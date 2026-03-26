import unittest

from app.prompts.character import build_character_section


class CharacterPromptTests(unittest.TestCase):
    def test_build_character_section_prefers_visual_dna(self):
        section = build_character_section(
            {
                "characters": [
                    {"name": "李明", "role": "主角", "description": "青年男子，黑色短发。"},
                ],
                "character_images": {
                    "李明": {
                        "visual_dna": "young man, short black hair, slim build",
                        "design_prompt": "Full-body character design sheet for 李明, dark blue robe",
                    }
                },
            }
        )

        self.assertIn("Visual DNA: young man, short black hair, slim build", section)
        self.assertNotIn("Full-body character design sheet", section)

    def test_build_character_section_falls_back_to_design_prompt(self):
        section = build_character_section(
            {
                "characters": [
                    {"name": "李明", "role": "主角", "description": "青年男子，黑色短发。"},
                ],
                "character_images": {
                    "李明": {
                        "design_prompt": "Full-body character design sheet for 李明, dark blue robe, fabric texture",
                    }
                },
            }
        )

        self.assertIn(
            "Visual DNA: Full-body character design sheet for 李明, dark blue robe, fabric texture",
            section,
        )

    def test_build_character_section_falls_back_to_legacy_prompt(self):
        section = build_character_section(
            {
                "characters": [
                    {"name": "李明", "role": "主角", "description": "青年男子，黑色短发。"},
                ],
                "character_images": {
                    "李明": {
                        "prompt": "Legacy portrait prompt for 李明, dark blue robe",
                    }
                },
            }
        )

        self.assertIn("Visual DNA: Legacy portrait prompt for 李明, dark blue robe", section)


if __name__ == "__main__":
    unittest.main()
