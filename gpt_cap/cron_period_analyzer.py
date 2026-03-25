import re

def get_cron_minute_interval(cron):
    # "*/5 * * * *"을 5로 return
    fields = cron.split()
    if len(fields) < 1:
        return None
    minute_field = fields[0]    
    m = re.match(r"\*/(\d+)", minute_field)
    if m:
        return int(m.group(1))
    if minute_field.isdigit():
        return int(minute_field)
    return None

def get_period_seconds(period):
    if isinstance(period, int) or isinstance(period, float):
        return period / 1000  # ms -> sec
    elif isinstance(period, str):
        m = re.match(r"(\d+)\s*(msec|ms|sec|s|min|mn)", period.lower())
        if m:
            value = int(m.group(1))
            unit = m.group(2)
            if unit in ("msec", "ms"):
                return value / 1000
            elif unit in ("sec", "s"):
                return value
            elif unit in ("min", "mn"):
                return value * 60
    return None

def check_cron_period_overlap(cron, period):
    cron_interval = get_cron_minute_interval(cron)
    period_sec = get_period_seconds(period)
    if cron_interval and period_sec:
        # 둘 다 1분 이상 주기일 때만 검사        
        if cron_interval*60.0 == period_sec:
            return "Overlap issue (cron and period)"
    return None