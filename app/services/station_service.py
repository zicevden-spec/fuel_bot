from datetime import datetime
from sqlalchemy import select
from app.database.base import async_session
from app.database.models import Report, Station


AVAILABILITY_EMOJI = {"available": "✅", "low": "⚠️", "unavailable": "❌"}
QUEUE_EMOJI = {"none": "🟢", "small": "🟡", "medium": "🟠", "critical": "🔴"}
AVAILABILITY_TEXT = {"available": "В наличии", "low": "Заканчивается", "unavailable": "Нет"}
QUEUE_TEXT = {"none": "очереди нет", "small": "маленькая очередь", "medium": "средняя очередь", "critical": "огромная очередь"}
STATUS_RANK = {"unavailable": 0, "low": 1, "available": 2}


async def get_last_reports(station_id: int) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(Report)
            .where(
                Report.station_id == station_id,
                Report.moderation_status == "approved"  # Показываем только подтверждённые отчёты
            )
            .order_by(Report.created_at.desc())
        )
        reports = result.scalars().all()

    latest = {}
    for r in reports:
        if r.fuel_type not in latest:
            latest[r.fuel_type] = r
    return latest


async def get_city_stations(city_id: int) -> list:
    async with async_session() as session:
        result = await session.execute(
            select(Station)
            .where(
                Station.city_id == city_id,
                Station.is_active == True,
                Station.is_verified == True,
            )
            .order_by(Station.brand, Station.address)
        )
        return result.scalars().all()


async def get_station_summary(station_id: int) -> dict:
    latest = await get_last_reports(station_id)
    return {fuel: r.availability for fuel, r in latest.items()}


def merge_summaries(summaries: list) -> dict:
    """Объединяет сводки нескольких заправок: берёт лучший статус по топливу"""
    merged = {}
    for s in summaries:
        for fuel, status in s.items():
            if fuel not in merged or STATUS_RANK.get(status, -1) > STATUS_RANK.get(merged[fuel], -1):
                merged[fuel] = status
    return merged


def format_summary_line(summary: dict) -> str:
    if not summary:
        return "📭 нет данных"
    return " | ".join(f"{AVAILABILITY_EMOJI.get(st, '')} {fuel}" for fuel, st in summary.items())


def unique_brands(stations: list) -> list:
    brands = []
    for s in stations:
        b = (s.brand or "Другое").strip()
        if b not in brands:
            brands.append(b)
    return brands


def format_card(station: Station, latest: dict) -> str:
    lines = [f"⛽ {station.brand} — {station.name}", f"📍 {station.address}", ""]
    if not latest:
        lines.append("📭 Данных пока нет. Будь первым, кто оставит отчёт!")
    else:
        lines.append("Текущее состояние:")
        for fuel, r in latest.items():
            age = datetime.utcnow() - r.created_at
            hours = int(age.total_seconds() // 3600)
            time_str = f"{hours} ч. назад" if hours > 0 else "только что"
            price_str = f" | 💰 {r.price:.2f}₽" if r.price else ""
            lines.append(
                f"{AVAILABILITY_EMOJI.get(r.availability, '')} {fuel}: "
                f"{AVAILABILITY_TEXT.get(r.availability, r.availability)} | "
                f"{QUEUE_EMOJI.get(r.queue_level, '')} {QUEUE_TEXT.get(r.queue_level, r.queue_level)} | "
                f"🕐 {time_str}{price_str}"
            )
    return "\n".join(lines)


def compact_summary(summary: dict) -> str:
    """Компактная строка статусов для кнопки: '✅ АИ-92 ❌ ДТ'"""
    if not summary:
        return ""
    return "  " + " ".join(f"{AVAILABILITY_EMOJI.get(st, '')} {fuel}" for fuel, st in summary.items())


def format_feed_card(station: Station, latest: dict) -> str:
    """Читаемая карточка для ленты: каждый вид топлива отдельным блоком"""
    lines = [f"⛽ {station.brand} — {station.name}", f"📍 {station.address}", ""]
    if not latest:
        lines.append("📭 Данных пока нет.")
        return "\n".join(lines)

    for fuel, r in latest.items():
        age = datetime.utcnow() - r.created_at
        hours = int(age.total_seconds() // 3600)
        time_str = f"{hours} ч. назад" if hours > 0 else "только что"
        lines.append(
            f"{AVAILABILITY_EMOJI.get(r.availability, '')} {fuel} · "
            f"{AVAILABILITY_TEXT.get(r.availability, r.availability)} · "
            f"{QUEUE_EMOJI.get(r.queue_level, '')} {QUEUE_TEXT.get(r.queue_level, r.queue_level)}"
        )
        price_time = f"💰 {r.price:.2f}₽" if r.price else ""
        if price_time:
            price_time += f" · {time_str}"
        else:
            price_time = time_str
        lines.append(f"{price_time}")
        lines.append("")

    return "\n".join(lines).rstrip()
