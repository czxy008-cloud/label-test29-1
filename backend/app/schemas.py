"""
Pydantic Schema 定义
定义API请求和响应的数据验证模型
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


# =====================================================================
# 用户相关 Schema
# =====================================================================

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")


class UserCreate(UserBase):
    """用户注册请求"""
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    """用户响应"""
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户信息更新"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None


class Token(BaseModel):
    """JWT令牌响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT令牌数据"""
    user_id: Optional[int] = None
    username: Optional[str] = None


# =====================================================================
# 问卷相关 Schema
# =====================================================================

class OptionCreate(BaseModel):
    """选项创建"""
    option_text: str = Field(..., min_length=1, max_length=500, description="选项文本")
    sort_order: int = Field(default=0, description="排序序号")


class OptionResponse(BaseModel):
    """选项响应"""
    id: int
    option_text: str
    sort_order: int

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    """问题创建"""
    question_text: str = Field(..., min_length=1, max_length=500, description="问题文本")
    question_type: str = Field(..., description="问题类型: single_choice/multiple_choice/text_input")
    is_required: bool = Field(default=True, description="是否必答")
    sort_order: int = Field(default=0, description="排序序号")
    options: Optional[List[OptionCreate]] = Field(default=None, description="选项列表（选择题必填）")


class QuestionResponse(BaseModel):
    """问题响应"""
    id: int
    question_text: str
    question_type: str
    is_required: bool
    sort_order: int
    options: List[OptionResponse] = []

    class Config:
        from_attributes = True


class SurveyCreate(BaseModel):
    """问卷创建请求"""
    title: str = Field(..., min_length=1, max_length=200, description="问卷标题")
    description: Optional[str] = Field(None, description="问卷描述")
    expire_at: Optional[datetime] = Field(None, description="过期时间")
    questions: List[QuestionCreate] = Field(..., min_length=1, description="问题列表")


class SurveyUpdate(BaseModel):
    """问卷更新请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expire_at: Optional[datetime] = None


class SurveyResponse(BaseModel):
    """问卷响应"""
    id: int
    title: str
    description: Optional[str]
    is_active: bool
    share_token: str
    expire_at: Optional[datetime]
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SurveyDetailResponse(SurveyResponse):
    """问卷详情响应（包含问题和选项）"""
    questions: List[QuestionResponse] = []


class SurveyListResponse(BaseModel):
    """问卷列表响应"""
    surveys: List[SurveyResponse]
    total: int


# =====================================================================
# 投票相关 Schema
# =====================================================================

class VoteItem(BaseModel):
    """单项投票数据"""
    question_id: int = Field(..., description="问题ID")
    option_ids: Optional[List[int]] = Field(default=None, description="选中的选项ID列表（选择题）")
    text_value: Optional[str] = Field(default=None, description="填空文本（填空题）")


class VoteSubmit(BaseModel):
    """投票提交请求"""
    survey_id: int = Field(..., description="问卷ID")
    votes: List[VoteItem] = Field(..., min_length=1, description="投票数据列表")


class VoteStatisticsResponse(BaseModel):
    """投票统计响应"""
    survey_id: int
    total_voters: int
    statistics: dict  # 包含各问题的统计数据


class DraftVoteItem(BaseModel):
    """草稿中的单项投票数据"""
    question_id: int
    question_type: str = Field(..., description="问题类型")
    option_ids: Optional[List[int]] = None
    text_value: Optional[str] = None


class DraftResponse(BaseModel):
    """草稿响应"""
    survey_id: int
    updated_at: Optional[datetime] = None
    votes: List[DraftVoteItem]


# =====================================================================
# 分享链接 Schema
# =====================================================================

class ShareLinkResponse(BaseModel):
    """分享链接响应"""
    survey_id: int
    share_token: str
    share_url: str
