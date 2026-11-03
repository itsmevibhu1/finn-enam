"""Evaluate session coverage independently of a successful HTTP request."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def expected_session(now,calendar):
    local=now.astimezone(ZoneInfo(calendar['timezone']))
    if local.year not in calendar['years']:
        return None
    for offset in range(15):
        candidate=local.date()-timedelta(days=offset)
        if candidate.year not in calendar['years']:
            return None
        key=str(candidate)
        special=calendar.get('special_sessions',{}).get(key)
        if not special and (candidate.weekday()>=5 or key in calendar['holidays']):
            continue
        cutoff=time.fromisoformat(special['eod_available_after'] if special else calendar['regular_eod_available_after'])
        if offset==0 and local.time()<cutoff:
            continue
        return key
    return None


def freshness(session_date,now,calendar):
    expected=expected_session(now,calendar)
    if not expected:
        return {'status':'unknown_calendar','expected_session':None,'reason':'Trading-calendar coverage is not configured for this date.'}
    if session_date==expected:
        return {'status':'current','expected_session':expected,'reason':'Returned session matches the configured completed-session calendar.'}
    if session_date<expected:
        return {'status':'stale','expected_session':expected,'reason':f'Returned session {session_date}; expected completed session {expected}.'}
    return {'status':'unexpected_session','expected_session':expected,'reason':'Provider returned a session after the configured completed-session cutoff.'}
