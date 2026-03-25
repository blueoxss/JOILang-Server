<Draft format manual>
Command: "1월 1일에 문이 닫혀있고 알람이 꺼져있을 때마다 5초 뒤에 알람을 키고, 이후 블라인드가 닫혔다 열렸을 때 알람을 킨 시점에서 3초가 지나있으면 짝수 태그가 붙은 알람을 모두 꺼줘.
Step1: Result of chunking. Do not specify condition statement. Match only with items in Connected device and Tag. If none are available, substitute with the most similar one.
Print each chunk's tag, period, duration, or delay.
Step2: Select condition statement.
Step3: Set cron and period.
Step4: Usage of phase variable and break. There must be a clear reason.
Step5: Simulate and Check Error.

<Draft example>
Step1: [1월 1일에 문이 닫혀있고 알람이 꺼져있을 때마다(period, meet multiple)]→[5초 뒤에(delay)]→[알람을 키고(now)]→[블라인드가 닫혔다 열렸을 때(meet once)]→[알람을 킨 시점에서 3초가 지나있으면(duration)]→[짝수 태그가 붙은 알람을 모두 꺼줘(짝수,모두,once)] 
Step2: cond1: if+triggered, cond2: 2 consecutive wait until
Step3: cron: "0 0 1 1 *", period: 100
Step4: use phase (if with period 100 and wait until co-exist), break when it isn't 1월 1일 (period > 0)
Step5: X

