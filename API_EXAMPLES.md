# API Examples — Israel News & Political Intelligence

Base URL: `http://localhost:8000`

---

## 🔐 Auth

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "shaikat",
  "password": "mypassword123"
}
```

### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=shaikat&password=mypassword123
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "tier": "free"
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

---

## 📰 News

### Get Categories
```http
GET /categories
```

### Get News by Category
```http
GET /news/economy?limit=10
GET /news/political?limit=20&exclude_negative=false
GET /news/positive?limit=15
GET /news/defence?limit=10
GET /news/education?limit=10
GET /news/community?limit=10&exclude_negative=true
GET /news/sport?limit=10
GET /news/culture?limit=10
GET /news/environment?limit=10
GET /news/science?limit=10
GET /news/international?limit=10
```

### Get All News (all categories)
```http
GET /news/all?limit=5
```

### Get Knesset Bills
```http
GET /news/knesset?limit=20
```

### Get Sources List
```http
GET /sources
```

---

## 🤖 AI Analysis

### Analyze Single Article
```http
POST /ai/analyze
Content-Type: application/json

{
  "guid": "article-unique-id-123",
  "title": "Israel economy grows 3% in Q1",
  "description": "The Israeli economy showed strong growth in the first quarter according to the Central Bureau of Statistics.",
  "source": "Times of Israel",
  "source_url": "https://timesofisrael.com"
}
```
**Response:**
```json
{
  "guid": "article-unique-id-123",
  "sentiment": "positive",
  "bias": "center",
  "credibility_score": 0.85,
  "fact_check_score": 0.77,
  "summary_hebrew": "[סיכום אוטומטי] Israel economy grows 3% in Q1",
  "topics": ["economy"]
}
```

### Analyze Batch (up to 20 articles)
```http
POST /ai/analyze/batch
Content-Type: application/json

{
  "articles": [
    {
      "guid": "art-001",
      "title": "Knesset approves new budget",
      "description": "The Israeli parliament approved the 2025 state budget after weeks of negotiations.",
      "source": "Haaretz",
      "source_url": "https://haaretz.com"
    },
    {
      "guid": "art-002",
      "title": "IDF reports security incident in north",
      "description": "The Israel Defense Forces reported a security incident near the northern border.",
      "source": "Jerusalem Post",
      "source_url": "https://jpost.com"
    }
  ],
  "use_ai": false
}
```

### Get Source Bias
```http
GET /ai/source-bias?source=Haaretz
GET /ai/source-bias?source=Jerusalem%20Post&source_url=https://jpost.com
```
**Response:**
```json
{
  "source_name": "Haaretz",
  "bias": "left",
  "credibility_score": 0.82,
  "bias_label": "⬅️ Left"
}
```

### Get All Sources Bias Table
```http
GET /ai/source-bias/all
```

---

## 🔗 Smart Correlation

### Cluster Articles by Theme
```http
POST /correlation/cluster
Content-Type: application/json

{
  "articles": [
    {
      "guid": "a1",
      "title": "Israel raises interest rates to fight inflation",
      "description": "Bank of Israel raises rates by 0.25%",
      "source": "Globes"
    },
    {
      "guid": "a2",
      "title": "Israeli shekel weakens amid rate hike concerns",
      "description": "Currency markets react to central bank decision",
      "source": "TheMarker"
    },
    {
      "guid": "a3",
      "title": "Knesset debates education reform bill",
      "description": "Parliament discusses changes to school curriculum",
      "source": "Times of Israel"
    }
  ],
  "use_ai": false
}
```
**Response:**
```json
{
  "total_articles": 3,
  "total_clusters": 2,
  "clusters_with_inconsistency": 0,
  "clusters": [
    {
      "theme": "rates, inflation, shekel",
      "article_count": 2,
      "articles": [...],
      "inconsistency": null,
      "method": "rule-based"
    },
    {
      "theme": "knesset, education, reform",
      "article_count": 1,
      "articles": [...],
      "inconsistency": null,
      "method": "rule-based"
    }
  ]
}
```

### Cluster Live News (auto-fetch + cluster)
```http
GET /correlation/cluster/live?limit=10&use_ai=false
```

### Cross-Reference News with Knesset Bills
```http
POST /correlation/cross-reference
Content-Type: application/json

