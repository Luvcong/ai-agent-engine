from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import LangChainMessage, ConversationSummary, ConversationResponse


class ConversationService:
    """대화 세션 관리 서비스 (메모리 기반, 향후 DB로 확장 가능)"""
    
    # 대화 요약 정보와 메시지 목록을 메모리 저장소로 초기화한다.
    def __init__(self):
        # 메모리 기반 저장소 (향후 DB로 교체 가능)
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._messages: Dict[str, List[LangChainMessage]] = {}
    
    # 새 대화 세션을 만들고 첫 메시지까지 함께 저장한다.
    def create_conversation(
        self,
        conversation_id: str,
        title: str,
        # IMP: 대화가 없을 경우 초기 프롬프트를 LangChainMessage 포맷으로 생성하여 저장소에 초기화하는 구현.
        initial_message: LangChainMessage
    ) -> str:
        """새 대화 세션을 생성합니다."""
        now = datetime.utcnow().isoformat() + "Z"
        
        self._conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 1,
            "last_message": initial_message.content if isinstance(initial_message.content, str) else str(initial_message.content)
        }
        
        self._messages[conversation_id] = [initial_message]
        
        return conversation_id
    
    # 기존 대화에 새 메시지를 추가하고 대화 요약 정보를 갱신한다.
    def add_message(
        self,
        conversation_id: str,
        # IMP: LangChainMessage 포맷으로 전달받은 새로운 메시지를 내부 대화 문맥 스토어(Memory)에 추가하는 로직 구현.
        message: LangChainMessage
    ):
        """대화 세션에 메시지를 추가합니다."""
        if conversation_id not in self._conversations:
            # 새 대화 생성
            title = message.content[:50] if isinstance(message.content, str) else "새 대화"
            self.create_conversation(conversation_id, title, message)
            return
        
        # 메시지 추가
        if conversation_id not in self._messages:
            self._messages[conversation_id] = []
        
        self._messages[conversation_id].append(message)
        
        # 대화 정보 업데이트
        self._conversations[conversation_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._conversations[conversation_id]["message_count"] = len(self._messages[conversation_id])
        if message.role == "user":
            self._conversations[conversation_id]["last_message"] = (
                message.content if isinstance(message.content, str) else str(message.content)
            )
    
    # 메모리에 저장된 대화 목록을 최신순으로 페이지네이션해 반환한다.
    def get_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> tuple[List[ConversationSummary], int]:
        """대화 목록을 조회합니다."""
        # user_id 필터링은 향후 구현
        conversations = list(self._conversations.values())
        total_count = len(conversations)
        
        # 정렬 (updated_at 기준 내림차순)
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        # 페이지네이션
        paginated = conversations[offset:offset + limit]
        
        summaries = [
            ConversationSummary(**conv) for conv in paginated
        ]
        
        return summaries, total_count
    
    # 대화 ID로 메시지 내역을 조회하고 필요 시 메타데이터 payload를 숨긴다.
    def get_conversation(
        self,
        conversation_id: str,
        include_data: bool = False
    ) -> Optional[ConversationResponse]:
        """대화 내용을 조회합니다."""
        if conversation_id not in self._conversations:
            return None
        
        conv_info = self._conversations[conversation_id]
        messages = self._messages.get(conversation_id, [])
        
        # include_data가 False인 경우 data와 chart 제거
        if not include_data:
            filtered_messages = []
            for msg in messages:
                msg_dict = msg.dict() if hasattr(msg, 'dict') else msg
                if isinstance(msg_dict, dict) and msg_dict.get("role") == "assistant":
                    if "response_metadata" in msg_dict:
                        metadata = msg_dict["response_metadata"]
                        if isinstance(metadata, dict):
                            metadata["data"] = None
                            metadata["chart"] = None
                filtered_messages.append(LangChainMessage(**msg_dict) if isinstance(msg_dict, dict) else msg)
            messages = filtered_messages
        
        return ConversationResponse(
            conversation_id=conv_info["conversation_id"],
            title=conv_info["title"],
            created_at=conv_info["created_at"],
            updated_at=conv_info["updated_at"],
            messages=messages,
            message_count=conv_info["message_count"]
        )


# 전역 인스턴스
conversation_service = ConversationService()
