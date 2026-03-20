import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.schemas.story import AnalyzeIdeaRequest, GenerateOutlineRequest, GenerateScriptRequest, ChatRequest, RefineRequest, WorldBuildingStartRequest, WorldBuildingTurnRequest
from app.services.story_llm import analyze_idea, generate_outline, generate_script, chat, refine, world_building_start, world_building_turn
from app.services.store import get_story, save_story

router = APIRouter(prefix="/api/v1/story", tags=["story"])


def get_llm_config(request: Request):
    return {
        "api_key": request.headers.get("X-LLM-API-Key", ""),
        "base_url": request.headers.get("X-LLM-Base-URL", ""),
        "provider": request.headers.get("X-LLM-Provider", ""),
    }


@router.post("/analyze-idea")
async def api_analyze_idea(req: AnalyzeIdeaRequest, request: Request):
    return await analyze_idea(req.idea, req.genre, req.tone, **get_llm_config(request))


@router.post("/generate-outline")
async def api_generate_outline(req: GenerateOutlineRequest, request: Request):
    return await generate_outline(req.story_id, req.selected_setting, **get_llm_config(request))


@router.post("/chat")
async def api_chat(req: ChatRequest, request: Request):
    cfg = get_llm_config(request)

    async def event_stream():
        try:
            async for chunk in chat(req.story_id, req.message, **cfg):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generate-script")
async def api_generate_script(req: GenerateScriptRequest, request: Request):
    cfg = get_llm_config(request)

    async def event_stream():
        scenes = []
        try:
            async for scene in generate_script(req.story_id, **cfg):
                if "__usage__" not in scene:
                    scenes.append(scene)
                    yield f"data: {json.dumps(scene, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps(scene, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        # 保存完整剧本供第二阶段使用
        save_story(req.story_id, {"scenes": scenes})
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/refine")
async def api_refine(req: RefineRequest, request: Request):
    return await refine(req.story_id, req.change_type, req.change_summary, **get_llm_config(request))


@router.post("/world-building/start")
async def api_wb_start(req: WorldBuildingStartRequest, request: Request):
    return await world_building_start(req.idea, **get_llm_config(request))


@router.post("/world-building/turn")
async def api_wb_turn(req: WorldBuildingTurnRequest, request: Request):
    return await world_building_turn(req.story_id, req.answer, **get_llm_config(request))


@router.post("/{story_id}/finalize")
async def finalize_script(story_id: str):
    """把第一阶段剧本序列化为文本，供第二阶段 pipeline 使用"""
    story = get_story(story_id)
    scenes = story.get("scenes", [])
    if not scenes:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="剧本尚未生成，请先调用 generate-script")

    lines = []
    for ep in scenes:
        lines.append(f"# 第{ep['episode']}集 {ep['title']}")
        for s in ep.get("scenes", []):
            lines.append(f"\n## 场景{s['scene_number']}")
            lines.append(f"【环境】{s['environment']}")
            lines.append(f"【画面】{s['visual']}")
            for a in s.get("audio", []):
                lines.append(f"【{a['character']}】{a['line']}")

    script_text = "\n".join(lines)
    return {"story_id": story_id, "script": script_text}
