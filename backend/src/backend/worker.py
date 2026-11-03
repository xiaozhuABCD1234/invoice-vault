"""独立 worker 进程：轮询 extraction_jobs 表并处理任务。

用法：

    python -m backend.worker             循环处理
    python -m backend.worker --once      只处理一轮后退出（测试/运维用）

单机不引入 Redis：一次处理 1 个任务；启动时把超时 running 改回 queued。
"""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .app_settings.service import effective_extraction_config
from .extraction.config import ExtractionConfig
from .extraction.service import QUEUED, RUNNING, process_job
from .models.extraction import ExtractionJob
from .shared.config import Settings, get_settings
from .shared.db import create_engine_for, get_session_factory, init_db, utcnow

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 5.0


def reset_stale_running(db: Session, *, stale_minutes: int) -> int:
    """启动时把超时的 running 任务改回 queued，返回修改条数。"""

    minutes = max(int(stale_minutes or 0), 1)
    threshold = utcnow() - timedelta(minutes=minutes)
    jobs = list(
        db.scalars(
            select(ExtractionJob).where(
                ExtractionJob.status == RUNNING,
                or_(
                    ExtractionJob.started_at.is_(None),
                    ExtractionJob.started_at < threshold,
                ),
            )
        ).all()
    )
    now = utcnow()
    for job in jobs:
        job.status = QUEUED
        job.queued_at = now
        job.started_at = None
        job.finished_at = None
        if not job.error_code:
            job.error_code = "worker_recovered"
            job.error_message = "worker 启动时发现任务超时，已重新排队"
    if jobs:
        db.commit()
    return len(jobs)


def next_job(db: Session) -> ExtractionJob | None:
    """取一个到期的 queued 任务（一次只处理 1 个）。"""

    return db.scalar(
        select(ExtractionJob)
        .where(
            ExtractionJob.status == QUEUED,
            ExtractionJob.queued_at <= utcnow(),
        )
        .order_by(ExtractionJob.queued_at.asc(), ExtractionJob.id.asc())
        .limit(1)
    )


def run_once(
    db: Session,
    *,
    settings: Settings,
    config: ExtractionConfig | None = None,
) -> ExtractionJob | None:
    """处理一轮：取 1 个到期任务并执行；没有任务时返回 None。"""

    cfg = config or effective_extraction_config(db, settings)
    job = next_job(db)
    if job is None:
        return None
    return process_job(db, job.id, settings=settings, config=cfg)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend.worker", description="发票识别任务 worker")
    parser.add_argument("--once", action="store_true", help="只处理一轮后退出")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="空闲轮询间隔（秒），默认 5",
    )
    parser.add_argument("--database-url", default=None, help="覆盖数据库连接串")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    config: ExtractionConfig | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    current: Any = settings or get_settings()
    if args.database_url:
        current = current.model_copy(update={"database_url": args.database_url})
    engine = create_engine_for(current.database_url, echo=current.sql_echo)
    init_db(engine, current)
    factory = get_session_factory(engine)
    with factory() as db:
        startup_config = config or effective_extraction_config(db, current)
    try:
        with factory() as db:
            recovered = reset_stale_running(
                db, stale_minutes=startup_config.stale_minutes
            )
        if recovered:
            logger.info("已将 %s 个超时 running 任务改回 queued", recovered)

        if args.once:
            with factory() as db:
                job = run_once(db, settings=current, config=config)
            if job is None:
                logger.info("--once：没有待处理任务")
            else:
                logger.info("--once：任务 %s 处理完成，状态 %s", job.id, job.status)
            return 0

        logger.info(
            "worker 启动：provider=%s，interval=%ss",
            startup_config.provider,
            args.interval,
        )
        while True:
            try:
                # 每轮重新读取配置，管理端改动对下一个任务生效
                with factory() as db:
                    job = run_once(db, settings=current, config=config)
                if job is not None:
                    logger.info("任务 %s 处理完成：%s", job.id, job.status)
                else:
                    time.sleep(max(args.interval, 0.1))
            except KeyboardInterrupt:
                logger.info("worker 收到中断，退出")
                return 0
            except Exception:  # pragma: no cover - 长期运行兜底
                logger.exception("worker 轮询异常")
                time.sleep(max(args.interval, 0.1))
    finally:
        engine.dispose()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
