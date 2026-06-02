#!/usr/bin/env python3
"""
Example usage of the user voting mechanism for bias/credibility validation.

This demonstrates:
1. Submitting bias votes on articles
2. Submitting credibility votes on sources
3. Flagging articles
4. Viewing voting statistics
5. Computing consensus from votes

Run: python scratch/voting_example.py
"""

import asyncio
from datetime import datetime
from app.core.database import get_db
from app.services.voting_service import (
    submit_bias_vote,
    submit_credibility_vote,
    flag_article,
    compute_bias_consensus,
    compute_credibility_consensus,
    get_article_votes,
    get_source_votes,
    get_user_vote_history,
    get_top_voters,
)


async def main():
    """Demonstrate the voting system."""
    
    print("=" * 80)
    print("TALMICAHEL: USER VOTING MECHANISM EXAMPLE")
    print("=" * 80)
    
    # Example article and source
    article_id = "article-israel-economy-2026-05-26"
    source_name = "Haaretz"
    user_id_1 = "user-123"
    user_id_2 = "user-456"
    user_id_3 = "user-789"
    
    # ────────────────────────────────────────────────────────────────────────
    # 1. SUBMIT BIAS VOTES
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n1️⃣  SUBMITTING BIAS VOTES")
    print("-" * 80)
    
    # Free tier user votes
    vote1 = await submit_bias_vote(
        article_id=article_id,
        user_id=user_id_1,
        user_tier="free",
        bias_assessment="left",
        confidence=0.75,
        user_notes="Article uses loaded language and ignores counter-arguments",
    )
    print(f"✓ Free user vote: {vote1['bias_assessment']} (confidence: {vote1['confidence']})")
    
    # Pro tier user votes (weighted 1.5x)
    vote2 = await submit_bias_vote(
        article_id=article_id,
        user_id=user_id_2,
        user_tier="pro",
        bias_assessment="left",
        confidence=0.82,
        user_notes="Cherry-picked statistics, missing context",
    )
    print(f"✓ Pro user vote: {vote2['bias_assessment']} (confidence: {vote2['confidence']})")
    
    # Platinum tier user votes (weighted 2x)
    vote3 = await submit_bias_vote(
        article_id=article_id,
        user_id=user_id_3,
        user_tier="platinum",
        bias_assessment="left",
        confidence=0.88,
        user_notes="Heavily one-sided reporting",
    )
    print(f"✓ Platinum user vote: {vote3['bias_assessment']} (confidence: {vote3['confidence']})")
    
    # ────────────────────────────────────────────────────────────────────────
    # 2. COMPUTE BIAS CONSENSUS
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n2️⃣  COMPUTING BIAS CONSENSUS")
    print("-" * 80)
    
    ai_bias = "center"  # Simulated AI assessment
    consensus = await compute_bias_consensus(article_id, ai_bias)
    
    print(f"AI Assessment: {ai_bias}")
    print(f"Consensus: {consensus.bias}")
    print(f"Confidence: {consensus.confidence:.2%}")
    print(f"Based on: {consensus.based_on}")
    print(f"Vote count: {consensus.vote_count}")
    if consensus.stats:
        print(f"Breakdown: {consensus.stats.breakdown}")
        print(f"Consensus %: {consensus.stats.consensus_percentage:.1f}%")
    
    # ────────────────────────────────────────────────────────────────────────
    # 3. SUBMIT CREDIBILITY VOTES
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n3️⃣  SUBMITTING CREDIBILITY VOTES")
    print("-" * 80)
    
    cred_vote1 = await submit_credibility_vote(
        source_name=source_name,
        user_id=user_id_1,
        user_tier="free",
        credibility_level="high",
        evidence="Generally accurate reporting, good fact-checking",
    )
    print(f"✓ Free user: {source_name} → {cred_vote1['credibility_level']} (score: {cred_vote1['credibility_score']})")
    
    cred_vote2 = await submit_credibility_vote(
        source_name=source_name,
        user_id=user_id_2,
        user_tier="pro",
        credibility_level="high",
        evidence="Rigorous journalism, transparent corrections",
    )
    print(f"✓ Pro user: {source_name} → {cred_vote2['credibility_level']} (score: {cred_vote2['credibility_score']})")
    
    cred_vote3 = await submit_credibility_vote(
        source_name=source_name,
        user_id=user_id_3,
        user_tier="platinum",
        credibility_level="medium",
        evidence="Solid reporting but occasional political bias in framing",
    )
    print(f"✓ Platinum user: {source_name} → {cred_vote3['credibility_level']} (score: {cred_vote3['credibility_score']})")
    
    # ────────────────────────────────────────────────────────────────────────
    # 4. COMPUTE CREDIBILITY CONSENSUS
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n4️⃣  COMPUTING CREDIBILITY CONSENSUS")
    print("-" * 80)
    
    ai_credibility = 0.82  # Simulated AI assessment
    cred_consensus = await compute_credibility_consensus(source_name, ai_credibility)
    
    print(f"AI Assessment: {ai_credibility:.2f}")
    print(f"Consensus Score: {cred_consensus.credibility_score:.2f}")
    print(f"Consensus Label: {cred_consensus.credibility_label}")
    print(f"Based on: {cred_consensus.based_on}")
    print(f"Vote count: {cred_consensus.vote_count}")
    if cred_consensus.stats:
        print(f"Breakdown: {cred_consensus.stats.breakdown}")
    
    # ────────────────────────────────────────────────────────────────────────
    # 5. FLAG ARTICLE
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n5️⃣  FLAGGING ARTICLE")
    print("-" * 80)
    
    flag = await flag_article(
        article_id=article_id,
        user_id=user_id_1,
        reason="biased",
        details="The article presents only one perspective on the economic data. Missing analysis of alternative viewpoints.",
    )
    print(f"✓ Article flagged for: {flag['reason']}")
    print(f"  Flag ID: {flag['_id']}")
    print(f"  Status: {flag['status']}")
    
    # ────────────────────────────────────────────────────────────────────────
    # 6. VIEW VOTING STATISTICS
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n6️⃣  VIEWING VOTING STATISTICS")
    print("-" * 80)
    
    article_votes = await get_article_votes(article_id)
    print(f"Article: {article_id}")
    print(f"  Bias votes: {len(article_votes['bias_votes'])}")
    print(f"  Flags: {article_votes['flag_count']}")
    print(f"  Flag reasons: {article_votes['flags_by_reason']}")
    
    source_votes = await get_source_votes(source_name)
    print(f"\nSource: {source_name}")
    print(f"  Credibility votes: {source_votes['total_votes']}")
    
    # ────────────────────────────────────────────────────────────────────────
    # 7. USER REPUTATION
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n7️⃣  USER REPUTATION & VOTING HISTORY")
    print("-" * 80)
    
    user_history = await get_user_vote_history(user_id_2)
    print(f"User: {user_id_2}")
    print(f"  Bias votes: {user_history['bias_votes']}")
    print(f"  Credibility votes: {user_history['credibility_votes']}")
    print(f"  Flags submitted: {user_history['flags']}")
    
    # ────────────────────────────────────────────────────────────────────────
    # 8. LEADERBOARD
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n8️⃣  TOP VOTERS LEADERBOARD")
    print("-" * 80)
    
    top_voters = await get_top_voters(limit=3)
    print("Top contributors by helpful votes:")
    for i, voter in enumerate(top_voters, 1):
        print(f"  {i}. {voter['_id']}: {voter['helpful_votes']} helpful votes ({voter['total_votes']} total)")
    
    # ────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ────────────────────────────────────────────────────────────────────────
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    print(f"""
✅ BIAS CONSENSUS: {consensus.bias}
   - AI said: {ai_bias}
   - Users validated: {consensus.bias} ({consensus.confidence:.0%} confidence)
   - Votes weighted by tier: Free=1x, Pro=1.5x, Platinum=2x

✅ CREDIBILITY CONSENSUS: {cred_consensus.credibility_score:.2f} ({cred_consensus.credibility_label})
   - AI said: {ai_credibility:.2f}
   - Users validated: {cred_consensus.credibility_score:.2f}
   - Reflects user community expertise

✅ QUALITY CONTROL:
   - Article flagged as: {flag['reason']}
   - Moderation team will review
   - Status: {flag['status']} → review → addressed

✅ REPUTATION SYSTEM:
   - High-quality votes get upvoted by other users
   - Top voters appear on leaderboard
   - Encourages participation from expert users

🎯 RESULT: Your platform now has crowdsourced trust validation!
    """)


if __name__ == "__main__":
    asyncio.run(main())
