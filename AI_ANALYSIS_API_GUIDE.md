# AI Analysis API Guide

এই ডকুমেন্ট সমস্ত AI Analysis endpoints এর বর্ণনা এবং sample inputs/outputs দিচ্ছে।

---

## 📊 API Overview

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/ai/analyze` | POST | একটি আর্টিকেল analyze করুন | Optional (tier based) |
| `/ai/analyze/batch` | POST | একসাথে 20টি পর্যন্ত আর্টিকেল | Optional (tier based) |
| `/ai/source-bias` | GET | একটি নিউজ সোর্সের bias পান | No |
| `/ai/source-bias/all` | GET | সমস্ত Israeli sources এর bias | No |
| `/ai/articles/{id}/vote/bias` | POST | একটি আর্টিকেলে bias vote করুন | Optional |
| `/ai/sources/{name}/vote/credibility` | POST | একটি সোর্সের credibility vote করুন | Optional |
| `/ai/articles/{id}/flag` | POST | একটি আর্টিকেল flag করুন (misinformation/propaganda) | Optional |
| `/ai/articles/{article_id}/votes` | GET | একটি আর্টিকেলের voting stats দেখুন | No |
| `/ai/sources/{source_name}/votes` | GET | একটি সোর্সের vote history দেখুন | No |
| `/ai/votes/{vote_id}/helpful` | POST | একটি vote কে helpful চিহ্নিত করুন | Optional |
| `/ai/user/{user_id}/vote-history` | GET | ব্যবহারকারীর vote history দেখুন | No |
| `/ai/votes/leaderboard` | GET | সেরা community voters দেখান | No |
| `/ai/articles/{article_id}/verify` | POST | একটি আর্টিকেল verify করুন | No |
| `/ai/verify/cross-source` | POST | batch cross-source verification চালান | No |
| `/ai/articles/{article_id}/cross-source` | GET | একটি আর্টিকেলের cross-source data দেখুন | No |
| `/ai/factcheck/search` | GET | published fact-check results search করুন | No |
| `/ai/articles/{article_id}/audit-trail` | GET | আর্টিকেলের analysis audit trail দেখুন | No |
| `/ai/sources/{source_name}/bias-history` | GET | সোর্সের bias trend history দেখুন | No |
| `/ai/sources/drifting` | GET | bias drifted sources তালিকা দেখুন | No |
| `/ai/articles/{article_id}/propaganda-check` | POST | একটি আর্টিকেল propaganda pattern চেক করুন | No |
| `/ai/propaganda/coordinated-narratives` | GET | coordinated narratives detect করুন | No |
| `/ai/sources/{source_name}/ownership` | GET | সোর্সের ownership data দেখুন | No |
| `/ai/sources/ownership/all` | GET | সকল সোর্সের ownership data দেখুন | No |

---

## 1️⃣ Single Article Analysis

### Endpoint
```
POST /ai/analyze?user_tier=free
```

### Description
একটি নিউজ আর্টিকেল analyze করে:
- **Sentiment**: positive / neutral / negative
- **Bias**: left / center / right / unknown
- **Bias Score**: 0.0 – 1.0
- **Credibility**: 0.0 – 1.0
- **Fact-Check Score**: 0.0 – 1.0
- **Topics**: extracted key topics
- **Claims**: মূল claims
- **Hebrew Summary**: 2-3 sentence summary

### User Tiers
- **`free`**: Rule-based analysis (instant, no API cost)
- **`pro`**: GPT-4o-mini powered (slower, higher quality)
- **`platinum`**: GPT-4o-mini + Perplexity + Gemini (ensemble)

### Request Body

```json
{
  "guid": "article-unique-id-123",
  "title": "Netanyahu announces new economic reforms amid inflation crisis",
  "description": "Prime Minister Benjamin Netanyahu unveiled a sweeping economic package today, promising to tackle Israel's rising cost of living. The plan includes tax cuts for businesses and subsidies for essential commodities. Critics argue the measures favor corporations over ordinary citizens.",
  "source": "Times of Israel",
  "source_url": "https://www.timesofisrael.com"
}
```

### Response (200 OK)

```json
{
  "guid": "article-unique-id-123",
  "sentiment": "neutral",
  "bias": "center",
  "bias_score": 0.35,
  "bias_types": [
    "loaded language",
    "cherry-picking"
  ],
  "bias_category": "Balanced Reporting with Minor Framing",
  "bias_score_explanation": "The article presents the PM's announcement objectively while including opposition criticism. Slight framing toward business interests.",
  "credibility_score": 0.82,
  "credibility_label": "likely credible",
  "fact_check_score": 0.78,
  "summary_hebrew": "ראש הממשלה נתניהו הכריז על חבילת רפורמה כלכלית שמטרתה להילחם בעלייה בעלות המחיה. התוכנית כוללת הנחות מסים לעסקים וסובסידיות לסחורות חיוניות. מבקרים טוענים שהאמצעים מעדיפים תאגידים על פני אזרחים רגילים.",
  "topics": [
    "economics",
    "politics",
    "government policy",
    "inflation"
  ],
  "claims": [
    "Netanyahu announces new economic reforms",
    "Plan includes tax cuts and subsidies"
  ],
  "factual_points": [
    "PM announced economic package today",
    "Plan targets rising cost of living",
    "Includes tax cuts and commodity subsidies"
  ],
  "claim_explanation": "The headline is an accurate summary of the article's main topic.",
  "bias_explanation": "The article balances government announcements with opposition viewpoints, maintaining relatively neutral coverage."
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/analyze?user_tier=pro" \
  -H "Content-Type: application/json" \
  -d '{
    "guid": "article-123",
    "title": "Netanyahu announces new economic reforms amid inflation crisis",
    "description": "Prime Minister Benjamin Netanyahu unveiled a sweeping economic package...",
    "source": "Times of Israel",
    "source_url": "https://www.timesofisrael.com"
  }'
