#!/usr/bin/env python3
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import db
from config import Config

def main():
    db.connect()
    now_ph = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    print(f"IT 107 Monitoring Report - {now_ph.strftime('%Y-%m-%d %H:%M PHT')}")
    scan_total = db.execute_query(
        "SELECT COUNT(*) c FROM activity_log WHERE created_at > now() - interval '24 hours'")
    print(f"Scanned: {int(dict(scan_total[0])['c'])} events (last 24 hours)")

    findings = []
    today = datetime.date.today()

    rows = db.execute_query(
        """SELECT host(ip_address) ip, COUNT(*) c, COUNT(DISTINCT details) d
           FROM activity_log
           WHERE event_type='LOGIN_FAILED' AND created_at > now() - interval '24 hours'
           GROUP BY ip_address HAVING COUNT(*) >= %s""", (Config.IP_BLOCK_THRESHOLD,))
    for r in rows:
        r = dict(r)
        findings.append(('IP_OVER_THRESHOLD', r['ip'], 'HIGH',
                         f"{r['c']} failures across any usernames"))

    rows = db.execute_query(
        """SELECT details, COUNT(DISTINCT ip_address) ips
           FROM activity_log
           WHERE event_type='LOGIN_FAILED' AND created_at > now() - interval '24 hours'
           GROUP BY details HAVING COUNT(DISTINCT ip_address) >= 3""")
    for r in rows:
        r = dict(r)
        findings.append(('ACCOUNT_TARGETED', r['details'], 'MED',
                         f"failures from {r['ips']} IPs"))

    rows = db.execute_query(
        """SELECT user_id, COUNT(*) c
           FROM activity_log
           WHERE event_type='OTP_FAILED' AND created_at > now() - interval '10 minutes'
           GROUP BY user_id HAVING COUNT(*) >= 5""")
    for r in rows:
        r = dict(r)
        findings.append(('OTP_GUESSING', str(r['user_id']), 'MED',
                         f"{r['c']} wrong OTPs in 10 min"))

    rows = db.execute_query(
        """SELECT user_id, created_at FROM activity_log
           WHERE event_type='LOGIN_SUCCESS'
             AND created_at > now() - interval '24 hours'
             AND EXTRACT(HOUR FROM created_at AT TIME ZONE 'Asia/Manila') BETWEEN 0 AND 4""")
    for r in rows:
        r = dict(r)
        findings.append(('OFF_HOURS_LOGIN', str(r['user_id']), 'LOW',
                         f"login at {r['created_at']}"))

    new_flags = 0
    already = 0
    for pattern, target, sev, details in findings:
        print(f"[{sev}] {pattern.replace('_',' ').title():22} {target:30} {details}")
        try:
            db.execute_query(
                """INSERT INTO security_flags (pattern, target, severity, details, day)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (pattern, target, day) DO NOTHING""",
                (pattern, target, sev, details, today))
            new_flags += 1
        except Exception:
            already += 1

    print(f"New flags written: {new_flags}  Already flagged today: {already}")
    db.close()

if __name__ == '__main__':
    main()