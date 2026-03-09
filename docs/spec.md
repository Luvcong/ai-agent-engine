# Agent API 명세서

Edu Agent의 API 엔드포인트 정의입니다.

## 기본 정보

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api`
- **Content-Type**: `application/json`


## 채팅 히스토리 API

### (1) 최근 질문 조회
**GET** `/api/v1/threads`

#### Response JSON
```json
{
  "response": [
    {
      "thread_id": "uuid.UUID",      
      "title": "string",             
      "type": "string",              
      "created_at": "2024-01-14T14:20:00Z",  
      "updated_at": "2024-01-14T14:20:00Z",  
      "is_favorited": true           
    }
  ]
}
```

---

### (2) 최근 질문 상세 조회
**GET** `/api/v1/threads/{thread_id}`

#### Response JSON
```json
{
  "thread_id": "uuid.UUID",      
  "title": "string",             
  "messages": [
    {
      "message_id": "uuid.UUID", 
      "role": "user",            
      "message": "string",       
      "is_favorited": false,     
      "created_at": "2024-01-14T14:20:00Z"
    },
    {
      "message_id": "uuid.UUID",
      "role": "assistant",
      "message": "string",       
      "metadata": {
        "code_snippet": "string",
        "data": {},
        "chart": {}
      },
      "created_at": "2024-01-14T14:20:00Z"
    }
  ]
}
```

---

## 채팅 API

### (1) 대화 요청
**POST** `/api/v1/chat`

#### Request JSON
```json
{
  "thread_id": "uuid.UUID",
  "message": "string"
}
```

#### Response JSON
- tool streaming 데이터
```json
{
  "step": "model", 
  "tool_calls": ["analyze_data"]
},
{
 "step": "tools", 
  "name": "analyze_data", 
  "content": {
    "code_snippet":"import pandas as pd\nresult = df.groupby('category').sum()",
    "result_message":"데이터 분석이 완료되었습니다."
  }
},
{
  "step": "model",
  "tool_calls": ["fetch_data"]
},
{
  "step": "tools",
  "name": "fetch_data",
  "content": 
  {
    "success":true,
    "message":"데이터 조회 완료 (3개 행)",
    "data":
    {
      "dataTable": {
        "columns": {
          "카테고리":["A","B","C"],
          "매출":["1000","2000","3000"]
        }
      }
    },
    "row_count":3,
    "error":null
  }
},
{
  "step": "model",
  "tool_calls": ["create_chart"]
},
{
  "step": "tools",
  "name": "create_chart",
  "content": {
    "success":true,
    "message":"차트 데이터가 생성되었습니다",
    "chart_data": {
      "title": {
        "text":"카테고리별 매출 현황"
      },
      "series":[
        {
          "name":"매출",
          "data":[1000.0, 2000.0, 3000.0]
        }
      ],
      "chart": {
        "type":"column"
      },
      "xAxis": {
        "categories":["A","B","C"]
      }
    },
    "error":null
  }
},
```
- 최종 응답

```json

{
  "step": "done", 
  "message_id": "b3d6f8a2-8c4f-4b2a-9f5d-1e2a3b4c5d6e",
  "role": "assistant",
  "content": "요청하신 월별 데이터 분석 결과와 차트를 생성했습니다.",
  "metadata": {
    "code_snippet": "import pandas as pd\n# sample analysis snippet",
    "data": {"dataTable": {"columns": {"카테고리": ["A", "B", "C"], "실적": [100, 200, 300]}}},
    "chart": {"title": {"text": "분석 결과"}, "series": [{"name": "실적", "data": [100, 200, 300]}], "chart": {"type": "column"}, "xAxis": {"categories": ["A", "B", "C"]}}
  },
  "created_at": "2025-11-17T08:03:01.668851"
}

```

---

## 참고
- `metadata`에는 코드 스니펫(`code_snippet`), 데이터, 차트 정보가 포함될 수 있습니다.  
- `is_favorited`로 즐겨찾기 여부를 관리합니다.  
- 날짜 필드는 ISO 8601 포맷 (`YYYY-MM-DDTHH:mm:ssZ`)을 사용합니다.
