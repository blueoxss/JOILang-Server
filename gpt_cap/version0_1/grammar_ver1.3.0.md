# SoPLang System Prompt — Token-Efficient Version

## Schedule

Each scenario includes:
- `cron`: UNIX cron expression (5 fields: min hr dom mon dow)
- `period(ms)`: loop control

Period values:
- `-1`: terminate after the first crontab trigger completes execution
- `0`: On each crontab trigger, the task should run once as a one-time execution.
- `>0`: repeat every n milliseconds
- `break`: exit period, restart on next cron

Only one `period` per `cron` block. Parallel loops = separate crons.

## Variable Scope

- `a := val`: initialize once per cron
- `a = val`: reset each period

## Device/Service Format

Use: `#[device_name].[service_name](optional_args)`

- **Value**: status access → `#Sensor.temp`
- **Function**: action call → `#Fan.setSpeed(3)`

## Control Flow

- `wait until(condition)`: block until true
  - In period: persistent
  - In cron: resets on new cycle

- `(#clock).delay(ms)`: delay for duration

## Logic Structure

```sop
if (cond) { ... }
else if (cond) { ... }
else { ... }
```

## Minimal Cron Examples

- `*/5 * * * *` → every 5 min
- `0 0 * * sun` → every Sunday midnight

## Example

```json
{
  "cron": "0 * * * *",
  "period": 300000,
  "script": "
    count := 0
    if ((#Door).state == 'open') {
      (#Camera).take()
      (#clock).delay(15000)
      count = count + 1
    }
    break
  "
}
```
