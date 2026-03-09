from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from typing_extensions import Literal


# IMP: LangChain의 복합 메시지 구조를 지원하기 위한 Content Block 모델 정의.
class ContentBlock(BaseModel):
    type: str
    text: Optional[str] = None


# IMP: LangChain 프레임워크와 호환되는 기본 메시지 객체(LangChainMessage) 모델 정의. 
# role, content, tool_calls 등의 필드를 포함합니다.
class LangChainMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: Union[str, List[ContentBlock]]
    id: Optional[str] = None
    name: Optional[str] = None
    response_metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage_metadata: Optional[Dict[str, Any]] = None


# IMP: LangChain 형식의 메시지 리스트를 입력받아 처리하기 위한 Query Request 모델 정의.
class QueryRequest(BaseModel):
    messages: List[LangChainMessage]
    conversation_id: Optional[str] = None


# Query Request (간단한 형식, 하위 호환성)
class QueryRequestSimple(BaseModel):
    query: str


# Item Info
class ItemInfo(BaseModel):
    name: str
    type: str
    group: Optional[str] = None
    table: Optional[str] = None
    # schema: Optional[str] = None
    description: Optional[str] = None


# Code Info
class CodeInfo(BaseModel):
    code_table: str
    code_value: str
    code_name: str
    description: Optional[str] = None
    is_active: bool


# Grid Data
class GridDataMetadata(BaseModel):
    total_rows: Optional[int] = None
    column_types: Dict[str, str]


class GridData(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    row_count: int
    execution_time: Optional[float] = None
    metadata: GridDataMetadata


# Chart Definition
class ChartDataPoint(BaseModel):
    label: Optional[str] = None
    x: Optional[float] = None
    y: float
    color: Optional[str] = None


class ChartSeries(BaseModel):
    type: str
    name: Optional[str] = None
    showInLegend: Optional[bool] = None
    dataPoints: List[ChartDataPoint]


class ChartAxis(BaseModel):
    title: Optional[str] = None
    labelAngle: Optional[int] = None
    interval: Optional[int] = None
    gridThickness: Optional[int] = None
    gridColor: Optional[str] = None


class ChartLegend(BaseModel):
    cursor: Optional[str] = None
    itemclick: Optional[str] = None
    verticalAlign: Optional[Literal["top", "center", "bottom"]] = None
    horizontalAlign: Optional[Literal["left", "center", "right"]] = None


class ChartOptions(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    theme: Optional[Literal["light1", "light2", "dark1", "dark2"]] = None
    animationEnabled: Optional[bool] = None
    animationDuration: Optional[int] = None
    axisX: Optional[ChartAxis] = None
    axisY: Optional[ChartAxis] = None
    legend: Optional[ChartLegend] = None
    show_legend: Optional[bool] = None
    stacked: Optional[bool] = None
    colors: Optional[List[str]] = None
    sort: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ChartConfig(BaseModel):
    type: str
    data: List[ChartSeries]
    options: ChartOptions


class ChartDataGrid(BaseModel):
    columns: List[str]
    row_count: int
    preview: List[Dict[str, Any]]


class ChartMetadata(BaseModel):
    chart_type: str
    data_processed: bool
    warnings: Optional[List[str]] = None


class ChartDefinition(BaseModel):
    chart_config: ChartConfig
    data_grid: ChartDataGrid
    metadata: ChartMetadata


# Response Metadata
class ResponseMetadata(BaseModel):
    code_snippet: Optional[str] = None
    items: Optional[List[ItemInfo]] = None
    codes: Optional[List[CodeInfo]] = None
    data: Optional[GridData] = None
    chart: Optional[ChartDefinition] = None


# IMP: LangChain 에이전트의 응답(AIMessage)을 API 결과로 반환하기 위한 응답 DTO 모델 정의.
class AIMessageResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    id: Optional[str] = None
    response_metadata: ResponseMetadata
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Query Response (간단한 형식, 하위 호환성)
class QueryResponse(BaseModel):
    code_snippet: Optional[str] = None
    items: Optional[List[ItemInfo]] = None
    codes: Optional[List[CodeInfo]] = None
    data: Optional[GridData] = None
    chart: Optional[ChartDefinition] = None
    message: Optional[str] = None
    error: Optional[str] = None


# Conversation Summary
class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    last_message: str


# Conversations Response
class ConversationsResponse(BaseModel):
    conversations: List[ConversationSummary]
    total_count: int
    limit: int
    offset: int


# Conversation Response
class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[LangChainMessage]
    message_count: int

