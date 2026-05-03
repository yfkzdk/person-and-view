"""
角色管理API - 提供RESTful接口管理角色卡片

功能：
- 创建/读取/更新/删除角色
- 导入/导出角色卡片
- 切换当前角色
- 角色蒸馏（从对话样本学习）
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os

from src.models.character_card import CharacterCard, CharacterCardManager
from src.utils.person_distiller import PersonDistiller


# 创建路由器
router = APIRouter(prefix="/api/characters", tags=["characters"])

# 全局角色管理器
character_manager = CharacterCardManager(cards_dir="characters")
character_manager.create_default_characters()


# ============ 数据模型 ============

class CharacterCreateRequest(BaseModel):
    """创建角色请求"""
    name: str
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""
    system_prompt: str = ""
    tags: List[str] = []
    custom_fields: Dict = {}


class CharacterUpdateRequest(BaseModel):
    """更新角色请求"""
    description: Optional[str] = None
    personality: Optional[str] = None
    scenario: Optional[str] = None
    first_mes: Optional[str] = None
    mes_example: Optional[str] = None
    system_prompt: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict] = None


class DistillRequest(BaseModel):
    """蒸馏请求"""
    name: str
    role: str
    dialogues: List[Dict[str, str]]  # [{"user_input": "...", "response": "..."}, ...]
    background: str = ""


class CharacterResponse(BaseModel):
    """角色响应"""
    name: str
    description: str
    personality: str
    scenario: str
    first_mes: str
    tags: List[str]
    system_prompt_preview: str  # 前200字符


# ============ API端点 ============

@router.get("/", response_model=List[str])
async def list_characters():
    """列出所有角色"""
    return character_manager.list_cards()


@router.get("/{name}", response_model=CharacterResponse)
async def get_character(name: str):
    """获取角色详情"""
    card = character_manager.get_card(name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    return CharacterResponse(
        name=card.name,
        description=card.description,
        personality=card.personality,
        scenario=card.scenario,
        first_mes=card.first_mes,
        tags=card.tags,
        system_prompt_preview=card.to_system_prompt()[:200] + "..."
    )


@router.post("/", response_model=CharacterResponse)
async def create_character(request: CharacterCreateRequest):
    """创建新角色"""
    # 检查是否已存在
    if character_manager.get_card(request.name):
        raise HTTPException(status_code=400, detail=f"Character '{request.name}' already exists")

    # 创建角色
    card = character_manager.create_card(
        name=request.name,
        description=request.description,
        personality=request.personality,
        scenario=request.scenario,
        first_mes=request.first_mes,
        mes_example=request.mes_example,
        system_prompt=request.system_prompt,
        tags=request.tags,
        custom_fields=request.custom_fields
    )

    # 保存
    character_manager.save_card(request.name)

    return CharacterResponse(
        name=card.name,
        description=card.description,
        personality=card.personality,
        scenario=card.scenario,
        first_mes=card.first_mes,
        tags=card.tags,
        system_prompt_preview=card.to_system_prompt()[:200] + "..."
    )


@router.put("/{name}", response_model=CharacterResponse)
async def update_character(name: str, request: CharacterUpdateRequest):
    """更新角色"""
    card = character_manager.get_card(name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    # 更新字段
    if request.description is not None:
        card.description = request.description
    if request.personality is not None:
        card.personality = request.personality
    if request.scenario is not None:
        card.scenario = request.scenario
    if request.first_mes is not None:
        card.first_mes = request.first_mes
    if request.mes_example is not None:
        card.mes_example = request.mes_example
    if request.system_prompt is not None:
        card.system_prompt = request.system_prompt
    if request.tags is not None:
        card.tags = request.tags
    if request.custom_fields is not None:
        card.custom_fields = request.custom_fields

    # 保存
    character_manager.save_card(name)

    return CharacterResponse(
        name=card.name,
        description=card.description,
        personality=card.personality,
        scenario=card.scenario,
        first_mes=card.first_mes,
        tags=card.tags,
        system_prompt_preview=card.to_system_prompt()[:200] + "..."
    )


@router.delete("/{name}")
async def delete_character(name: str):
    """删除角色"""
    if name not in character_manager.cards:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    del character_manager.cards[name]

    # 删除文件
    filepath = f"characters/{name}.json"
    if os.path.exists(filepath):
        os.remove(filepath)

    return {"message": f"Character '{name}' deleted"}


@router.post("/{name}/activate")
async def activate_character(name: str):
    """激活角色（设置为当前使用的角色）"""
    success = character_manager.set_active_card(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    return {"message": f"Character '{name}' activated", "active_character": name}


@router.get("/active/current")
async def get_active_character():
    """获取当前激活的角色"""
    if not character_manager.active_card:
        return {"active_character": None}

    return {
        "active_character": character_manager.active_card.name,
        "system_prompt_preview": character_manager.active_card.to_system_prompt()[:200] + "..."
    }


@router.post("/export/{name}")
async def export_character(name: str):
    """导出角色卡片为JSON"""
    card = character_manager.get_card(name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    return card.to_sillytavern_format()


@router.post("/import")
async def import_character(file: UploadFile = File(...)):
    """从JSON文件导入角色卡片"""
    try:
        content = await file.read()
        data = json.loads(content)

        card = CharacterCard.from_sillytavern_format(data)
        character_manager.cards[card.name] = card
        character_manager.save_card(card.name)

        return {
            "message": f"Character '{card.name}' imported successfully",
            "name": card.name
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import character: {str(e)}")


@router.post("/distill", response_model=CharacterResponse)
async def distill_character(request: DistillRequest):
    """
    从对话样本蒸馏角色特征

    输入对话样本，自动提取性格、说话风格等特征
    """
    try:
        # 准备对话数据
        dialogues = [
            (d["user_input"], d["response"])
            for d in request.dialogues
        ]

        # 蒸馏
        distiller = PersonDistiller()
        profile = distiller.distill_from_dialogues(
            name=request.name,
            role=request.role,
            dialogues=dialogues,
            background=request.background
        )

        # 转换为角色卡片
        card = character_manager.create_card(
            name=profile.name,
            description=profile.background,
            personality=", ".join([t.value for t in profile.personality_traits]),
            scenario="",
            first_mes="",
            mes_example="\n\n".join([
                f"{{{{user}}}}: {ex.user_input}\n{{{{char}}}}: {ex.response}"
                for ex in profile.example_dialogues[:3]
            ]),
            system_prompt=profile.to_system_prompt(),
            tags=[request.role],
            custom_fields={
                "emotional_responses": profile.emotional_responses,
                "expertise_areas": profile.expertise_areas,
                "speaking_style": profile.speaking_style.value if hasattr(profile.speaking_style, 'value') else str(profile.speaking_style),
                "catchphrases": profile.catchphrases
            }
        )

        # 保存
        character_manager.save_card(card.name)

        return CharacterResponse(
            name=card.name,
            description=card.description,
            personality=card.personality,
            scenario=card.scenario,
            first_mes=card.first_mes,
            tags=card.tags,
            system_prompt_preview=card.to_system_prompt()[:200] + "..."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Distillation failed: {str(e)}")


@router.get("/{name}/system-prompt")
async def get_system_prompt(name: str):
    """获取角色的完整系统提示词"""
    card = character_manager.get_card(name)
    if not card:
        raise HTTPException(status_code=404, detail=f"Character '{name}' not found")

    return {
        "name": name,
        "system_prompt": card.to_system_prompt()
    }


# ============ 集成到主应用 ============

def setup_character_routes(app):
    """
    将角色管理路由集成到FastAPI应用

    Args:
        app: FastAPI应用实例
    """
    app.include_router(router)


# 使用示例
if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI(title="Character Management API")
    setup_character_routes(app)

    print("=" * 80)
    print("角色管理API")
    print("=" * 80)
    print("\n可用端点：")
    print("  GET    /api/characters/              列出所有角色")
    print("  GET    /api/characters/{name}        获取角色详情")
    print("  POST   /api/characters/              创建新角色")
    print("  PUT    /api/characters/{name}        更新角色")
    print("  DELETE /api/characters/{name}        删除角色")
    print("  POST   /api/characters/{name}/activate  激活角色")
    print("  POST   /api/characters/distill       从对话蒸馏角色")
    print("  POST   /api/characters/import        导入角色卡片")
    print("  POST   /api/characters/export/{name} 导出角色卡片")
    print("\n启动服务器: http://localhost:8000")
    print("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=8000)
