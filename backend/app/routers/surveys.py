"""
问卷相关API路由
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas import (
    SurveyCreate, SurveyUpdate, SurveyResponse,
    SurveyDetailResponse, SurveyListResponse, ShareLinkResponse
)
from app.models import Survey, Question, Option, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/surveys", tags=["问卷"])


def generate_share_token() -> str:
    """生成唯一的分享令牌"""
    return secrets.token_urlsafe(32)


@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(
    survey_data: SurveyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建问卷
    """
    # 生成分享令牌
    share_token = generate_share_token()

    # 确保令牌唯一
    while db.query(Survey).filter(Survey.share_token == share_token).first():
        share_token = generate_share_token()

    # 创建问卷
    survey = Survey(
        title=survey_data.title,
        description=survey_data.description,
        creator_id=current_user.id,
        share_token=share_token,
        expire_at=survey_data.expire_at,
    )
    db.add(survey)
    db.flush()

    # 创建问题
    for q_data in survey_data.questions:
        question = Question(
            survey_id=survey.id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            is_required=q_data.is_required,
            sort_order=q_data.sort_order,
        )
        db.add(question)
        db.flush()

        # 创建选项（选择题需要选项）
        if q_data.options and q_data.question_type in ("single_choice", "multiple_choice"):
            for opt_data in q_data.options:
                option = Option(
                    question_id=question.id,
                    option_text=opt_data.option_text,
                    sort_order=opt_data.sort_order,
                )
                db.add(option)

    db.commit()
    db.refresh(survey)

    return survey


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取问卷列表
    """
    query = db.query(Survey).filter(Survey.creator_id == current_user.id)

    if is_active is not None:
        query = query.filter(Survey.is_active == is_active)

    total = query.count()
    surveys = query.order_by(Survey.created_at.desc()).offset(skip).limit(limit).all()

    return SurveyListResponse(surveys=surveys, total=total)


@router.get("/{survey_id}", response_model=SurveyDetailResponse)
async def get_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取问卷详情
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限（只有创建者或管理员可以查看）
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此问卷")

    return survey


@router.get("/share/{share_token}", response_model=SurveyDetailResponse)
async def get_survey_by_share_token(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    通过分享令牌获取问卷（公开访问）
    """
    survey = db.query(Survey).filter(Survey.share_token == share_token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if not survey.is_active:
        raise HTTPException(status_code=400, detail="问卷已关闭")

    # 检查是否过期
    from datetime import datetime, timezone
    if survey.expire_at and survey.expire_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="问卷已过期")

    return survey


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: int,
    survey_data: SurveyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新问卷
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权修改此问卷")

    # 更新字段
    if survey_data.title is not None:
        survey.title = survey_data.title
    if survey_data.description is not None:
        survey.description = survey_data.description
    if survey_data.is_active is not None:
        survey.is_active = survey_data.is_active
    if survey_data.expire_at is not None:
        survey.expire_at = survey_data.expire_at

    db.commit()
    db.refresh(survey)

    return survey


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除问卷
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权删除此问卷")

    db.delete(survey)
    db.commit()


@router.get("/{survey_id}/share", response_model=ShareLinkResponse)
async def get_share_link(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取问卷分享链接
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此问卷")

    share_url = f"/survey/{survey.share_token}"

    return ShareLinkResponse(
        survey_id=survey.id,
        share_token=survey.share_token,
        share_url=share_url,
    )