{
  "articles": [
    {
      "guid": "a1",
      "title": "New education reform passes first reading",
      "description": "The education reform bill passed its first Knesset reading",
      "source": "Kan News"
    }
  ],
  "bills": [
    {
      "name": "Education Reform Act 2025",
      "name_hebrew": "חוק רפורמת החינוך",
      "status": "First Reading"
    }
  ]
}
```

### Cross-Reference Live (auto-fetch both)
```http
GET /correlation/cross-reference/live?limit=10
```

---

## 💡 AI Insights & Trends

### Get Insight for One Category
```http
GET /insights/economy?limit=20&use_ai=false
GET /insights/political?limit=20&use_ai=true
GET /insights/security?use_ai=false
```
**Response:**
```json
{
  "category": "economy",
  "article_count": 18,
  "insight_hebrew": "[economy] 18 articles analyzed. Key topics: shekel, inflation, budget...",
  "trends": [
    {
      "keyword": "shekel",
      "count": 5,
      "sample_headlines": ["Shekel weakens against dollar", "Bank of Israel defends shekel"]
    },
    {
      "keyword": "inflation",
      "count": 4,
      "sample_headlines": ["Inflation hits 3.2% in April"]
    }
  ],
  "ai_trends": [],
  "generated_at": "2025-05-24T10:00:00Z"
}
```

### Get Insights for All Categories
```http
GET /insights/all?limit=15&use_ai=false
```

### Get Global Trending Topics
```http
GET /insights/trends?limit=20&use_ai=false
```
**Response:**
```json
{
  "total_articles_analyzed": 156,
  "use_ai": false,
  "trends": [
    {"keyword": "knesset", "count": 12, "sample_headlines": [...]},
    {"keyword": "budget", "count": 9, "sample_headlines": [...]},
    {"keyword": "election", "count": 7, "sample_headlines": [...]}
  ]
}
```

---

## 💬 AI Q&A

### Ask GPT-4o
```http
POST /qa/ask
Content-Type: application/json

{
  "question": "What is the current state of the Israeli economy?",
  "category": "economy",
  "use_context": true,
  "model": "gpt-4o"
}
```
**Response:**
```json
{
  "answer": "Based on recent news, the Israeli economy is showing...",
  "model": "gpt-4o",
  "tokens_used": 312,
  "cached": false
}
```

### Ask in Hebrew
```http
POST /qa/ask
Content-Type: application/json

{
  "question": "מה קורה בכנסת השבוע?",
  "category": "political",
  "use_context": true,
  "model": "gpt-4o"
}
```

### Streaming Response (SSE)
```http
POST /qa/ask/stream
Content-Type: application/json

{
  "question": "Explain the latest Knesset bill on education",
  "use_context": true,
  "model": "gpt-4o-mini"
}
```
*Returns Server-Sent Events — each chunk: `data: <text>\n\n`*

### Ask ITHY-style
```http
POST /qa/ask/ithy
Content-Type: application/json

{
  "question": "What are the different perspectives on Israel's security situation?",
  "use_context": true,
  "model": "gpt-4o"
}
```

### Dual AI Comparison (GPT vs ITHY)
```http
POST /qa/ask/dual
Content-Type: application/json

