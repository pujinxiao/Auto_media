import unittest

import sys
import types

llm_factory_stub = types.ModuleType("app.services.llm.factory")
llm_factory_stub.get_llm_provider = lambda *args, **kwargs: None
sys.modules.setdefault("app.services.llm.factory", llm_factory_stub)

from app.services.storyboard import (
    _build_minimal_valid_shot_item,
    _limit_core_shot_items,
    _normalize_shot_item,
    _postprocess_shot,
)
from app.schemas.storyboard import Shot


class StoryboardNormalizationTests(unittest.TestCase):
    def test_normalize_shot_item_backfills_narration_speaker(self):
        shot = _normalize_shot_item(
            {
                "characters": ["李明"],
                "storyboard_description": "他停在门口，旁白落下。",
                "audio_reference": {
                    "type": "narration",
                    "content": "他知道，门后的一切都会改变。",
                },
            },
            shot_number=1,
        )

        self.assertEqual(shot["audio_reference"]["type"], "narration")
        self.assertEqual(shot["audio_reference"]["speaker"], "旁白")

    def test_normalize_shot_item_backfills_single_character_dialogue_speaker(self):
        shot = _normalize_shot_item(
            {
                "characters": ["李明"],
                "storyboard_description": "他停在门口，说出一句提醒。",
                "audio_reference": {
                    "type": "dialogue",
                    "content": "别进去。",
                },
            },
            shot_number=1,
        )

        self.assertEqual(shot["audio_reference"]["type"], "dialogue")
        self.assertEqual(shot["audio_reference"]["speaker"], "李明")

    def test_normalize_shot_item_rewrites_generic_pronoun_speaker_to_single_character(self):
        shot = _normalize_shot_item(
            {
                "characters": ["李明"],
                "storyboard_description": "他停在门口，说出一句提醒。",
                "audio_reference": {
                    "type": "dialogue",
                    "speaker": "他",
                    "content": "别进去。",
                },
            },
            shot_number=1,
        )

        self.assertEqual(shot["audio_reference"]["speaker"], "李明")

    def test_normalize_shot_item_does_not_guess_dialogue_speaker_with_multiple_characters(self):
        shot = _normalize_shot_item(
            {
                "characters": ["李明", "老板"],
                "storyboard_description": "两人对峙，其中一人先开口。",
                "audio_reference": {
                    "type": "dialogue",
                    "speaker": "他",
                    "content": "别进去。",
                },
            },
            shot_number=1,
        )

        self.assertIsNone(shot["audio_reference"]["speaker"])

    def test_build_minimal_valid_shot_item_uses_same_audio_backfill_rules(self):
        shot = _build_minimal_valid_shot_item(
            {
                "characters": ["李明"],
                "storyboard_description": "他停在门口，说出一句提醒。",
                "dialogue": "别进去。",
            },
            shot_number=1,
        )

        self.assertEqual(shot["audio_reference"]["type"], "dialogue")
        self.assertEqual(shot["audio_reference"]["speaker"], "李明")

    def test_limit_core_shot_items_keeps_only_three_shots_per_scene(self):
        limited = _limit_core_shot_items(
            [
                {
                    "shot_id": "scene1_shot1",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头一",
                    "scene_position": "establishing",
                    "characters": ["李明"],
                },
                {
                    "shot_id": "scene1_shot2",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头二",
                    "scene_position": "development",
                },
                {
                    "shot_id": "scene1_shot3",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头三",
                    "scene_position": "development",
                    "scene_intensity": "high",
                    "audio_reference": {"type": "dialogue", "speaker": "李明", "content": "别进去。"},
                    "characters": ["李明"],
                },
                {
                    "shot_id": "scene1_shot4",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头四",
                    "scene_position": "development",
                },
                {
                    "shot_id": "scene1_shot5",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头五",
                    "scene_position": "resolution",
                    "characters": ["李明"],
                },
            ]
        )

        self.assertEqual(len(limited), 3)
        self.assertEqual([item["shot_id"] for item in limited], ["scene1_shot1", "scene1_shot2", "scene1_shot3"])
        self.assertEqual(limited[0]["storyboard_description"], "镜头一")
        self.assertEqual(limited[1]["storyboard_description"], "镜头三")
        self.assertEqual(limited[2]["storyboard_description"], "镜头五")
        self.assertIsNone(limited[0]["transition_from_previous"])
        self.assertIn("主衣物", limited[1]["transition_from_previous"])
        self.assertIn("主衣物", limited[2]["transition_from_previous"])

    def test_limit_core_shot_items_merges_omitted_content_into_retained_shots(self):
        limited = _limit_core_shot_items(
            [
                {
                    "shot_id": "scene1_shot1",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头一展示走廊入口",
                    "scene_position": "establishing",
                },
                {
                    "shot_id": "scene1_shot2",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头二里李明推门进入回廊",
                    "visual_elements": {
                        "subject_and_clothing": "李明，深色长袍",
                        "action_and_expression": "推门进入回廊",
                        "environment_and_props": "木门与回廊立柱",
                        "lighting_and_color": "暖色灯笼光",
                    },
                    "characters": ["李明"],
                    "scene_position": "development",
                },
                {
                    "shot_id": "scene1_shot3",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头三展示他停步观察",
                    "scene_position": "development",
                },
                {
                    "shot_id": "scene1_shot4",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头四里桌上密信被展开",
                    "visual_elements": {
                        "subject_and_clothing": "",
                        "action_and_expression": "伸手展开密信",
                        "environment_and_props": "木桌上的密信",
                        "lighting_and_color": "",
                    },
                    "audio_reference": {"type": "narration", "speaker": "旁白", "content": "密信内容终于暴露。"},
                    "scene_position": "development",
                },
                {
                    "shot_id": "scene1_shot5",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头五展示李明的最终反应",
                    "scene_position": "resolution",
                },
            ]
        )

        self.assertEqual(len(limited), 3)
        self.assertIn("镜头二里李明推门进入回廊", limited[1]["storyboard_description"])
        self.assertIn("镜头四里桌上密信被展开", limited[1]["storyboard_description"])
        self.assertIn("李明", limited[1]["characters"])

    def test_limit_core_shot_items_normalizes_short_scene_shot_ids(self):
        limited = _limit_core_shot_items(
            [
                {
                    "shot_id": "scene1",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头一",
                },
                {
                    "shot_id": "scene2",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头二",
                },
                {
                    "shot_id": "scene3",
                    "source_scene_key": "ep01_scene01",
                    "storyboard_description": "镜头三",
                },
            ]
        )

        self.assertEqual([item["shot_id"] for item in limited], ["scene1_shot1", "scene1_shot2", "scene1_shot3"])
        self.assertIsNone(limited[0]["transition_from_previous"])

    def test_postprocess_shot_trims_verbose_fields_but_keeps_core_visual_motion_and_continuity(self):
        shot = _postprocess_shot(
            Shot(
                **_normalize_shot_item(
                    {
                        "shot_id": "scene1_shot2",
                        "scene_position": "development",
                        "storyboard_description": (
                            "李明停在半开的木门前，右手还扶着门边，雨水在门槛上反光。"
                            "他朝内堂抬眼，呼吸压得很轻。"
                            "柜台后的暖灯和门外冷雨还保持不变。"
                            "镜头继续强调他心里的犹豫与局势的复杂变化。"
                        ),
                        "visual_elements": {
                            "subject_and_clothing": "李明，深蓝长衫，发梢微湿，右手扶门，身体半侧朝向内堂，衣摆被雨气打湿",
                            "action_and_expression": "停顿后抬眼看向内堂，嘴唇微张，眉心轻轻收紧，同时保持随时推门的起势",
                            "environment_and_props": "半开木门、湿润门槛、柜台、算盘、门外雨丝、屋内暖灯、门框阴影和内堂桌椅",
                            "lighting_and_color": "门外冷色雨夜天光和屋内暖黄灯笼补光同时存在，整体冷暖对比明显",
                        },
                        "image_prompt": (
                            "Medium shot. Li Ming pauses at the half-open wooden door with one hand braced on the edge. "
                            "Rain glints on the threshold, the counter and abacus sit deeper inside, and warm lantern light holds behind him. "
                            "Highly detailed cinematic lighting, 8k, masterpiece."
                        ),
                        "final_video_prompt": (
                            "Medium shot. Slow Dolly in. Li Ming pauses at the half-open wooden door with one hand braced on the edge, "
                            "then slowly lifts his gaze toward the teahouse counter and prepares to step inside while the warm lantern light "
                            "and rainy threshold remain stable in the same location. Highly detailed cinematic lighting, 8k."
                        ),
                        "transition_from_previous": (
                            "承接上一镜头，保持李明的外观与主衣物不变。"
                            "右手仍扶着门边，门扇开合幅度与门外雨夜冷光保持连续。"
                            "镜头语言继续延续外景切入内堂的压迫感。"
                        ),
                        "mood": "restrained tension with quiet hesitation",
                    },
                    shot_number=2,
                )
            )
        )

        self.assertIn("李明停在半开的木门前", shot.storyboard_description)
        self.assertIn("他朝内堂抬眼", shot.storyboard_description)
        self.assertNotIn("局势的复杂变化", shot.storyboard_description)
        self.assertNotIn("Highly detailed", shot.image_prompt)
        self.assertNotIn("8k", shot.final_video_prompt)
        self.assertIn("Slow Dolly in", shot.final_video_prompt)
        self.assertIn("抬眼看向内堂", shot.visual_elements.action_and_expression)
        self.assertNotIn("镜头语言继续延续", shot.transition_from_previous)
        self.assertIn("右手仍扶着门边", shot.transition_from_previous)
        self.assertEqual(shot.mood, "restrained tension with quiet hesitation")

    def test_postprocess_shot_reanchors_sparse_image_prompt_with_subject_and_environment(self):
        shot = _postprocess_shot(
            Shot(
                **_normalize_shot_item(
                    {
                        "shot_id": "scene1_shot2",
                        "scene_position": "development",
                        "storyboard_description": "继续，云影利用阴影和障碍物隐藏自己。",
                        "camera_setup": {"shot_size": "MS", "camera_angle": "Eye-level", "movement": "Static"},
                        "visual_elements": {
                            "subject_and_clothing": "云影身着黑色紧身衣，头戴面纱",
                            "action_and_expression": "利用阴影和障碍物隐藏自己，表情紧张",
                            "environment_and_props": "狭窄街道，古老石墙，紧闭木门，昏黄街灯",
                            "lighting_and_color": "昏黄灯光，暗淡环境",
                        },
                        "image_prompt": "云影利用阴影和障碍物隐藏自己，表情紧张",
                        "final_video_prompt": "云影利用阴影和障碍物隐藏自己，突然一群刺客从四面八方涌来，她迅速做出反应",
                    },
                    shot_number=2,
                )
            )
        )

        self.assertIn("云影身着黑色紧身衣", shot.image_prompt)
        self.assertIn("狭窄街道", shot.image_prompt)
        self.assertIn("隐藏自己", shot.image_prompt)


if __name__ == "__main__":
    unittest.main()