```

---

## 2️⃣ Batch Article Analysis

### Endpoint
```
POST /ai/analyze/batch?user_tier=platinum
```

### Description
একসাথে সর্বোচ্চ 20টি আর্টিকেল analyze করুন। প্রতিটি আর্টিকেলের জন্য একই analysis return হয়।

### Request Body

```json
{
  "articles": [
    {
      "guid": "article-1",
      "title": "Israeli tech exports surge by 12%",
      "description": "Israel's high-tech sector reported record exports this quarter...",
      "source": "Globes",
      "source_url": "https://www.globes.co.il"
    },
    {
      "guid": "article-2",
      "title": "Palestinian Authority condemns new settlement expansion",
      "description": "The Palestinian Authority issued a statement today condemning Israel's expansion...",
      "source": "Ma'an News",
      "source_url": "https://www.maannews.net"
    },
    {
      "guid": "article-3",
      "title": "Supreme Court rules on judicial reform case",
      "description": "Israel's Supreme Court delivered a landmark decision on the government's judicial reform bill...",
      "source": "Haaretz",
      "source_url": "https://www.haaretz.com"
    }
  ]
}
```

### Response (200 OK)

```json
[
  {
    "guid": "article-1",
    "sentiment": "positive",
    "bias": "center",
    "bias_score": 0.15,
    "bias_types": ["source leaning"],
    "bias_category": "Objective Reporting",
    "bias_score_explanation": "Economic news reported factually.",
    "credibility_score": 0.80,
    "credibility_label": "likely credible",
    "fact_check_score": 0.85,
    "summary_hebrew": "ישראל דיווחה על עלייה של 12% בייצוא ההיי-טק...",
    "topics": ["economy", "technology", "business"],
    "claims": ["Israeli tech exports surge by 12%"],
    "factual_points": ["Record exports reported this quarter"],
    "claim_explanation": "...",
    "bias_explanation": "..."
  },
  {
    "guid": "article-2",
    "sentiment": "negative",
    "bias": "left",
    "bias_score": 0.65,
    "bias_types": ["loaded language", "framing"],
    "bias_category": "Partisan Framing",
    "bias_score_explanation": "Uses charged language regarding settlements.",
    "credibility_score": 0.60,
    "credibility_label": "needs review",
    "fact_check_score": 0.55,
    "summary_hebrew": "הרשות הפלסטינית הוציאה הצהרה גנאי על התרחבות ההתנחלויות של ישראל...",
    "topics": ["politics", "Palestinian affairs", "settlements"],
    "claims": ["Palestinian Authority condemns settlement expansion"],
    "factual_points": ["PA issued a statement", "Related to settlement expansion"],
    "claim_explanation": "...",
    "bias_explanation": "..."
  },
  {
    "guid": "article-3",
    "sentiment": "neutral",
    "bias": "center",
    "bias_score": 0.20,
    "bias_types": ["source leaning"],
    "bias_category": "Objective Reporting",
    "bias_score_explanation": "Court decisions reported neutrally.",
    "credibility_score": 0.85,
    "credibility_label": "likely credible",
    "fact_check_score": 0.90,
    "summary_hebrew": "בית המשפט העליון הוציא החלטה הנוגעת לחוק ההשתנות המשפטית...",
    "topics": ["law", "politics", "government"],
    "claims": ["Supreme Court rules on judicial reform"],
    "factual_points": ["Court issued landmark decision"],
    "claim_explanation": "...",
    "bias_explanation": "..."
  }
]
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/analyze/batch?user_tier=platinum" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {"guid": "1", "title": "Article 1", "description": "...", "source": "Globes"},
      {"guid": "2", "title": "Article 2", "description": "...", "source": "Haaretz"}
    ]
  }'
