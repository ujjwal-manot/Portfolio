# Scorecard

Fill one row in `scores.csv` when you finish each project. Score each question 1 to 5. Energy comes from your sessions in `sessions.csv`, not from this table.

| Column | Question |
|---|---|
| endurance | Would a version ten times harder be welcome every day for two years? |
| debugging | Did fixing failures feel like a puzzle (5) or a chore (1)? |
| interview | Were the ten interview questions in the project README enjoyable to answer? |
| sharing | Did you explain the project to someone without being asked? |

Log every session as it ends:

```
python3 tracking/log_session.py cpu 2.5 4 yes no "forwarding finally worked" "load-use bug took an hour"
```

Arguments: project, hours, energy 1 to 5, lost track of time (yes/no), did extra work nobody asked for (yes/no), best moment, worst moment.

Arguments for `whole_chip` work the same way; its hours count a third to each track.

Check the split at any time:

```
python3 tracking/balance.py
```

It prints hours and finished checks for digital, analog and AMS. A check counts as finished only if it passed and none of its sources changed since. It fails if any track is more than 10% behind the leader on either number, which is the signal to work on that track next.
