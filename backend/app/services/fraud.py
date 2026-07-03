"""
Fraud scoring service.

This service evaluates transfers for fraud risk using a combination of:
1. Rule-based heuristics (immediate red flags)
2. ML model scores (when available)
3. Historical patterns

Transfers with high fraud scores are held for manual review.
"""

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class FraudScore:
    """Result of fraud evaluation."""
    score: float  # 0.0 = safe, 1.0 = definitely fraud
    reasons: list[str]
    should_hold: bool


class FraudEngine:
    """Fraud detection engine using rule-based heuristics."""
    
    # Thresholds
    HOLD_THRESHOLD = 0.7  # Scores above this trigger manual review
    WARNING_THRESHOLD = 0.5  # Scores above this get flagged but still process
    
    # Risk factors
    MAX_SINGLE_TRANSFER = 10_000_00  # $10,000 in cents
    MAX_DAILY_VOLUME = 50_000_00  # $50,000 in cents
    MAX_HOURLY_TRANSFERS = 10
    SUSPICIOUS_NOTES = ["test", "scam", "hack", "crypto", "bitcoin"]
    
    def __init__(self, db_pool):
        self.db = db_pool
    
    async def score_transfer(
        self,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
        amount_cents: int,
        note: str | None = None,
    ) -> FraudScore:
        """Evaluate a transfer for fraud risk."""
        reasons = []
        score = 0.0
        
        # Check for suspicious notes
        if note:
            note_lower = note.lower()
            for suspicious in self.SUSPICIOUS_NOTES:
                if suspicious in note_lower:
                    score += 0.3
                    reasons.append(f"Suspicious keyword in note: '{suspicious}'")
        
        # Check for unusually large transfers
        if amount_cents > self.MAX_SINGLE_TRANSFER:
            score += 0.4
            reasons.append(f"Large transfer amount: ${amount_cents / 100:.2f}")
        
        # Check user's recent activity
        recent_volume = await self._get_daily_volume(from_user_id)
        if recent_volume > self.MAX_DAILY_VOLUME:
            score += 0.3
            reasons.append(f"High daily volume: ${recent_volume / 100:.2f}")
        
        # Check for rapid successive transfers
        recent_count = await self._get_hourly_transfer_count(from_user_id)
        if recent_count > self.MAX_HOURLY_TRANSFERS:
            score += 0.2
            reasons.append(f"High hourly transfer count: {recent_count}")
        
        # Check if sending to a new user (account created recently)
        if await self._is_new_user(to_user_id):
            score += 0.15
            reasons.append("Recipient is a new user")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return FraudScore(
            score=score,
            reasons=reasons,
            should_hold=score >= self.HOLD_THRESHOLD,
        )
    
    async def _get_daily_volume(self, user_id: uuid.UUID) -> int:
        """Get total transfer volume for a user in the last 24 hours."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(amount), 0) as volume
                FROM transfers t
                JOIN accounts a ON a.id = t.from_account
                WHERE a.user_id = $1
                  AND t.created_at > NOW() - INTERVAL '24 hours'
                  AND t.status IN ('completed', 'pending_review')
                """,
                user_id,
            )
            return row["volume"] if row else 0
    
    async def _get_hourly_transfer_count(self, user_id: uuid.UUID) -> int:
        """Get number of transfers in the last hour."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) as count
                FROM transfers t
                JOIN accounts a ON a.id = t.from_account
                WHERE a.user_id = $1
                  AND t.created_at > NOW() - INTERVAL '1 hour'
                """,
                user_id,
            )
            return row["count"] if row else 0
    
    async def _is_new_user(self, user_id: uuid.UUID) -> bool:
        """Check if user account was created in the last 7 days."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT created_at FROM users WHERE id = $1
                """,
                user_id,
            )
            if not row:
                return False
            from datetime import datetime, timedelta
            return row["created_at"] > datetime.now() - timedelta(days=7)


# Fallback simple scorer for when DB isn't available
class SimpleFraudEngine:
    """Simple rule-based fraud detection without database lookups."""
    
    HOLD_THRESHOLD = 0.7
    MAX_SINGLE_TRANSFER = 10_000_00
    SUSPICIOUS_NOTES = ["test", "scam", "hack", "crypto", "bitcoin"]
    
    def score_transfer(
        self,
        amount_cents: int,
        note: str | None = None,
    ) -> FraudScore:
        """Simple scoring based only on amount and note."""
        reasons = []
        score = 0.0
        
        if note:
            note_lower = note.lower()
            for suspicious in self.SUSPICIOUS_NOTES:
                if suspicious in note_lower:
                    score += 0.4
                    reasons.append(f"Suspicious keyword in note: '{suspicious}'")
        
        if amount_cents > self.MAX_SINGLE_TRANSFER:
            score += 0.5
            reasons.append(f"Large transfer amount: ${amount_cents / 100:.2f}")
        
        score = min(score, 1.0)
        
        return FraudScore(
            score=score,
            reasons=reasons,
            should_hold=score >= self.HOLD_THRESHOLD,
        )
