# User Voting Mechanism — Implementation Guide

## Overview

**Problem**: How do you validate AI analysis + detect misinformation at scale?  
**Solution**: Crowdsourced voting with smart consensus algorithms.

Your platform now enables users to validate AI bias/credibility assessments, creating a **trusted community standard** for news quality.

---

## Features Implemented

### 1. Bias Voting

Users assess article bias: **left → center → right → unclear**

```python
POST /ai/articles/{article_id}/vote/bias
{
  "bias_assessment": "left",
  "confidence": 0.85,              # How sure are you?
  "user_notes": "Loaded language" 
}
```

**Consensus Algorithm**:
- Votes weighted by user tier (Free=1x, Pro=1.5x, Platinum=2x)
- **<5 votes** → trust AI assessment
- **≥5 votes** → use weighted majority vote
- Final confidence = % agreement among voters

### 2. Credibility Voting

Users rate source reliability: **very_low → low → medium → high → very_high**

```python
POST /ai/sources/{source_name}/vote/credibility
{
  "credibility_level": "high",
  "evidence": "Fact-checks thoroughly, corrects errors"
}
```

**Consensus Algorithm**:
- Each level converts to score: very_low=0.1, low=0.3, medium=0.5, high=0.8, very_high=0.95
- Weighted average across votes (by tier)
- **<5 votes** → trust AI score
- **≥5 votes** → use weighted average
- Converts back to label: verified (≥0.85) | likely credible (≥0.70) | needs review (≥0.50) | unverified

### 3. Article Flagging

Users report misinformation, propaganda, bias, unreliable sources:

```python
POST /ai/articles/{article_id}/flag
{
  "reason": "misinformation",
  "details": "Falsely claims Israeli GDP declined 5%. Actually grew 2%."
}
```

Flags go to moderation queue for review.

### 4. Reputation System

- Votes receive upvotes from other users: `POST /ai/votes/{vote_id}/helpful`
- Top voters appear on leaderboard: `GET /ai/votes/leaderboard`
- Encourages quality participation from expert users

---

## API Reference

### Bias Voting

#### Submit Vote
```
POST /ai/articles/{article_id}/vote/bias
Query params:
  - user_id: str (from JWT)
  - user_tier: str (free|pro|platinum)

Body:
{
  "bias_assessment": "left|center|right|unclear",
  "confidence": 0.0-1.0,
  "user_notes": "optional explanation"
}

Response: { status, vote_id, article_id, recorded_at }
```

#### View Votes
```
GET /ai/articles/{article_id}/votes

Response: {
  "bias_votes_count": 12,
  "flags_count": 2,
  "votes": {
    "bias_votes": [...breakdown by assessment...],
    "flags_by_reason": {...}
  }
}
```

### Credibility Voting

#### Submit Vote
```
POST /ai/sources/{source_name}/vote/credibility
Query params:
  - user_id: str
  - user_tier: str (free|pro|platinum)

Body:
{
  "credibility_level": "very_low|low|medium|high|very_high",
  "evidence": "optional explanation"
}

Response: { status, vote_id, source_name, recorded_at }
```

#### View Votes
```
GET /ai/sources/{source_name}/votes

Response: {
  "source_name": "Haaretz",
  "votes": {
    "credibility_votes": [...breakdown...],
    "total_votes": 47
  }
}
```

### Article Flagging

```
POST /ai/articles/{article_id}/flag
Query params:
  - user_id: str

Body:
{
  "reason": "misinformation|propaganda|biased|unreliable_source",
  "details": "explain your concern"
}

Response: { status, flag_id, article_id, reason, message }
```

### Reputation & Leaderboard

#### User History
```
GET /ai/user/{user_id}/vote-history?limit=50

Response: {
  "reputation": {
    "bias_votes": 15,
    "credibility_votes": 8,
    "flags_submitted": 3
  },
  "recent_activity": {...}
}
```

