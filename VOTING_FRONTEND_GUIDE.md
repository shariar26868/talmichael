# Voting System — Frontend Integration Guide

**For**: Frontend/UI Developers  
**Purpose**: Integrate voting UI into article display  
**Timeline**: 2-3 days

---

## Quick Start

The backend is ready. You need to:

1. ✅ Add voting UI components to article cards
2. ✅ Call voting API endpoints on user interaction
3. ✅ Display consensus results with confidence indicators
4. ✅ Show user reputation badges on profiles

---

## API Endpoints (Backend Ready)

### 1. Vote on Bias
```javascript
POST /ai/articles/{article_id}/vote/bias
Query: user_id, user_tier (free|pro|platinum)
Body: { bias_assessment, confidence, user_notes }
Response: { status, vote_id, recorded_at }
```

### 2. Vote on Credibility
```javascript
POST /ai/sources/{source_name}/vote/credibility
Query: user_id, user_tier
Body: { credibility_level, evidence }
Response: { status, vote_id, recorded_at }
```

### 3. Flag Article
```javascript
POST /ai/articles/{article_id}/flag
Query: user_id
Body: { reason, details }
Response: { status, flag_id, message }
```

### 4. View Voting Stats
```javascript
GET /ai/articles/{article_id}/votes
Response: { bias_votes_count, flags_count, votes {...} }

GET /ai/sources/{source_name}/votes
Response: { source_name, votes {...} }
```

### 5. User Leaderboard
```javascript
GET /ai/votes/leaderboard?limit=10
Response: { leaderboard: [{_id, total_votes, helpful_votes}, ...] }
```

---

## UI Component: Article Bias Card

### Design (HTML/React)

```jsx
<div className="article-bias-card">
  {/* AI Assessment */}
  <div className="ai-assessment">
    <label>AI Analysis</label>
    <span className="bias-badge" data-bias={article.bias}>
      {biasLabel(article.bias)}
    </span>
    <span className="confidence">
      {article.credibility_score}% credible
    </span>
  </div>

  {/* Voting Section */}
  <div className="voting-section">
    <label>Do you agree?</label>
    
    {/* Bias Voting Buttons */}
    <div className="bias-buttons">
      {["left", "center", "right", "unclear"].map(bias => (
        <button
          key={bias}
          onClick={() => submitBiasVote(article.id, bias)}
          className={`bias-btn ${selectedBias === bias ? 'active' : ''}`}
        >
          {biasEmoji(bias)} {bias}
        </button>
      ))}
    </div>

    {/* Confidence Slider */}
    <input
      type="range"
      min="0.1"
      max="1.0"
      step="0.1"
      value={confidence}
      onChange={(e) => setConfidence(parseFloat(e.target.value))}
    />
    <span>Confidence: {(confidence * 100).toFixed(0)}%</span>

    {/* Optional Notes */}
    <textarea
      placeholder="Why do you think this? (optional)"
      value={userNotes}
      onChange={(e) => setUserNotes(e.target.value)}
    />

    {/* Submit */}
    <button onClick={handleBiasVote} className="btn-primary">
      Submit Vote
    </button>
  </div>

  {/* Consensus Display */}
  {article.bias_based_on === "user_consensus" && (
    <div className="consensus-banner">
      ✓ Community validated: <strong>{article.bias}</strong>
      ({(article.bias_confidence * 100).toFixed(0)}% agreement)
    </div>
  )}

  {/* Voting Stats */}
  <div className="voting-stats">
    <a href="#" onClick={() => showVoteBreakdown(article.id)}>
      {article.bias_votes_count} votes • {article.flags_count} flags
    </a>
  </div>

  {/* Flag Button */}
  <button className="btn-secondary" onClick={() => openFlagDialog(article.id)}>
    🚩 Report Issue
  </button>
</div>
```

### Styling (CSS)

