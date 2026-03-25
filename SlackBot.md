여기에 관리자 로그 폴더를 만들어서 slack으로 ai 사용자를 하나 만들어서 그 챗봇에게 dm을 보내면 그 내용을 기록해서 저장하는 기능을 만들거야. 날짜별로 분류해서 어느 사용자로부터 어떤 문제점을 보고받는지 필요한 정보들을 저장하도록 해줘. 그리고 이건 한번 날을 잡아서 한번에 llm 모델과 프로젝트를 수정하고 반영하는데 사용될 거야.

[봇 권한(Scopes) 부여]
- 봇이 DM을 읽을 수 있도록 권한
- 스크롤을 내려 Scopes 부분의 Bot Token Scopes에서 **[Add an OAuth Scope]**를 누릅니다.
- 다음 두 가지 권한을 찾아 추가:
    im:history (DM 기록을 읽기 위한 권한)
    chat:write (필요시 봇이 답장을 보내기 위한 권한)

[이벤트 구독(Event Subscriptions) 켜기]
- 누군가 봇에게 DM을 보냈을 때, 그 알림(Event)을 로컬로 보내도록 설정
- 좌측 메뉴에서 **[Event Subscriptions]**로 이동합니다.
- Enable Events 스위치를 켭니다.

- 스크롤을 내려 Subscribe to bot events를 엽니다.
- **[Add Bot User Event]**를 누르고 message.im을 찾아 추가.
- (DM 메시지가 올 때마다 이벤트를 받겠다는 뜻입니다.)

[워크스페이스에 설치 및 토큰 발급]
- 좌측 메뉴에서 **[Install App]**으로 이동합니다.
- [Install to Workspace] 버튼을 누르고 허용(Allow)
- 설치가 완료되면 xoxb-...로 시작하는 Bot User OAuth Token이 발급
- App Home > Allow users to send Slash commands and messages from the messages tab