#### Top Voters
```
GET /ai/votes/leaderboard?limit=10

Response: {
  "leaderboard": [
    {
      "_id": "user-123",
      "total_votes": 287,
      "helpful_votes": 445
    }
  ]
}
```

#### Mark Helpful
```
POST /ai/votes/{vote_id}/helpful?vote_type=bias|credibility

Response: { status: "upvoted", vote_id }
```

---

## Database Schema

### bias_votes collection
```javascript
{
  _id: ObjectId,
  article_id: String,
  user_id: String,
  user_tier: String,           // free|pro|platinum
  bias_assessment: String,      // left|center|right|unclear
  confidence: Number,           // 0.0-1.0
  user_notes: String,
  created_at: Date,
  helpful_count: Number         // upvotes from other users
}

Indexes:
  - { article_id: 1 }
  - { user_id: 1 }
  - { created_at: -1 }
  - { helpful_count: -1 }
```

### credibility_votes collection
```javascript
{
  _id: ObjectId,
  source_name: String,
  user_id: String,
  user_tier: String,           // free|pro|platinum
  credibility_level: String,   // very_low|low|medium|high|very_high
  credibility_score: Number,   // 0.1|0.3|0.5|0.8|0.95
  evidence: String,
  created_at: Date,
  helpful_count: Number
}

Indexes:
  - { source_name: 1 }
  - { user_id: 1 }
  - { created_at: -1 }
  - { helpful_count: -1 }
```

### article_flags collection
```javascript
{
  _id: ObjectId,
  article_id: String,
  user_id: String,
  reason: String,              // misinformation|propaganda|biased|unreliable_source
  details: String,
  created_at: Date,
  status: String               // pending|reviewed|addressed
}

Indexes:
  - { article_id: 1 }
  - { user_id: 1 }
  - { reason: 1 }
  - { status: 1 }
  - { created_at: -1 }
```

---

## Integration Points

### In ArticleAnalysis Response

When fetching analyzed articles, include voting data:

```python
# app/services/news_service.py

async def fetch_news(...) -> NewsResponse:
    ...
    for article in news.articles:
        analysis = await analyze_article(...)
        article.sentiment = analysis.sentiment
        article.bias = analysis.bias
        
        # NEW: Include voting consensus
        bias_consensus = await compute_bias_consensus(
            article.guid, 
            analysis.bias
        )
        article.bias = bias_consensus.bias
        article.bias_confidence = bias_consensus.confidence
        article.bias_based_on = bias_consensus.based_on  # "ai" or "user_consensus"
```

### Update ArticleAnalysis Schema

```python
# app/models/schemas.py

class NewsArticle(BaseModel):
    # ... existing fields ...
    
    # NEW: Voting fields
    bias_based_on: Optional[str] = None          # "ai" | "user_consensus"
    bias_confidence: Optional[float] = None       # combined confidence
    credibility_based_on: Optional[str] = None
    credibility_confidence: Optional[float] = None
    community_flags_count: Optional[int] = None
```

---

## Business Logic: Tier Weighting

Why different tiers?

| Tier | Weight | Use Case |
|------|--------|----------|
| **Free** | 1.0x | General public (learning bias detection) |
| **Pro** | 1.5x | Engaged users (journalists, researchers) |
| **Platinum** | 2.0x | Experts (fact-checkers, editors) |

**Example**: If 3 Pro users vote "left" and 2 Free users vote "center":
- Weighted: (1.5 × 1 × 3) + (1.0 × 1 × 2) = 4.5 + 2 = 6.5 for left
- Left consensus wins with 56% confidence

This ensures expert opinions shape consensus while maintaining broad participation.

---

## Quality Control Features

### Moderation Queue

Flagged articles automatically enter review:

```python
# Future: Add moderation dashboard
GET /admin/flags?status=pending
POST /admin/flags/{flag_id}/review
{
  "decision": "verified|false_positive",
  "moderator_notes": "Article was accurate, user misunderstood data"
}
```

