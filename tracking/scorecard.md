# Scorecard

Fill one row in `scores.csv` when you finish each project. Score each question 1 to 5. Energy is not typed in: `decide.py` takes the average energy from your sessions in `sessions.csv`.

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

After the Semester 1 courses, run `python3 tracking/decide.py`. It applies the rules from the career report:

1. If digital (fifo_bridge + cpu) or analog (opamp + adc) is ahead by 15% or more, pick it.
2. Otherwise pick digital and keep AMS verification as a bridge.
3. If opamp energy is 2 or lower, analog is out regardless of the adc.
4. If the adc is the top project, consider data converter design.
