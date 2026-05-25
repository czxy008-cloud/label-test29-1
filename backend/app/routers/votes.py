"""
投票相关API路由
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.schemas import VoteSubmit, VoteStatisticsResponse
from app.models import Survey, Question, Option, Vote, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/votes", tags=["投票"])


def get_voter_session(request: Request) -> str:
    """
    获取或创建投票者会话ID
    用于匿名投票去重
    """
    session_id = request.cookies.get("voter_session")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_vote(
    vote_data: VoteSubmit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = None
):
    """
    提交投票
    支持匿名投票（通过会话ID去重）
    """
    # 获取问卷
    survey = db.query(Survey).filter(Survey.id == vote_data.survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if not survey.is_active:
        raise HTTPException(status_code=400, detail="问卷已关闭")

    # 检查是否过期
    if survey.expire_at and survey.expire_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="问卷已过期")

    # 获取或创建投票者会话
    voter_session = get_voter_session(request)

    # 检查是否已投票（同一问卷同一会话只能投一次）
    existing_vote = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.voter_session == voter_session
    ).first()

    if existing_vote:
        raise HTTPException(status_code=400, detail="您已对此问卷投票")

    # 获取问卷的所有问题
    questions = db.query(Question).filter(Question.survey_id == survey.id).all()
    question_map = {q.id: q for q in questions}

    # 验证并保存投票
    for vote_item in vote_data.votes:
        question = question_map.get(vote_item.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"问题ID {vote_item.question_id} 不存在"
            )

        # 验证必填问题
        if question.is_required:
            if question.question_type in ("single_choice", "multiple_choice"):
                if not vote_item.option_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"问题 '{question.question_text}' 为必答题"
                    )
            elif question.question_type == "text_input":
                if not vote_item.text_value or not vote_item.text_value.strip():
                    raise HTTPException(
                        status_code=400,
                        detail=f"问题 '{question.question_text}' 为必答题"
                    )

        # 保存投票
        if question.question_type in ("single_choice", "multiple_choice"):
            # 选择题
            if vote_item.option_ids:
                for option_id in vote_item.option_ids:
                    # 验证选项属于该问题
                    option = db.query(Option).filter(
                        Option.id == option_id,
                        Option.question_id == question.id
                    ).first()
                    if not option:
                        raise HTTPException(
                            status_code=400,
                            detail=f"选项ID {option_id} 不属于该问题"
                        )

                    vote = Vote(
                        survey_id=survey.id,
                        question_id=question.id,
                        option_id=option.id,
                        voter_session=voter_session,
                        voter_id=current_user.id if current_user else None,
                    )
                    db.add(vote)
        else:
            # 填空题
            if vote_item.text_value is not None:
                vote = Vote(
                    survey_id=survey.id,
                    question_id=question.id,
                    text_value=vote_item.text_value.strip() if vote_item.text_value else "",
                    voter_session=voter_session,
                    voter_id=current_user.id if current_user else None,
                )
                db.add(vote)

    db.commit()

    return {"message": "投票成功", "voter_session": voter_session}


@router.get("/survey/{survey_id}/statistics", response_model=VoteStatisticsResponse)
async def get_vote_statistics(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取问卷投票统计数据
    """
    # 获取问卷
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据")

    # 获取所有问题
    questions = db.query(Question).filter(
        Question.survey_id == survey.id
    ).order_by(Question.sort_order).all()

    # 计算唯一投票者数量
    unique_voters = db.query(Vote.voter_session).filter(
        Vote.survey_id == survey.id
    ).distinct().count()

    # 构建统计数据
    statistics = {
        "survey_id": survey.id,
        "survey_title": survey.title,
        "total_voters": unique_voters,
        "questions": []
    }

    for question in questions:
        question_stats = {
            "id": question.id,
            "text": question.question_text,
            "type": question.question_type,
            "is_required": question.is_required,
        }

        if question.question_type in ("single_choice", "multiple_choice"):
            # 选择题统计
            options = db.query(Option).filter(
                Option.question_id == question.id
            ).order_by(Option.sort_order).all()

            option_stats = []
            for option in options:
                vote_count = db.query(Vote).filter(
                    Vote.question_id == question.id,
                    Vote.option_id == option.id
                ).count()

                percentage = round((vote_count / unique_voters * 100), 1) if unique_voters > 0 else 0

                option_stats.append({
                    "id": option.id,
                    "text": option.option_text,
                    "count": vote_count,
                    "percentage": percentage,
                })

            question_stats["options"] = option_stats

            # 计算该问题的总票数
            question_stats["total_votes"] = sum(opt["count"] for opt in option_stats)

        else:
            # 填空题统计
            text_votes = db.query(Vote).filter(
                Vote.question_id == question.id,
                Vote.text_value.isnot(None),
                Vote.text_value != ""
            ).all()

            question_stats["answers"] = [
                {"id": v.id, "text": v.text_value, "voted_at": v.voted_at.isoformat() if v.voted_at else None}
                for v in text_votes
            ]
            question_stats["total_answers"] = len(text_votes)

        statistics["questions"].append(question_stats)

    return VoteStatisticsResponse(
        survey_id=survey.id,
        total_voters=unique_voters,
        statistics=statistics,
    )


@router.get("/survey/{survey_id}/export")
async def export_votes_csv(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出问卷投票数据为CSV格式
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    # 获取问卷
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    # 检查权限
    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权导出此数据")

    # 获取所有问题
    questions = db.query(Question).filter(
        Question.survey_id == survey.id
    ).order_by(Question.sort_order).all()

    # 获取所有投票数据
    votes = db.query(Vote).filter(Vote.survey_id == survey.id).all()

    # 按会话分组投票
    session_votes = defaultdict(dict)
    for vote in votes:
        key = f"q_{vote.question_id}"
        if vote.option_id:
            option = db.query(Option).filter(Option.id == vote.option_id).first()
            session_votes[vote.voter_session][key] = option.option_text if option else ""
        elif vote.text_value is not None:
            session_votes[vote.voter_session][key] = vote.text_value

    # 生成CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    header = ["投票时间", "会话ID"]
    for q in questions:
        header.append(f"Q{q.sort_order + 1}: {q.question_text[:30]}...")
    writer.writerow(header)

    # 写入数据
    for session_id, vote_data in session_votes.items():
        # 获取该会话的第一个投票时间
        first_vote = db.query(Vote).filter(
            Vote.survey_id == survey.id,
            Vote.voter_session == session_id
        ).order_by(Vote.voted_at).first()

        row = [
            first_vote.voted_at.isoformat() if first_vote and first_vote.voted_at else "",
            session_id,
        ]
        for q in questions:
            key = f"q_{q.id}"
            row.append(vote_data.get(key, ""))
        writer.writerow(row)

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=survey_{survey_id}_votes.csv"
        }
    )