### Vote Patterns

Detect and suppress spam voting:

```python
# Future: Voting abuse detection
- Same user voting on 100 articles in 5 minutes → flag
- User voting opposite to their historical pattern → flag
- Coordinated voting from same IP range → flag
```

### Helpful Vote Weighting

Only upvotes from verified users count heavily:

```python
# helpful_count is weighted by who upvoted
helpful_count = sum(
  1.5 if upvoter_tier == "pro" else
  2.0 if upvoter_tier == "platinum" else
  1.0
  for upvoter in helpful_upvoters
)
```

---

## Example: Complete Flow

### Scenario: User reads article about Israeli economy

```
1. Article fetched from feed
   ↓
2. AI analysis runs: sentiment=positive, bias=center, credibility=0.82
   ↓
3. Voting data retrieved:
   - 5 bias votes: 3x "left", 2x "center" (weighted: 3×1.5 + 2×1 = 6.5 vs 2)
   - Consensus: LEFT (65% confidence)
   - 8 credibility votes: average = 0.75
   - Consensus: "likely credible" (0.70-0.85 range)
   - 1 flag: "biased framing"
   ↓
4. Updated analysis returned to frontend:
   {
     "bias": "left",           // Updated from AI's "center"
     "bias_confidence": 0.65,  // How sure are we?
     "bias_based_on": "user_consensus",
     "credibility": 0.75,
     "credibility_label": "likely credible",
     "flags": 1
   }
   ↓
5. User can:
   - Vote on bias: "I agree it's left" ✓
   - Vote on credibility: "Source is reliable" ✓
   - Flag if concerned: "False statistics" 🚩
   ↓
6. Their votes immediately influence consensus for next user
```

---

## Metrics to Track

For analytics/dashboards:

```python
# MongoDB aggregations

# Most voted articles
db.bias_votes.aggregate([
  { "$group": { "_id": "$article_id", "count": { "$sum": 1 } } },
  { "$sort": { "count": -1 } },
  { "$limit": 10 }
])

# Most contentious sources
db.credibility_votes.aggregate([
  { "$group": { 
      "_id": "$source_name", 
      "votes": { "$sum": 1 },
      "avg_score": { "$avg": "$credibility_score" },
      "std_dev": { "$stdDevSamp": "$credibility_score" }
  } },
  { "$sort": { "std_dev": -1 } }  # High disagreement
])

# User participation
db.bias_votes.countDocuments({ "user_tier": "pro" })
db.credibility_votes.countDocuments({ "created_at": { "$gte": ISODate("2026-05-01") } })
```

---

## Deployment Checklist

- [x] Schemas updated (BiasVote, CredibilityVote, etc.)
- [x] voting_service.py created with consensus logic
- [x] Database indexes created for performance
- [x] Routes added to ai.py (8 new endpoints)
- [x] API examples updated (API_EXAMPLES.md)
- [ ] Frontend integration (show consensus labels, voting UI)
- [ ] Authentication/authorization (verify user_id from JWT)
- [ ] Rate limiting (prevent vote spam)
- [ ] Monitoring (track voting patterns for abuse)
- [ ] Admin dashboard for moderation queue

---

## Next Steps

1. **Frontend Integration**: Add voting buttons to article cards
2. **Real-time Updates**: WebSocket for live consensus changes
3. **Expert Verification**: Badge system for trusted voters
4. **Reputation Badges**: Show top voters on user profiles
5. **Analytics Dashboard**: Visualize voting patterns, source credibility trends
6. **Appeal System**: Allow articles to appeal flags, provide counter-evidence

---

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Users voting per article | 5-10 | 2-3 weeks |
| Consensus accuracy (vs ground truth) | 85%+ | Month 2 |
| Mod queue resolution time | <24 hours | Continuous |
| Repeat voters (reputation builders) | 20%+ | Month 1 |
| Pro/Platinum participation | 15%+ of votes | Month 2 |

