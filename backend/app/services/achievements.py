from datetime import date
from sqlalchemy.orm import Session
from .. import models as m

CATALOG = {
    "first_meal": "First meal logged", "first_workout": "First workout", "streak_7": "7-day streak", "streak_30": "30-day streak",
    "lost_1kg": "First 1 kg lost", "goal_achieved": "Goal achieved",
}


def _streak(days: set[date]) -> int:
    from datetime import timedelta
    d, n = date.today(), 0
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def evaluate(db: Session, user: m.User) -> list[str]:
    uid = user.id
    have = {a.key for a in db.query(m.Achievement).filter_by(user_id=uid)}
    fd = {r[0] for r in db.query(m.FoodLog.day).filter_by(user_id=uid)}
    wd = {r[0] for r in db.query(m.WorkoutLog.day).filter_by(user_id=uid)}
    wl = db.query(m.WeightLog).filter_by(user_id=uid).order_by(m.WeightLog.day).all()
    s = _streak(fd | wd)
    earned = set()
    if fd: earned.add("first_meal")
    if wd: earned.add("first_workout")
    if s >= 7: earned.add("streak_7")
    if s >= 30: earned.add("streak_30")
    p = user.profile
    if len(wl) >= 2 and wl[0].weight_kg - wl[-1].weight_kg >= 1 and p and p.goal_type == "lose": earned.add("lost_1kg")
    if p and p.target_weight_kg and wl:
        last = wl[-1].weight_kg
        if (p.goal_type == "lose" and last <= p.target_weight_kg) or (p.goal_type == "gain" and last >= p.target_weight_kg):
            earned.add("goal_achieved")
    new = earned - have
    for k in new:
        db.add(m.Achievement(user_id=uid, key=k))
    db.commit()
    return sorted(new)
