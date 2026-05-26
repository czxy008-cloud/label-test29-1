"""
投票相关API路由
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.orm import Session
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.schemas import (
    VoteSubmit, VoteStatisticsResponse, DraftResponse, DraftVoteItem
)
from app.models import Survey, Question, Option, Vote, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/votes", tags=["投票"])


async def get_optional_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    可选用户依赖：若请求携带 Authorization: Bearer <token> 则尝试解析登录用户，
    否则返回 None。用于支持匿名投票与登录用户草稿的统一处理。
    """
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except Exception:
        return None


def get_voter_session(request: Request) -> str:
    """
    获取或创建投票者会话ID
    用于匿名投票去重
    """
    session_id = request.cookies.get("voter_session")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


def _attach_session_cookie(response: Response, session_id: str):
    """将投票者会话写入响应 cookie（若请求中不存在则设置）"""
    response.set_cookie(
        key="voter_session",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,
    )


def _get_submitted_vote_filter():
    """已提交投票的过滤条件（兼容老数据 status 为 NULL 的场景）"""
    from sqlalchemy import or_
    return or_(Vote.status == "submitted", Vote.status.is_(None))


def _build_vote_records(
    db: Session,
    survey: Survey,
    vote_data: VoteSubmit,
    voter_session: str,
    current_user: Optional[User],
    status_value: str = "submitted",
):
    """
    构建投票记录（共享逻辑）。
    对提交（submitted）执行必填校验；对草稿（draft）允许部分填写。
    返回生成的 Vote 对象列表（未提交事务）。
    """
    questions = db.query(Question).filter(Question.survey_id == survey.id).all()
    question_map = {q.id: q for q in questions}
    option_cache: dict = {}

    records: list = []

    for vote_item in vote_data.votes:
        question = question_map.get(vote_item.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"问题ID {vote_item.question_id} 不存在"
            )

        # 只有提交时才校验必填
        if status_value == "submitted" and question.is_required:
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

        if question.question_type in ("single_choice", "multiple_choice"):
            if vote_item.option_ids:
                for option_id in vote_item.option_ids:
                    cache_key = (option_id, question.id)
                    if cache_key not in option_cache:
                        option_cache[cache_key] = db.query(Option).filter(
                            Option.id == option_id,
                            Option.question_id == question.id
                        ).first()
                    option = option_cache[cache_key]
                    if not option:
                        raise HTTPException(
                            status_code=400,
                            detail=f"选项ID {option_id} 不属于该问题"
                        )
                    records.append(Vote(
                        survey_id=survey.id,
                        question_id=question.id,
                        option_id=option.id,
                        voter_session=voter_session,
                        voter_id=current_user.id if current_user else None,
                        status=status_value,
                    ))
        else:
            if vote_item.text_value is not None:
                records.append(Vote(
                    survey_id=survey.id,
                    question_id=question.id,
                    text_value=vote_item.text_value.strip() if vote_item.text_value else "",
                    voter_session=voter_session,
                    voter_id=current_user.id if current_user else None,
                    status=status_value,
                ))

    return records


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_vote(
    vote_data: VoteSubmit,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    提交投票
    支持匿名投票（通过会话ID去重）
    若存在同一会话的草稿，将草稿转换为已提交状态（覆盖）
    """
    survey = db.query(Survey).filter(Survey.id == vote_data.survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if not survey.is_active:
        raise HTTPException(status_code=400, detail="问卷已关闭")

    if survey.expire_at and survey.expire_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="问卷已过期")

    voter_session = get_voter_session(request)
    _attach_session_cookie(response, voter_session)

    # 检查是否已提交（忽略草稿）
    existing_submitted = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.voter_session == voter_session,
        _get_submitted_vote_filter(),
    ).first()
    if existing_submitted:
        raise HTTPException(status_code=400, detail="您已对此问卷投票")

    # 删除已有草稿记录
    db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.voter_session == voter_session,
        Vote.status == "draft",
    ).delete(synchronize_session=False)

    records = _build_vote_records(
        db, survey, vote_data, voter_session, current_user,
        status_value="submitted",
    )
    for r in records:
        db.add(r)

    db.commit()

    return {"message": "投票成功", "voter_session": voter_session}


# =====================================================================
# 草稿相关接口
# =====================================================================


@router.post("/draft", status_code=status.HTTP_200_OK)
async def save_draft(
    vote_data: VoteSubmit,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    保存问卷填写草稿。
    同一 survey_id 与 voter_session 下仅保留一份草稿（覆盖式保存）。
    """
    survey = db.query(Survey).filter(Survey.id == vote_data.survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if survey.expire_at and survey.expire_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="问卷已过期")

    # 已提交的问卷不再接受草稿
    voter_session = get_voter_session(request)
    _attach_session_cookie(response, voter_session)

    existing_submitted = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.voter_session == voter_session,
        _get_submitted_vote_filter(),
    ).first()
    if existing_submitted:
        raise HTTPException(status_code=400, detail="您已对此问卷投票，无法保存草稿")

    # 清除旧草稿
    db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.voter_session == voter_session,
        Vote.status == "draft",
    ).delete(synchronize_session=False)

    records = _build_vote_records(
        db, survey, vote_data, voter_session, current_user,
        status_value="draft",
    )
    for r in records:
        db.add(r)

    db.commit()

    return {"message": "草稿已保存", "voter_session": voter_session}


