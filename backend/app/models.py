"""
SQLAlchemy ORM 模型定义
定义系统所需的所有数据库表结构
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """用户模型 - 存储系统注册用户信息"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    surveys = relationship("Survey", back_populates="creator", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="voter")


class Survey(Base):
    """问卷模型 - 存储调查问卷的基本信息"""

    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    share_token = Column(String(64), unique=True, nullable=False, index=True)
    expire_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    creator = relationship("User", back_populates="surveys")
    questions = relationship("Question", back_populates="survey", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="survey", cascade="all, delete-orphan")


class Question(Base):
    """问题模型 - 存储问卷中的问题信息"""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(String(500), nullable=False)
    question_type = Column(String(20), nullable=False)  # single_choice, multiple_choice, text_input
    is_required = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 约束：问题类型必须是指定的值
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('single_choice', 'multiple_choice', 'text_input')",
            name="chk_question_type"
        ),
    )

    # 关联关系
    survey = relationship("Survey", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="question", cascade="all, delete-orphan")


class Option(Base):
    """选项模型 - 存储单选题和多选题的选项内容"""

    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_text = Column(String(500), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    question = relationship("Question", back_populates="options")
    votes = relationship("Vote", back_populates="option")


class Vote(Base):
    """投票模型 - 存储用户的投票记录"""

    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_id = Column(Integer, ForeignKey("options.id", ondelete="CASCADE"), nullable=True, index=True)
    text_value = Column(Text, nullable=True)
    voter_session = Column(String(100), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="submitted", server_default="submitted", index=True)
    voted_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted')",
            name="chk_vote_status"
        ),
    )

    # 关联关系
    survey = relationship("Survey", back_populates="votes")
    question = relationship("Question", back_populates="votes")
    option = relationship("Option", back_populates="votes")
    voter = relationship("User", back_populates="votes")