```css
.article-bias-card {
  border-left: 4px solid #0066cc;
  padding: 12px;
  margin: 12px 0;
  background: #f9f9f9;
  border-radius: 4px;
}

.bias-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: bold;
  margin: 0 8px;
}

.bias-badge[data-bias="left"] {
  background: #e8f0ff;
  color: #003d99;
}

.bias-badge[data-bias="center"] {
  background: #f0f0f0;
  color: #333;
}

.bias-badge[data-bias="right"] {
  background: #ffe8e8;
  color: #990000;
}

.bias-buttons {
  display: flex;
  gap: 8px;
  margin: 12px 0;
}

.bias-btn {
  padding: 6px 12px;
  border: 1px solid #ccc;
  background: white;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.bias-btn:hover {
  border-color: #0066cc;
  background: #f0f8ff;
}

.bias-btn.active {
  background: #0066cc;
  color: white;
}

.consensus-banner {
  background: #e8f5e9;
  border-left: 4px solid #4caf50;
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 2px;
  font-size: 0.9em;
}
```

---

## JavaScript/React Implementation

### Vote on Bias

```javascript
async function submitBiasVote(articleId, biasAssessment, confidence = 0.7, userNotes = "") {
  const userId = getCurrentUserId();
  const userTier = getCurrentUserTier();
  
  try {
    const response = await fetch(
      `/ai/articles/${articleId}/vote/bias?user_id=${userId}&user_tier=${userTier}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bias_assessment: biasAssessment,
          confidence: confidence,
          user_notes: userNotes
        })
      }
    );
    
    const result = await response.json();
    
    if (response.ok) {
      // Show success message
      showNotification("Vote recorded! Thank you.", "success");
      
      // Refresh article to show updated consensus
      await refreshArticleAnalysis(articleId);
    } else {
      showNotification("Error: " + result.detail, "error");
    }
  } catch (error) {
    console.error("Vote submission failed:", error);
    showNotification("Failed to submit vote", "error");
  }
}
```

### Vote on Credibility

```javascript
async function submitCredibilityVote(sourceName, credibilityLevel, evidence = "") {
  const userId = getCurrentUserId();
  const userTier = getCurrentUserTier();
  
  try {
    const response = await fetch(
      `/ai/sources/${sourceName}/vote/credibility?user_id=${userId}&user_tier=${userTier}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          credibility_level: credibilityLevel,
          evidence: evidence
        })
      }
    );
    
    const result = await response.json();
    
    if (response.ok) {
      showNotification("Source credibility vote recorded!", "success");
      // Refresh all articles from this source
      await refreshSourceArticles(sourceName);
    }
  } catch (error) {
    console.error("Credibility vote failed:", error);
  }
}
```

### Flag Article

```javascript
async function flagArticle(articleId, reason, details) {
  const userId = getCurrentUserId();
  
  try {
    const response = await fetch(
      `/ai/articles/${articleId}/flag?user_id=${userId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: reason,  // misinformation|propaganda|biased|unreliable_source
          details: details
        })
      }
    );
    
    const result = await response.json();
    
    if (response.ok) {
      showNotification(
        "Thank you! Our team will review this article.",
        "success"
      );
    }
  } catch (error) {
    console.error("Flag submission failed:", error);
  }
}
```

### Display Voting Statistics

```javascript
async function displayVotingStats(articleId) {
  try {
    const response = await fetch(`/ai/articles/${articleId}/votes`);
    const stats = await response.json();
    
    // Group by bias assessment
    const biasBreakdown = {};
    stats.votes.bias_votes.forEach(vote => {
      const assessment = vote.bias_assessment;
      biasBreakdown[assessment] = (biasBreakdown[assessment] || 0) + 1;
    });
    
    // Display modal
    showModal({
      title: "Community Voting",
      content: `
        <p>Bias assessments: ${JSON.stringify(biasBreakdown)}</p>
        <p>Flags: ${stats.flags_count}</p>
      `
    });
  } catch (error) {
    console.error("Failed to fetch voting stats:", error);
  }
}
```

---

## Component: Credibility Source Rating

For displaying credibility next to source name:

```jsx
<div className="article-source">
  <strong>{article.source}</strong>
  
  <CredibilityBadge source={article.source} />
</div>