{
  "question": "Is the Israeli coalition government stable?",
  "category": "political",
  "use_context": true,
  "model": "gpt-4o"
}
```
**Response:**
```json
{
  "question": "Is the Israeli coalition government stable?",
  "gpt": {
    "answer": "The current coalition faces several challenges...",
    "model": "gpt-4o",
    "tokens_used": 287
  },
  "ithy": {
    "answer": "From multiple perspectives, the coalition stability depends on...",
    "source": "ithy-simulated"
  },
  "comparison_note": "GPT focuses on specific coalition dynamics while ITHY provides broader multi-party analysis."
}
```

### Quick GET Q&A (browser/curl test)
```http
GET /qa/ask?q=What+is+happening+in+Israel+today&model=gpt-4o-mini
GET /qa/ask?q=מה+קורה+בישראל&category=political
```

---

## 🏛️ Political Intelligence

### Sync MPs/Parties/Committees from Knesset API (admin only)
```http
POST /political/sync
Authorization: Bearer <admin_token>
```

### List All MPs
```http
GET /political/mps
GET /political/mps?party_name=Likud
```

### Get MP Profile
```http
GET /political/mps/64f1a2b3c4d5e6f7a8b9c0d1
```
**Response:**
```json
{
  "id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "name": "Benjamin Netanyahu",
  "name_hebrew": "בנימין נתניהו",
  "role": "Prime Minister",
  "consistency_score": 0.72,
  "party": {"name": "Likud", "wing": "right"},
  "quotes": [...],
  "actions": [...]
}
```

### Add Quote for MP
```http
POST /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/quotes
Authorization: Bearer <token>
Content-Type: application/json

{
  "quote": "We will never compromise on Jerusalem",
  "context": "Speech at Knesset plenary session",
  "source_url": "https://knesset.gov.il/speech/123",
  "topic": "politics",
  "date": "2025-03-15"
}
```

### Add Action for MP
```http
POST /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/actions
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "Voted against Jerusalem status bill",
  "action_type": "vote",
  "topic": "politics",
  "source_url": "https://knesset.gov.il/vote/456",
  "date": "2025-04-20"
}
```

### Get MP Quotes
```http
GET /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/quotes
```

### Get MP Actions
```http
GET /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/actions
```

### Run Contradiction Scan
```http
POST /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/contradictions/scan
Authorization: Bearer <token>
```
**Response:**
```json
{
  "mp_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "new_contradictions_found": 1,
  "contradictions": [
    {
      "explanation": "Quote and action appear to contradict each other.",
      "severity": "medium",
      "topic": "politics",
      "detected_at": "2025-05-24T10:00:00"
    }
  ]
}
```

### Get Stored Contradictions
```http
GET /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/contradictions
```

### List All Parties
```http
GET /political/parties
```
**Response:**
```json
{
  "total": 12,
  "parties": [
    {"name": "Likud", "wing": "right", "seats": 32, "leader": "Netanyahu"},
    {"name": "Yesh Atid", "wing": "center", "seats": 24},
    {"name": "Haaretz", "wing": "left", "seats": 4}
  ]
}
```

### Get Party Detail
```http
GET /political/parties/64f1a2b3c4d5e6f7a8b9c0d2
```

### List Knesset Committees
```http
GET /political/committees
```

### Vote on a Bill (Referendum)
```http
POST /political/bills/64f1a2b3c4d5e6f7a8b9c0d3/vote
Authorization: Bearer <token>
Content-Type: application/json

{
  "support": true
}
```
**Response:**
```json
{
  "bill_id": "64f1a2b3c4d5e6f7a8b9c0d3",
  "your_vote": "support",
  "total_votes": 142,
  "support": 98,
  "oppose": 44,
  "support_pct": 69.0
}
```

### Get Bill Vote Tally
```http
GET /political/bills/64f1a2b3c4d5e6f7a8b9c0d3/tally
```

---

## 🐦 Social Media

### Search Twitter
```http
GET /social/twitter/search?query=Israel+economy&limit=10&israeli_only=true
```

### Get User Tweets
```http
GET /social/twitter/user/TimesofIsrael?limit=10
GET /social/twitter/user/KnessetIsrael?limit=5
```

### Get All Israeli Account Tweets
```http
GET /social/twitter/israeli-accounts?limit=5
```

---

## ❤️ Health

```http
GET /
GET /health
```

---

## 🔑 Notes

- **MongoDB IDs** — `_id` fields are 24-char hex strings like `64f1a2b3c4d5e6f7a8b9c0d1`
- **use_ai=true** — requires `OPENAI_API_KEY` in `.env`, otherwise falls back to rule-based
- **Authorization** — `Bearer <token>` header required for protected endpoints
- **Streaming** — `/qa/ask/stream` returns `text/event-stream`, read with EventSource or curl
- **Categories** — `economy`, `political`, `defence`, `education`, `community`, `sport`, `culture`, `environment`, `science`, `positive`, `international`, `knesset`