```

---

## 3️⃣ Get Source Bias

### Endpoint
```
GET /ai/source-bias?source=Haaretz&source_url=https://www.haaretz.com
```

### Description
একটি নিউজ সোর্সের প্রি-configured bias এবং credibility পান।

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | Source name (e.g., "Haaretz", "Times of Israel") |
| `source_url` | string | No | Source website URL |

### Response (200 OK)

```json
{
  "source_name": "Haaretz",
  "bias": "left",
  "credibility_score": 0.85,
  "bias_label": "⬅️ Left",
  "report_count": 245
}
```

### More Examples

```bash
# Example 1: Times of Israel
curl "http://localhost:8000/ai/source-bias?source=Times%20of%20Israel"

# Response:
{
  "source_name": "Times of Israel",
  "bias": "center",
  "credibility_score": 0.82,
  "bias_label": "⚖️ Center",
  "report_count": 189
}

# Example 2: Arutz Sheva
curl "http://localhost:8000/ai/source-bias?source=Arutz%20Sheva"

# Response:
{
  "source_name": "Arutz Sheva",
  "bias": "right",
  "credibility_score": 0.62,
  "bias_label": "➡️ Right",
  "report_count": 78
}
```

---

## 4️⃣ Get All Israeli Sources Bias

### Endpoint
```
GET /ai/source-bias/all
```

### Description
সমস্ত configured Israeli news sources এর bias এবং credibility রেটিং।

### Response (200 OK)

```json
{
  "total": 30,
  "sources": [
    {
      "source_name": "+972 Magazine",
      "bias": "left",
      "credibility_score": 0.70,
      "bias_label": "⬅️ Left"
    },
    {
      "source_name": "Arutz Sheva",
      "bias": "right",
      "credibility_score": 0.62,
      "bias_label": "➡️ Right"
    },
    {
      "source_name": "Channel 12 (Mako)",
      "bias": "center",
      "credibility_score": 0.82,
      "bias_label": "⚖️ Center"
    },
    {
      "source_name": "Channel 13 (Reshet)",
      "bias": "center",
      "credibility_score": 0.80,
      "bias_label": "⚖️ Center"
    },
    {
      "source_name": "Globes",
      "bias": "center",
      "credibility_score": 0.80,
      "bias_label": "⚖️ Center"
    },
    {
      "source_name": "Haaretz",
      "bias": "left",
      "credibility_score": 0.85,
      "bias_label": "⬅️ Left"
    },
    {
      "source_name": "Israel Hayom",
      "bias": "right",
      "credibility_score": 0.68,
      "bias_label": "➡️ Right"
    },
    {
      "source_name": "Jerusalem Post",
      "bias": "center-right",
      "credibility_score": 0.78,
      "bias_label": "➡️ Right"
    },
    {
      "source_name": "Kan News",
      "bias": "center",
      "credibility_score": 0.88,
      "bias_label": "⚖️ Center"
    },
    {
      "source_name": "Times of Israel",
      "bias": "center",
      "credibility_score": 0.82,
      "bias_label": "⚖️ Center"
    },
    {
      "source_name": "Ynet News",
      "bias": "center",
      "credibility_score": 0.75,
      "bias_label": "⚖️ Center"
    }
  ]
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/source-bias/all"
```

---

## 5️⃣ Submit Bias Vote (Crowdsourced)

### Endpoint
```
POST /ai/articles/{article_id}/vote/bias
```

### Description
একটি আর্টিকেলের bias assessment এ vote করুন। এটি crowdsourced bias detection এর জন্য ব্যবহার হয়।

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `article_id` | string | Yes | অনন্য আর্টিকেল ID |
| `user_id` | query string | Yes | আপনার user ID (JWT থেকে) |
| `user_tier` | query string | No | free / pro / platinum (default: free) |

### Request Body

```json
{
  "bias_assessment": "left",
  "confidence": 0.85,
  "user_notes": "The article uses very loaded language when discussing the Palestinian Authority."
}
```

### Valid Bias Values
```
"far-left", "left", "center-left", "center",
"center-right", "right", "far-right", "unclear"
```

### Response (200 OK)

```json
{
  "status": "recorded",
  "vote_id": "vote-uuid-12345",
  "article_id": "article-guid-789",
  "recorded_at": "2026-06-20T10:30:45.123Z",
  "new_consensus": {
    "bias": "left",
    "consensus_percentage": 62.5,
    "total_votes": 16,
    "breakdown": {
      "left": 10,
      "center-left": 3,
      "center": 2,
      "right": 1
    }
  }
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/articles/article-guid-789/vote/bias?user_id=user-123&user_tier=pro" \
  -H "Content-Type: application/json" \
  -d '{
    "bias_assessment": "left",
    "confidence": 0.85,
    "user_notes": "Loaded language against Palestinian Authority"
  }'
```

---

## 6️⃣ Submit Credibility Vote (Source Rating)

### Endpoint
```
POST /ai/sources/{source_name}/vote/credibility
```

### Description
একটি নিউজ সোর্সের overall credibility এ vote করুন।

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_name` | string | Yes | Source name (e.g., "Haaretz", "Times of Israel") |
| `user_id` | query string | Yes | আপনার user ID |
| `user_tier` | query string | No | free / pro / platinum |

### Request Body

```json
{
  "credibility_level": "high",
  "evidence": "Haaretz consistently fact-checks its reporting and issues corrections. Their investigative journalism has exposed multiple scandals."
}
```

### Valid Credibility Levels
```
"very_low", "low", "medium", "high", "very_high"
```

### Response (200 OK)

```json
{
  "status": "recorded",
  "vote_id": "credibility-vote-uuid",
  "source_name": "Haaretz",
  "recorded_at": "2026-06-20T10:35:22.456Z",
  "updated_credibility": {
    "average_credibility_score": 0.84,
    "total_votes": 127,
    "breakdown": {
      "very_low": 2,
      "low": 4,
      "medium": 15,
      "high": 68,
      "very_high": 38
    }
  }
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/sources/Haaretz/vote/credibility?user_id=user-456&user_tier=pro" \
  -H "Content-Type: application/json" \
  -d '{
    "credibility_level": "high",
    "evidence": "Consistently fact-checks and issues corrections"
  }'
```

---

## 7️⃣ Flag Article

### Endpoint
```
POST /ai/articles/{article_id}/flag
```

### Description
একটি আর্টিকেল misinformation, propaganda, bias, বা unreliable source এর জন্য flag করুন। এটি moderators এর attention এ যাবে।

### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `article_id` | string | Yes | অনন্য আর্টিকেল ID |
| `user_id` | query string | Yes | আপনার user ID |

### Request Body

```json
{
  "reason": "misinformation",
  "details": "The article claims that the government announced a ban on imports, but the official government website shows no such announcement. The headline is misleading."
}
```

### Valid Reasons
```
"misinformation" — article contains false information
"propaganda" — article is designed to manipulate public opinion
"biased" — article shows strong bias without balancing views
"unreliable_source" — source has poor track record for accuracy
```

### Response (200 OK)

```json
{
  "status": "flagged",
  "flag_id": "flag-uuid-abcde",
  "article_id": "article-guid-789",
  "reason": "misinformation",
  "flagged_at": "2026-06-20T10:40:15.789Z",
  "review_status": "pending_moderation",
  "message": "Your flag has been submitted and will be reviewed by our moderation team."
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/articles/article-guid-789/flag?user_id=user-789" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "misinformation",
    "details": "Article claims government ban that does not exist on official website"
  }'
```

---

## 8️⃣ Article Vote Statistics

### Endpoint
```
GET /ai/articles/{article_id}/votes
```

### Description
একটি আর্টিকেলের bias votes, flags, এবং votes summary পান।

### Response (200 OK)

```json
{
  "article_id": "article-guid-789",
  "bias_votes_count": 12,
  "flags_count": 3,
  "votes": {
    "bias_votes": [
      {
        "article_id": "article-guid-789",
        "user_tier": "pro",
        "bias_assessment": "left",
        "confidence": 0.9,
        "user_notes": "Loaded language detected.",
        "created_at": "2026-06-20T10:30:45.123Z",
        "updated_at": "2026-06-20T10:30:45.123Z",
        "helpful_count": 2
      }
    ],
    "flag_count": 3,
    "flags_by_reason": {
      "misinformation": 2,
      "biased": 1
    }
  }
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/articles/article-guid-789/votes"
```

---

## 9️⃣ Source Vote Statistics

### Endpoint
```
GET /ai/sources/{source_name}/votes
```

### Description
একটি সোর্সের credibility vote breakdown এবং total votes দেখুন।

### Response (200 OK)

```json
{
  "source_name": "Haaretz",
  "votes": {
    "credibility_votes": [
      {
        "source_name": "Haaretz",
        "user_tier": "free",
        "credibility_level": "high",
        "credibility_score": 0.8,
        "evidence": "Consistent fact-checking.",
        "created_at": "2026-06-19T15:22:11.000Z",
        "updated_at": "2026-06-19T15:22:11.000Z",
        "helpful_count": 1
      }
    ],
    "total_votes": 42
  }
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/sources/Haaretz/votes"
```

---

## 🔟 Mark Vote Helpful

### Endpoint
```
POST /ai/votes/{vote_id}/helpful?vote_type=bias
```

### Description
একটি bias অথবা credibility vote কে helpful হিসেবে চিহ্নিত করুন।

### Request
No body needed.

### Response (200 OK)

```json
{
  "status": "upvoted",
  "vote_id": "64f1a2b3c4d5e6f7a8b9c0d1"
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/votes/64f1a2b3c4d5e6f7a8b9c0d1/helpful?vote_type=bias"
```

---

## 1️⃣1️⃣ User Vote History

### Endpoint
```
GET /ai/user/{user_id}/vote-history?limit=10
```

### Description
ব্যবহারকারীর recent voting history এবং participation stats দেখুন।

### Response (200 OK)

```json
{
  "user_id": "usr-555",
  "reputation": {
    "bias_votes": 24,
    "credibility_votes": 10,
    "flags_submitted": 3
  },
  "recent_activity": {
    "bias_votes": [
      {
        "article_id": "article-guid-789",
        "bias_assessment": "left",
        "confidence": 0.85,
        "created_at": "2026-06-20T10:30:45.123Z"
      }
    ],
    "credibility_votes": [
      {
        "source_name": "Haaretz",
        "credibility_level": "high",
        "created_at": "2026-06-19T15:22:11.000Z"
      }
    ],
    "flags": [
      {
        "article_id": "article-guid-101",
        "reason": "biased",
        "created_at": "2026-06-18T12:00:00.000Z"
      }
    ]
  }
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/user/usr-555/vote-history?limit=10"
```

---

## 1️⃣2️⃣ Votes Leaderboard

### Endpoint
```
GET /ai/votes/leaderboard?limit=10
```

### Description
Top community voters ranked by helpful votes received.

### Response (200 OK)

```json
{
  "leaderboard": [
    {
      "_id": "usr-999",
      "total_votes": 150,
      "helpful_votes": 340
    }
  ],
  "description": "Top voters by helpful votes received"
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/votes/leaderboard?limit=10"
```

---

## 1️⃣3️⃣ Verify Article

### Endpoint
```
POST /ai/articles/{article_id}/verify?title=...&description=...
```

### Description
Run a verification pipeline on an article:
- verified claims extraction
- framing analysis
- cross-source match lookup
- composite verification confidence

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Article title |
| `description` | string | No | Article body text |

### Response (200 OK)

```json
{
  "article_id": "article-guid-789",
  "verified_claims": [
    {
      "claim_text": "Government announced new tax cuts",
      "verification_status": "verified",
      "evidence_sources": ["official press release"],
      "confidence": 0.85,
      "explanation": "Confirmed by the government statement and budget papers."
    }
  ],
  "framing_analysis": {
    "headline_body_consistency": 0.9,
    "attribution_count": 2,
    "perspective_balance": "balanced",
    "narrative_frame": "economic",
    "voice_analysis": "mixed",
    "omission_signals": []
  },
  "cross_source_match": null,
  "verification_confidence": {
    "overall_score": 0.72,
    "components": {
      "source_credibility": 0.82,
      "cross_source_agreement": 0.0,
      "claims_verification": 0.75,
      "framing": 0.60
    },
    "label": "needs review",
    "explanation": "Limited cross-source confirmation, moderate claim support."
  }
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/articles/article-guid-789/verify?title=Test%20Title&description=Test%20body"
```

---

## 1️⃣4️⃣ Cross-Source Verification Batch

### Endpoint
```
POST /ai/verify/cross-source
```

### Description
Run cross-source verification on a batch of articles and group related stories.

### Request Body
```json
{
  "articles": [
    {
      "guid": "article-1",
      "title": "Israel announces new settlement policy",
      "description": "The government said...",
      "source": "Haaretz"
    },
    {
      "guid": "article-2",
      "title": "New settlement policy announced by Israeli government",
      "description": "Officials confirmed...",
      "source": "Israel Hayom"
    }
  ]
}
```

### Response (200 OK)

```json
{
  "total_articles": 2,
  "clusters_found": 1,
  "clusters": [
    {
      "event_cluster_id": "evt-12345",
      "matching_articles": [
        {"source": "Haaretz", "title": "Israel announces new settlement policy", "bias": "left", "guid": "article-1"},
        {"source": "Israel Hayom", "title": "New settlement policy announced by Israeli government", "bias": "right", "guid": "article-2"}
      ],
      "source_count": 2,
      "agreement_score": 0.78,
      "divergences": ["Covered by sources across the spectrum: left, right"],
      "consensus_framing": "Most sources frame this as neutral"
    }
  ]
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/verify/cross-source" \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {"guid": "article-1", "title": "...", "description": "...", "source": "Haaretz"},
      {"guid": "article-2", "title": "...", "description": "...", "source": "Israel Hayom"}
    ]
  }'
```

---

## 1️⃣5️⃣ Get Article Cross-Source Data

### Endpoint
```
GET /ai/articles/{article_id}/cross-source
```

### Description
Retrieve cross-source verification for a specific article, if available.

### Response Options

#### When found
```json
{
  "article_id": "article-guid-789",
  "status": "verified",
  "cross_source": {
    "event_cluster_id": "evt-12345",
    "matching_articles": [
      {"source": "Haaretz", "title": "...", "bias": "left", "guid": "article-1"},
      {"source": "Israel Hayom", "title": "...", "bias": "right", "guid": "article-2"}
    ],
    "source_count": 2,
    "agreement_score": 0.78,
    "divergences": ["Covered by sources across the spectrum: left, right"],
    "consensus_framing": "Most sources frame this as neutral"
  }
}
```

#### When not available
```json
{
  "article_id": "article-guid-789",
  "status": "no_cross_source_data",
  "message": "No cross-source verification available for this article yet."
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/articles/article-guid-789/cross-source"
```

---

## 1️⃣6️⃣ Factcheck Search

### Endpoint
```
GET /ai/factcheck/search?query=Netanyahu%20settlement%20claims
```

### Description
Search the Google Fact Check API for published fact-checks related to a claim or topic.

### Response (200 OK)

```json
{
  "query": "Netanyahu settlement claims",
  "results_count": 2,
  "fact_checks": [
    {
      "title": "Fact check: settlement claims",
      "url": "https://factcheck.org/article",
      "publisher": "FactCheck.org",
      "published_date": "2026-06-19",
      "claim": "Netanyahu announced a settlement freeze",
      "rating": "false"
    }
  ],
  "note": "Results from published fact-checkers via Google Fact Check Tools API."
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/factcheck/search?query=Netanyahu%20settlement%20claims"
```

---

## 1️⃣7️⃣ Article Audit Trail

### Endpoint
```
GET /ai/articles/{article_id}/audit-trail
```

### Description
Get transparency logs for an article's AI analysis.

### Response (200 OK)

```json
{
  "article_id": "article-guid-789",
  "audit_entries": [
    {
      "article_id": "article-guid-789",
      "timestamp": "2026-06-20T10:32:00.000Z",
      "models_used": ["gpt-4o-mini", "rule-based"],
      "user_vote_count": 0,
      "analysis_tier": "pro",
      "final_bias": "center",
      "final_credibility": 0.82,
      "consensus_source": "ai"
    }
  ],
  "total_entries": 1
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/articles/article-guid-789/audit-trail"
```

---

## 1️⃣8️⃣ Source Bias History

### Endpoint
```
GET /ai/sources/{source_name}/bias-history?days=90
```

### Description
Get a bias trend report for a source, including moving averages and drift detection.

### Response (200 OK)

```json
{
  "source_name": "Haaretz",
  "data_points": 120,
  "period_days": 90,
  "averages": {
    "7_day": {
      "period_days": 7,
      "data_points": 12,
      "avg_bias_numeric": -1.2,
      "avg_bias_label": "left",
      "avg_bias_score": 0.76,
      "avg_credibility": 0.82
    },
    "30_day": {
      "period_days": 30,
      "data_points": 42,
      "avg_bias_numeric": -0.95,
      "avg_bias_label": "center-left",
      "avg_bias_score": 0.74,
      "avg_credibility": 0.81
    },
    "90_day": {
      "period_days": 90,
      "data_points": 120,
      "avg_bias_numeric": -0.80,
      "avg_bias_label": "center-left",
      "avg_bias_score": 0.73,
      "avg_credibility": 0.80
    }
  },
  "drift": {
    "detected": true,
    "magnitude": -0.4,
    "direction": "shifting_left",
    "explanation": "No significant bias shift detected."
  },
  "label_distribution": {
    "left": 80,
    "center-left": 30,
    "center": 10
  }
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/sources/Haaretz/bias-history?days=90"
```

---

## 1️⃣9️⃣ Drifting Sources

### Endpoint
```
GET /ai/sources/drifting
```

### Description
List sources whose bias has shifted significantly over the last 90 days.

### Response (200 OK)

```json
{
  "drifting_sources": [
    {
      "source_name": "Israel Hayom",
      "drift_magnitude": 0.65,
      "direction": "shifting_right",
      "data_points": 95
    }
  ],
  "total": 1,
  "description": "Sources whose bias has shifted significantly in the last 90 days."
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/sources/drifting"
```

---

## 2️⃣0️⃣ Propaganda Check

### Endpoint
```
POST /ai/articles/{article_id}/propaganda-check?title=...&description=...&auto_flag=true
```

### Description
Analyze an article for propaganda patterns and optionally auto-flag it when severity is medium/high.

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Article title |
| `description` | string | No | Article body text |
| `auto_flag` | bool | No | Automatically flag on medium/high severity |

### Response (200 OK)

```json
{
  "article_id": "article-guid-789",
  "is_flagged": true,
  "signals": [
    {
      "type": "conspiracy_language",
      "matches": ["deep state"],
      "severity": "high"
    },
    {
      "type": "excessive_punctuation",
      "severity": "low",
      "detail": "5 exclamation marks detected."
    }
  ],
  "signal_count": 2,
  "severity": "high",
  "explanation": "Detected 2 propaganda signal(s): conspiracy language, excessive punctuation. Overall severity: high.",
  "auto_flagged": true
}
```

### Curl Example
```bash
curl -X POST "http://localhost:8000/ai/articles/article-guid-789/propaganda-check?title=Shocking%20News&description=...&auto_flag=true"
```

---

## 2️⃣1️⃣ Coordinated Narratives

### Endpoint
```
GET /ai/propaganda/coordinated-narratives?hours=2&min_sources=4
```

### Description
Detect coordinated narrative patterns across multiple sources within a short window.

### Response (200 OK)

```json
{
  "time_window_hours": 2,
  "min_sources": 4,
  "narratives_found": 1,
  "narratives": [
    {
      "narrative_key": "netanyahu israel settlement",
      "source_count": 5,
      "sources": ["Haaretz", "Israel Hayom", "Ynet News", "Channel 12 (Mako)", "Times of Israel"],
      "sample_titles": [
        "Israel announces new settlement plan",
        "Netanyahu unveils fresh settlement policy"
      ],
      "article_count": 6,
      "time_window_hours": 2,
      "assessment": "possibly_coordinated"
    }
  ]
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/propaganda/coordinated-narratives?hours=2&min_sources=4"
```

---

## 2️⃣2️⃣ Source Ownership

### Endpoint
```
GET /ai/sources/{source_name}/ownership
```

### Description
Get ownership, funding, and transparency data for a single source.

### Response (200 OK)

```json
{
  "source_name": "Haaretz",
  "ownership": "Haaretz Group (Schocken family, ~25% + DuMont Schauberg)",
  "funding_model": "Subscription + advertising",
  "notable_affiliations": "Center-left editorial line, owned by Schocken family since 1937",
  "transparency_score": 0.8,
  "press_freedom_note": "Considered Israel's newspaper of record for liberal readership"
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/sources/Haaretz/ownership"
```

---

## 2️⃣3️⃣ All Source Ownership

### Endpoint
```
GET /ai/sources/ownership/all
```

### Description
Get ownership and transparency data for all sources with recorded ownership metadata.

### Response (200 OK)

```json
{
  "total": 5,
  "sources": [
    {
      "source_name": "Haaretz",
      "ownership": "Haaretz Group (Schocken family, ~25% + DuMont Schauberg)",
      "funding_model": "Subscription + advertising",
      "notable_affiliations": "Center-left editorial line, owned by Schocken family since 1937",
      "transparency_score": 0.8,
      "press_freedom_note": "Considered Israel's newspaper of record for liberal readership"
    }
  ]
}
```

### Curl Example
```bash
curl "http://localhost:8000/ai/sources/ownership/all"
```

---

## 📈 Response Schemas

### ArticleAnalysis (Full Response)

```typescript
{
  guid: string                  // Unique article ID
  sentiment: string             // "positive" | "neutral" | "negative"
  bias: string                  // "left" | "center" | "right" | "unknown"
  bias_score: float (0.0-1.0)   // Strength of bias
  bias_types: string[]          // ["loaded language", "framing", "cherry-picking", etc.]
  bias_category: string         // Human-readable category
  bias_score_explanation: string // Why this bias was detected
  credibility_score: float      // 0.0-1.0
  credibility_label: string     // "verified" | "likely credible" | "needs review" | "unverified"
  fact_check_score: float       // 0.0-1.0 (how many facts verified)
  summary_hebrew: string        // 2-3 sentence Hebrew summary
  topics: string[]              // ["economy", "politics", "technology", etc.]
  claims: string[]              // Main claims in article
  factual_points: string[]      // Verified facts
  claim_explanation: string     // How claims differ from facts
  bias_explanation: string      // Detailed explanation of bias
}
```

---

## 🔑 Key Concepts

### Bias Spectrum (Israeli Context)
- **far-left** — strongly anti-government, anti-occupation
- **left** — progressive, critical of government/occupation
- **center-left** — moderate progressive
- **center** — balanced, objective reporting
- **center-right** — moderate conservative
- **right** — conservative, pro-government
- **far-right** — strongly pro-government, nationalist

### Credibility Score Ranges
- **0.0-0.3** — very_low (unreliable, sensationalist)
- **0.3-0.5** — low (some bias, occasional errors)
- **0.5-0.7** — medium (mixed record, some credible content)
- **0.7-0.85** — high (generally reliable, well-researched)
- **0.85-1.0** — very_high (trusted sources, strict editorial standards)

### Bias Types
- **loaded language** — emotional, charged words
- **framing** — selective presentation of context
- **cherry-picking** — selecting only supporting facts
- **source leaning** — inherent bias of the news outlet
- **speculative reporting** — presenting unverified claims as fact
- **context omission** — missing important background

---

## 💡 Usage Tips

1. **Free tier** (rule-based) is instant but less accurate
2. **Pro tier** uses OpenAI GPT-4o-mini, more accurate but slower
3. **Platinum tier** uses ensemble (GPT-4o + Perplexity + Gemini) for best accuracy
4. Use **batch endpoint** for analyzing many articles efficiently
5. User votes are **crowdsourced credibility** validation — community consensus can override AI scores
6. Always check **credibility_label** — if "needs review", verify before sharing

---

## 🚫 Error Examples

### 400 Bad Request — Invalid bias assessment
```json
{
  "detail": "bias_assessment must be one of: far-left, left, center-left, center, center-right, right, far-right, unclear"
}
```

### 400 Bad Request — Batch size exceeded
```json
{
  "detail": "Max 20 articles per batch"
}
```

### 422 Unprocessable Entity — Missing required field
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "title"],
      "msg": "Field required"
    }
  ]
}
```

---

Generated: 2026-06-20
