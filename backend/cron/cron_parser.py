# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Autonomous Cron Engine
# ==============================================================================

import re
from datetime import datetime, timedelta
from typing import List, Set, Tuple, Optional, Dict, Any

MONTH_NAMES = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

DAY_NAMES = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6
}

SPECIAL_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
    "@every_1m": "* * * * *",
    "@every_5m": "*/5 * * * *",
    "@every_10m": "*/10 * * * *",
    "@every_15m": "*/15 * * * *",
    "@every_30m": "*/30 * * * *",
    "@every_6h": "0 */6 * * *"
}

class CronParseError(ValueError):
    """Raised when a cron expression cannot be parsed."""
    pass

class CronExpression:
    """
    High-performance, pure-Python Cron Expression Parser and Schedule Calculator.
    Zero external dependencies, highly resilient, and supports English and Bengali summaries.
    """
    def __init__(self, expression: str):
        self.raw_expression = expression.strip()
        self.expression = self._resolve_alias(self.raw_expression)
        self.minutes, self.hours, self.days, self.months, self.weekdays = self._parse()

    def _resolve_alias(self, expr: str) -> str:
        low = expr.lower()
        if low in SPECIAL_ALIASES:
            return SPECIAL_ALIASES[low]
        return expr

    def _parse_field(self, field: str, min_val: int, max_val: int, name_map: Optional[Dict[str, int]] = None) -> Set[int]:
        field = field.strip().upper()
        if name_map:
            for name, val in name_map.items():
                field = re.sub(rf'\b{name}\b', str(val), field)

        result: Set[int] = set()
        parts = field.split(",")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Step values: */step or range/step
            if "/" in part:
                sub_parts = part.split("/")
                if len(sub_parts) != 2:
                    raise CronParseError(f"Invalid step format: '{part}'")
                range_part, step_str = sub_parts
                if not step_str.isdigit() or int(step_str) <= 0:
                    raise CronParseError(f"Invalid step value: '{step_str}'")
                step = int(step_str)

                if range_part == "*":
                    start, end = min_val, max_val
                elif "-" in range_part:
                    r_sub = range_part.split("-")
                    if len(r_sub) != 2 or not r_sub[0].isdigit() or not r_sub[1].isdigit():
                        raise CronParseError(f"Invalid range in step: '{range_part}'")
                    start, end = int(r_sub[0]), int(r_sub[1])
                else:
                    if not range_part.isdigit():
                        raise CronParseError(f"Invalid range in step: '{range_part}'")
                    start, end = int(range_part), max_val

                if start < min_val or end > max_val or start > end:
                    raise CronParseError(f"Range out of bounds: {start}-{end} (allowed {min_val}-{max_val})")

                result.update(range(start, end + 1, step))

            # Range values: start-end
            elif "-" in part:
                sub_parts = part.split("-")
                if len(sub_parts) != 2 or not sub_parts[0].isdigit() or not sub_parts[1].isdigit():
                    raise CronParseError(f"Invalid range format: '{part}'")
                start, end = int(sub_parts[0]), int(sub_parts[1])
                if start < min_val or end > max_val or start > end:
                    raise CronParseError(f"Range out of bounds: {start}-{end} (allowed {min_val}-{max_val})")
                result.update(range(start, end + 1))

            # Wildcard
            elif part == "*":
                result.update(range(min_val, max_val + 1))

            # Exact number
            elif part.isdigit():
                val = int(part)
                # Weekday special case: 7 is Sunday (same as 0)
                if min_val == 0 and max_val == 6 and val == 7:
                    val = 0
                if val < min_val or val > max_val:
                    raise CronParseError(f"Value '{val}' out of bounds ({min_val}-{max_val})")
                result.add(val)
            else:
                raise CronParseError(f"Unrecognized token in cron field: '{part}'")

        if not result:
            raise CronParseError(f"Field '{field}' produced an empty set")
        return result

    def _parse(self) -> Tuple[Set[int], Set[int], Set[int], Set[int], Set[int]]:
        tokens = self.expression.split()
        if len(tokens) != 5:
            raise CronParseError(f"Cron expression must contain 5 fields, got {len(tokens)}: '{self.expression}'")

        minutes = self._parse_field(tokens[0], 0, 59)
        hours = self._parse_field(tokens[1], 0, 23)
        days = self._parse_field(tokens[2], 1, 31)
        months = self._parse_field(tokens[3], 1, 12, MONTH_NAMES)
        weekdays = self._parse_field(tokens[4], 0, 6, DAY_NAMES)

        return minutes, hours, days, months, weekdays

    def matches(self, dt: datetime) -> bool:
        """Checks if a given datetime exactly matches this cron schedule."""
        # Note: Sunday is 6 in Python dt.weekday() (Monday is 0).
        # Standard cron: Sunday is 0 (or 7), Monday is 1 ... Saturday is 6.
        # Python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6.
        # Convert Python weekday to Cron weekday: (python_weekday + 1) % 7
        cron_wday = (dt.weekday() + 1) % 7

        if dt.minute not in self.minutes:
            return False
        if dt.hour not in self.hours:
            return False
        if dt.month not in self.months:
            return False

        # In standard cron, if both DOM and DOW are specified (not *), it is an OR condition
        tokens = self.expression.split()
        dom_restricted = tokens[2] != "*"
        dow_restricted = tokens[4] != "*"

        if dom_restricted and dow_restricted:
            if dt.day not in self.days and cron_wday not in self.weekdays:
                return False
        elif dom_restricted:
            if dt.day not in self.days:
                return False
        elif dow_restricted:
            if cron_wday not in self.weekdays:
                return False

        return True

    def get_next_run(self, base_time: Optional[datetime] = None) -> datetime:
        """
        Calculates the next matching datetime strictly after base_time.
        Fast minute-stepping search limited to 5 years forward.
        """
        if base_time is None:
            base_time = datetime.now()

        # Start from the next minute with 00 seconds
        candidate = base_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        max_searches = 525600 * 5  # 5 years in minutes

        searched = 0
        while searched < max_searches:
            # Optimize fast skipping by month
            if candidate.month not in self.months:
                # Advance to next month 1st day 00:00
                year = candidate.year + (1 if candidate.month == 12 else 0)
                month = 1 if candidate.month == 12 else candidate.month + 1
                candidate = datetime(year, month, 1, 0, 0, 0)
                searched += 1440
                continue

            # Fast skip by day
            cron_wday = (candidate.weekday() + 1) % 7
            tokens = self.expression.split()
            dom_restricted = tokens[2] != "*"
            dow_restricted = tokens[4] != "*"

            day_match = True
            if dom_restricted and dow_restricted:
                day_match = (candidate.day in self.days) or (cron_wday in self.weekdays)
            elif dom_restricted:
                day_match = candidate.day in self.days
            elif dow_restricted:
                day_match = cron_wday in self.weekdays

            if not day_match:
                candidate = candidate.replace(hour=0, minute=0) + timedelta(days=1)
                searched += 1440
                continue

            # Fast skip by hour
            if candidate.hour not in self.hours:
                candidate = candidate.replace(minute=0) + timedelta(hours=1)
                searched += 60
                continue

            # Minute check
            if candidate.minute in self.minutes:
                return candidate

            candidate += timedelta(minutes=1)
            searched += 1

        raise CronParseError("No scheduled run found within the next 5 years.")

    def get_next_runs(self, count: int = 5, base_time: Optional[datetime] = None) -> List[datetime]:
        """Returns the upcoming N executions."""
        runs = []
        curr = base_time or datetime.now()
        for _ in range(count):
            nxt = self.get_next_run(curr)
            runs.append(nxt)
            curr = nxt
        return runs

    def to_human_en(self) -> str:
        """Returns human-readable English description."""
        tokens = self.expression.split()
        m, h, dom, mon, dow = tokens

        if self.expression == "* * * * *":
            return "Every minute"
        if m.startswith("*/"):
            step = m.split("/")[1]
            return f"Every {step} minutes"
        if m == "0" and h == "*":
            return "Hourly at minute 0"
        if h.startswith("*/") and m == "0":
            step = h.split("/")[1]
            return f"Every {step} hours"
        if dom == "*" and mon == "*" and dow == "*":
            return f"Daily at {int(h):02d}:{int(m):02d}"
        if dom == "*" and mon == "*" and dow != "*":
            w_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            days_str = ", ".join(w_names[int(x) % 7] for x in dow.split(",") if x.isdigit())
            return f"Weekly on {days_str} at {int(h):02d}:{int(m):02d}"
        if dom != "*" and mon == "*":
            return f"Monthly on day {dom} at {int(h):02d}:{int(m):02d}"
        return f"Scheduled: {self.expression}"

    def to_human_bn(self) -> str:
        """Returns human-readable Bengali description."""
        tokens = self.expression.split()
        m, h, dom, mon, dow = tokens

        if self.expression == "* * * * *":
            return "প্রতি মিনিটে"
        if m.startswith("*/"):
            step = m.split("/")[1]
            return f"প্রতি {step} মিনিট অন্তর অন্তর"
        if m == "0" and h == "*":
            return "প্রতি ঘণ্টার শুরুতে"
        if h.startswith("*/") and m == "0":
            step = h.split("/")[1]
            return f"প্রতি {step} ঘণ্টা পর পর"
        if dom == "*" and mon == "*" and dow == "*":
            return f"প্রতিদিন {int(h):02d}:{int(m):02d} টায়"
        if dom == "*" and mon == "*" and dow != "*":
            w_names = ["রবিবার", "সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার"]
            days_str = ", ".join(w_names[int(x) % 7] for x in dow.split(",") if x.isdigit())
            return f"প্রতি {days_str} {int(h):02d}:{int(m):02d} টায়"
        if dom != "*" and mon == "*":
            return f"প্রতি মাসের {dom} তারিখে {int(h):02d}:{int(m):02d} টায়"
        return f"শিডিউল: {self.expression}"


def validate_cron_expression(expr: str) -> Dict[str, Any]:
    """Validates expression and returns metadata."""
    try:
        cron = CronExpression(expr)
        next_run = cron.get_next_run()
        next_runs = cron.get_next_runs(5)
        return {
            "valid": True,
            "expression": cron.expression,
            "human_en": cron.to_human_en(),
            "human_bn": cron.to_human_bn(),
            "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S"),
            "next_runs": [r.strftime("%Y-%m-%d %H:%M:%S") for r in next_runs],
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "expression": expr,
            "human_en": "Invalid expression",
            "human_bn": "ত্রুটিপূর্ণ ক্রন এক্সপ্রেশন",
            "next_run": None,
            "next_runs": [],
            "error": str(e)
        }