@router.get("/draft/survey/{survey_id}", response_model=DraftResponse)
async def get_draft(
    survey_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    获取当前用户/会话对指定问卷的草稿。
    优先使用登录用户身份；否则使用 cookie 中的 voter_session。
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    session_id = request.cookies.get("voter_session")

    draft_query = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.status == "draft",
    )
    if current_user is not None:
        draft_query = draft_query.filter(Vote.voter_id == current_user.id)
    elif session_id:
        draft_query = draft_query.filter(Vote.voter_session == session_id)
    else:
        return DraftResponse(survey_id=survey.id, updated_at=None, votes=[])

    draft_votes = draft_query.all()
    if not draft_votes:
        return DraftResponse(survey_id=survey.id, updated_at=None, votes=[])

    # 加载问题类型以便返回给前端
    question_ids = list({v.question_id for v in draft_votes})
    questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
    q_type_map = {q.id: q.question_type for q in questions}

    # 按问题聚合（多选题会有多条记录）
    grouped: dict = defaultdict(lambda: {"option_ids": [], "text_value": None})
    for v in draft_votes:
        bucket = grouped[v.question_id]
        if v.option_id is not None:
            bucket["option_ids"].append(v.option_id)
        if v.text_value is not None:
            bucket["text_value"] = v.text_value

    updated_at = max((v.voted_at for v in draft_votes if v.voted_at), default=None)

    result_votes = []
    for qid, data in grouped.items():
        result_votes.append(DraftVoteItem(
            question_id=qid,
            question_type=q_type_map.get(qid, "text_input"),
            option_ids=data["option_ids"] or None,
            text_value=data["text_value"],
        ))

    return DraftResponse(
        survey_id=survey.id,
        updated_at=updated_at,
        votes=result_votes,
    )


@router.delete("/draft/survey/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    survey_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    删除当前用户/会话对指定问卷的草稿。
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    session_id = request.cookies.get("voter_session")

    draft_query = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        Vote.status == "draft",
    )
    if current_user is not None:
        draft_query = draft_query.filter(Vote.voter_id == current_user.id)
    elif session_id:
        draft_query = draft_query.filter(Vote.voter_session == session_id)
    else:
        return Response(status_code=204)

    draft_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)


# =====================================================================
# 统计与导出
# =====================================================================


@router.get("/survey/{survey_id}/statistics", response_model=VoteStatisticsResponse)
async def get_vote_statistics(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取问卷投票统计数据（仅统计已提交的投票）
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此数据")

    questions = db.query(Question).filter(
        Question.survey_id == survey.id
    ).order_by(Question.sort_order).all()

    submitted_filter = _get_submitted_vote_filter()

    unique_voters = db.query(Vote.voter_session).filter(
        Vote.survey_id == survey.id,
        submitted_filter,
    ).distinct().count()

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
            options = db.query(Option).filter(
                Option.question_id == question.id
            ).order_by(Option.sort_order).all()

            option_stats = []
            for option in options:
                vote_count = db.query(Vote).filter(
                    Vote.question_id == question.id,
                    Vote.option_id == option.id,
                    submitted_filter,
                ).count()

                percentage = round((vote_count / unique_voters * 100), 1) if unique_voters > 0 else 0

                option_stats.append({
                    "id": option.id,
                    "text": option.option_text,
                    "count": vote_count,
                    "percentage": percentage,
                })

            question_stats["options"] = option_stats
            question_stats["total_votes"] = sum(opt["count"] for opt in option_stats)
        else:
            text_votes = db.query(Vote).filter(
                Vote.question_id == question.id,
                Vote.text_value.isnot(None),
                Vote.text_value != "",
                submitted_filter,
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
    导出问卷投票数据为CSV格式（仅导出已提交的投票）
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")

    if survey.creator_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权导出此数据")

    questions = db.query(Question).filter(
        Question.survey_id == survey.id
    ).order_by(Question.sort_order).all()

    submitted_filter = _get_submitted_vote_filter()

    votes = db.query(Vote).filter(
        Vote.survey_id == survey.id,
        submitted_filter,
    ).all()

    session_votes = defaultdict(dict)
    for vote in votes:
        key = f"q_{vote.question_id}"
        if vote.option_id:
            option = db.query(Option).filter(Option.id == vote.option_id).first()
            session_votes[vote.voter_session][key] = option.option_text if option else ""
        elif vote.text_value is not None:
            session_votes[vote.voter_session][key] = vote.text_value

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["投票时间", "会话ID"]
    for q in questions:
        header.append(f"Q{q.sort_order + 1}: {q.question_text[:30]}...")
    writer.writerow(header)

    for session_id, vote_data in session_votes.items():
        first_vote = db.query(Vote).filter(
            Vote.survey_id == survey.id,
            Vote.voter_session == session_id,
            submitted_filter,
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
