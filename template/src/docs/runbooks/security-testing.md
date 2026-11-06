# Security testing

A pentest or external scan is prepared before a vendor is booked, so it can start on a day's notice without the
scope or the rules living in chat. The record is one *Security test* issue.

## Before booking
- List the scope for the environment under test: every path and method in the API contract, with the base URL.
- Open a *Security test* issue: window, stance, scope, findings recipient, alarm channel.
- Agree the release freeze with the client and record it in the issue.

## Onboarding testers
- Create only the accounts the stance needs, and list each one in the issue with its removal date.
- Put the removal date on the team calendar.
- Ask for the testers' source addresses before day one.

## During the test
- No releases to the tested environment unless the issue says otherwise.
- Alarms go to the team channel named in the issue; match them against the testers' addresses before treating them
  as an incident.

## After the test
- Turn each finding into an issue, linked from the *Security test* issue, and update the threat model.
- Remove every tester account on its removal date, and tick it off in the issue.
- Lift the freeze and close the issue.

## Symptoms

| Symptom | Fix |
|---|---|
| The vendor asks for scope at short notice | List it from the API contract and paste it into the issue; do not assemble it from chat |
| An alarm fires during the window | Check the testers' source addresses first; if they don't match, treat it as an incident |
| A tester account is still active after the window | Remove it now and record the late removal in the issue |