function CredibilityBadge({ source }) {
  const [credibility, setCredibility] = useState(null);
  
  useEffect(() => {
    fetchSourceCredibility(source).then(setCredibility);
  }, [source]);
  
  if (!credibility) return null;
  
  const stars = Math.round(credibility.score * 5);
  
  return (
    <span 
      className="credibility-badge"
      title={`${credibility.label} (${(credibility.score * 100).toFixed(0)}%)`}
    >
      {'⭐'.repeat(stars)}{'☆'.repeat(5 - stars)}
    </span>
  );
}
```

---

## Component: User Reputation Badge

Show on user profiles:

```jsx
<div className="user-reputation">
  <h3>Voting Reputation</h3>
  
  <div className="rep-stats">
    <div className="stat">
      <span className="number">{user.bias_votes}</span>
      <span className="label">Bias Votes</span>
    </div>
    <div className="stat">
      <span className="number">{user.credibility_votes}</span>
      <span className="label">Credibility Votes</span>
    </div>
    <div className="stat">
      <span className="number">{user.helpful_votes}</span>
      <span className="label">Helpful Votes</span>
    </div>
  </div>
  
  {user.rank && (
    <div className="rank-badge">
      🏆 #{user.rank} Top Voter
    </div>
  )}
</div>
```

---

## Dialog: Flag Article

Modal for reporting issues:

```jsx
function FlagDialog({ articleId, onClose }) {
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  
  return (
    <dialog className="flag-dialog">
      <h2>Report Article Issue</h2>
      
      <fieldset>
        <legend>Reason</legend>
        <label>
          <input
            type="radio"
            name="reason"
            value="misinformation"
            onChange={(e) => setReason(e.target.value)}
          />
          Contains false information
        </label>
        <label>
          <input
            type="radio"
            name="reason"
            value="propaganda"
            onChange={(e) => setReason(e.target.value)}
          />
          Propaganda or manipulation
        </label>
        <label>
          <input
            type="radio"
            name="reason"
            value="biased"
            onChange={(e) => setReason(e.target.value)}
          />
          Unfairly biased
        </label>
        <label>
          <input
            type="radio"
            name="reason"
            value="unreliable_source"
            onChange={(e) => setReason(e.target.value)}
          />
          Unreliable source
        </label>
      </fieldset>
      
      <textarea
        placeholder="Please explain..."
        value={details}
        onChange={(e) => setDetails(e.target.value)}
      />
      
      <button
        onClick={() => {
          flagArticle(articleId, reason, details);
          onClose();
        }}
      >
        Submit Report
      </button>
      <button onClick={onClose}>Cancel</button>
    </dialog>
  );
}
```

---

## Testing Checklist

- [ ] Can submit bias vote
- [ ] Can submit credibility vote
- [ ] Can flag article
- [ ] Voting stats display correctly
- [ ] Consensus updates after votes
- [ ] User reputation shows on profile
- [ ] Leaderboard displays correctly
- [ ] Mobile responsive (voting buttons stack)

---

## Performance Tips

1. **Cache voting stats** — Don't fetch on every article load
2. **Debounce confidence slider** — Prevent rapid API calls
3. **Show loading state** — Indicate vote is being submitted
4. **Batch updates** — Don't update all articles at once

```javascript
// Example: Debounced confidence slider
const debouncedVote = debounce(
  (articleId, bias, confidence) => submitBiasVote(articleId, bias, confidence),
  1000  // Wait 1 second after last change
);
```

---

## Error Handling

```javascript
async function submitBiasVoteWithErrorHandling(articleId, bias, confidence) {
  try {
    const result = await submitBiasVote(articleId, bias, confidence);
    return { success: true, data: result };
  } catch (error) {
    if (error.message.includes("401")) {
      // Redirect to login
      redirectToLogin();
    } else if (error.message.includes("429")) {
      // Rate limited
      showNotification("Too many votes. Please wait.", "warning");
    } else {
      showNotification("Vote failed. Try again.", "error");
    }
    return { success: false, error };
  }
}
```

---

## Timeline

| Week | Tasks |
|------|-------|
| Week 1 | Design voting UI component, integrate bias voting |
| Week 2 | Add credibility voting, flag dialog, stats display |
| Week 3 | User reputation badges, leaderboard, testing |
| Week 4 | Polish, performance optimization, launch |

---

## Questions

Check:
- Backend API: [API_EXAMPLES.md](API_EXAMPLES.md)
- System Design: [VOTING_SYSTEM_GUIDE.md](VOTING_SYSTEM_GUIDE.md)
- Code: `app/services/voting_service.py`
