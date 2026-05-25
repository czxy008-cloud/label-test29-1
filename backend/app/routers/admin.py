"""
管理员相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas import UserResponse, SurveyResponse
from app.models import User, Survey, Vote
from app.auth import require_admin, get_current_user

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户列表（管理员权限）
    """
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户详情（管理员权限）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    删除用户（管理员权限）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不允许删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db.delete(user)
    db.commit()


@router.get("/surveys", response_model=List[SurveyResponse])
async def list_all_surveys(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取所有问卷列表（管理员权限）
    """
    surveys = db.query(Survey).order_by(Survey.created_at.desc()).offset(skip).limit(limit).all()
    return surveys


@router.get("/statistics/summary")
async def get_system_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取系统统计摘要（管理员权限）
    """
    total_users = db.query(User).count()
    total_surveys = db.query(Survey).count()
    total_votes = db.query(Vote).count()
    active_surveys = db.query(Survey).filter(Survey.is_active == True).count()

    return {
        "total_users": total_users,
        "total_surveys": total_surveys,
        "active_surveys": active_surveys,
        "total_votes": total_votes,
    }
