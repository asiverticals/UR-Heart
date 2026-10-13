1. Master Conditions Matrix (C1 – C4) Runtime State Engine
UR-Heart Sanctuary uses four deterministic runtime gates (Conditions C1 – C4) to regulate algorithmic access, geographic bootstrapping, monetization boundaries, and distribution runtime environments.
MD

                                  ┌──────────────────────────────────────────────┐
                                  │      APP LIFECYCLE & DISCOVERY INITIALIZER   │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        ▼                                ▼                                ▼
         ┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────┐
         │     CONDITION C1 GATE        │ │     CONDITION C3 GATE        │ │     CONDITION C2 GATE        │
         │   30-Day MAU >= 1,000,000?   │ │   30-Day MAU >= 1,000,000?   │ │ ENABLE_GLOBAL_USD_BILLING?   │
         │   OR Override Flag == True   │ │   OR Override Flag == True   │ │                              │
         └──────────────┬───────────────┘ └──────────────┬───────────────┘ └──────────────┬───────────────┘
                        │                                │                                │
             ┌──────────┴──────────┐          ┌──────────┴──────────┐          ┌──────────┴──────────┐
             ▼                     ▼          ▼                     ▼          ▼                     ▼
        [LOCKED: 403]       [UNLOCKED]   [LOCKED: 403]       [UNLOCKED]   [INR + Ads]        [USD Active]
        Progress Dialog    Active 180s   Local Radius Only  Global Roam   Micro-perks ₹29    Global Catalog

MD

Comprehensive Conditions Runtime Specification
Gate Domain Target Configuration Flags Mathematical Rule & Evaluation Query Runtime Engine Behavior UI Presentation State
C1 Blind Date 1M MAU Gate 
BLIND_DATE_MIN_ACTIVE_USERS=1000000

ENABLE_BLIND_DATE_OVERRIDE=false

MD

MAU
30
d
≥
1
,
000
,
000
∨
Override
=

=
true
MAU
30d
​
 ≥1,000,000∨Override==true

MD

Endpoint /api/v1/blind-date/queue/join executes live 30-day active user count query. Returns 403 Forbidden (milestone_locked) if condition fails.
MD

+ 1

Flutter Hub renders MilestoneProgressIndicator showing live community progress toward 1,000,000 active souls with explanatory modal.
MD

C2 Monetization Currency Boundary 
ENABLE_GLOBAL_USD_BILLING=false

MD

Flag
=

=
true
⟹
Catalog
USD
 Active
Flag==true⟹Catalog
USD
​
  Active

MD

Primary live revenue defaults strictly to Indian Rupee (INR ₹) micro-perks and rewarded video ads. International USD tier catalog is gated.
MD

+ 1

Store UI defaults to INR (₹) micro-perks (₹29 Direct Letter, ₹99 Bridge). USD pricing remains invisible until flag is enabled.
MD

+ 1

C3 Global Passport 1M MAU Gate 
PASSPORT_MIN_ACTIVE_USERS=1000000

ENABLE_PASSPORT_OVERRIDE=false

MD

MAU
30
d
≥
1
,
000
,
000
∨
Override
=

=
true
MAU
30d
​
 ≥1,000,000∨Override==true

MD

Rejects coordinate override requests outside local boundary until density milestone is attained, preventing early geographical dilution.
MD

Discovery settings display Global Passport locked behind community milestone badge with informative dialog.
MD

C4 Target Runtime Platform 
Native Android / Standalone Web PWA
MD

Platform
∈
{
Android Native
,
Installable PWA
}
Platform∈{Android Native,Installable PWA}

MD

Codebase supports Native Android (.apk/.aab) and installable iOS/Desktop PWA (manifest.json, sw.js, Standalone Safari).
MD

Responsive container (ResponsiveDesktopFrame) displays laptop mockup on viewports
≥
600
px
≥600px.
MD

MD

1. Condition C1: 180s / 300s Blind Date Subsystem
The Blind Date subsystem provides an anonymous, fast-track matchmaking experience while preserving privacy.
MD

2.1 Backend Verification & Milestone Evaluator
Implemented in backend/app/services/blind_date_service.py:
MD

Python

# backend/app/services/blind_date_service.py

from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.domain.user import User
from app.core.exceptions import MilestoneLockedException

async def verify_blind_date_milestone_unlocked(session: AsyncSession) -> dict:
    """Verifies Condition C1: 1M 30-day MAU gate check."""
    if settings.ENABLE_BLIND_DATE_OVERRIDE:
        return {"unlocked": True, "current_mau": 1_000_000, "target_mau": settings.BLIND_DATE_MIN_ACTIVE_USERS}

    query = select(func.count(User.id)).where(
        User.deleted_at.is_(None),
        User.last_active_at >= func.now() - func.cast("30 days", func.INTERVAL)
    )
    result = await session.execute(query)
    current_mau = result.scalar() or 0

    if current_mau < settings.BLIND_DATE_MIN_ACTIVE_USERS:
        raise MilestoneLockedException(
            condition_code="C1",
            current_mau=current_mau,
            target_mau=settings.BLIND_DATE_MIN_ACTIVE_USERS
        )

    return {"unlocked": True, "current_mau": current_mau, "target_mau": settings.BLIND_DATE_MIN_ACTIVE_USERS}

MD

2.2 Blind Date Session State Machine
  ┌───────────────────┐
  │   JOIN QUEUE      │ ──► Enqueued in public.blind_date_queue (status: 'waiting')
  └─────────┬─────────┘
            │
            ▼ (FIFO Matching on age, gender & reciprocal orientation)
  ┌───────────────────┐
  │   SESSION ACTIVE  │ ──► 180s Timer Initiated (expires_at = NOW() + 180s)
  │                   │     35px Frosted Veil on Profile Photos
  │                   │     Eva Icebreaker Prompt Injected
  └─────────┬─────────┘
            │
            ├─────────────────────────────────────────┐
            ▼ (Optional +180s Extension)              ▼ (Timer Hits 0s)
  ┌───────────────────┐                     ┌───────────────────┐
  │  SESSION EXTENDED │                     │  SESSION EXPIRED  │
  │ (extension_count) │                     │ (status: expired) │
  └─────────┬─────────┘                     └───────────────────┘
            │
            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                  MUTUAL RESONANCE DECISION                  │
  └──────────────┬──────────────────────────────┬───────────────┘
                 │                              │
                 ▼ (Both select 'resonate')     ▼ (Either selects 'pass')
  ┌──────────────────────────────┐ ┌──────────────────────────────┐
  │      STATUS: REVEALED        │ │       STATUS: PASSED         │
  │ • Blur Veil Unmasked         │ │ • Session archived           │
  │ • Provision public.matches   │ │ • Zero penalty for either    │
  │ • Elevate to 1:1 Dialogue    │ │ • Return to Discovery deck   │
  └──────────────────────────────┘ └──────────────────────────────┘

MD

Mathematical State Transitions
Let session state be
S
∈
{
waiting
,
active
,
expired
,
revealed
,
passed
}
S∈{waiting,active,expired,revealed,passed}:

Transition
waiting
→
active
waiting→active:
Occurs when seekers
u
1
,
u
2
u
1
​
 ,u
2
​
  satisfy mutual orientation matching:

match
(
u
1
,
u
2
)
⟺
u
1
.
gender
∈
u
2
.
interested_in
∧
u
2
.
gender
∈
u
1
.
interested_in
match(u
1
​
 ,u
2
​
 )⟺u
1
​
 .gender∈u
2
​
 .interested_in∧u
2
​
 .gender∈u
1
​
 .interested_in
∧
u
1
.
age
∈
[
u
2
.
pref_min
,
u
2
.
pref_max
]
∧
u
2
.
age
∈
[
u
1
.
pref_min
,
u
1
.
pref_max
]
∧u
1
​
 .age∈[u
2
​
 .pref_min,u
2
​
 .pref_max]∧u
2
​
 .age∈[u
1
​
 .pref_min,u
1
​
 .pref_max]

MD

Transition
active
→
revealed
active→revealed:

d
(
u
1
)
=

’resonate’
∧
d
(
u
2
)
=

’resonate’
d(u
1
​
 )=’resonate’∧d(u
2
​
 )=’resonate’

Action: Insert into public.matches(user1_id, user2_id) and dispatch real-time reveal frame.
MD

Transition
active
→
passed
active→passed:

d
(
u
1
)
=

’pass’
∨
d
(
u
2
)
=

’pass’
∨
(
T
remaining
≤
0
∧
¬
(
d
(
u
1
)
=

’resonate’
∧
d
(
u
2
)
=

’resonate’
)
)
d(u
1
​
 )=’pass’∨d(u
2
​
 )=’pass’∨(T
remaining
​
 ≤0∧¬(d(u
1
​
 )=’resonate’∧d(u
2
​
 )=’resonate’))

Action: Close session with dignity; zero negative bias recorded in algorithm.
MD

1. Condition C3: Discovery Deck & Geofence Fuzzing Engine
To protect user home addresses and comply with Section 6 of India's DPDP Act 2023, exact GPS coordinates are sanitized and fuzzed.
MD

  Raw Device GPS (lat, lon) ──► DPDP Act Coordinate Fuzzing ──► Discovery Projection
  e.g., (26.792194, 82.199821)       Round to 2 decimals (~1.1 km)    (26.790000, 82.200000)
                                      Clamp minimum display to 0.5 km

MD

3.1 DPDP Act GPS Fuzzing & Distance Mathematics
Let raw GPS coordinates be
(
ϕ
raw
,
λ
raw
)
(ϕ
raw
​
 ,λ
raw
​
 ).
The obfuscated coordinates stored and broadcast are calculated via rounding:

ϕ
fuzzed
=

⌊
100
⋅
ϕ
raw
+
0.5
⌋
100
,
λ
fuzzed
=

⌊
100
⋅
λ
raw
+
0.5
⌋
100
ϕ
fuzzed
​
 =

100
⌊100⋅ϕ
raw
​
 +0.5⌋
​
 ,λ
fuzzed
​
 =

100
⌊100⋅λ
raw
​
 +0.5⌋
​

MD

This limits spatial accuracy to approximately:

Δ
D
≈
111.32
×
0.01
≈
1.11
 km
ΔD≈111.32×0.01≈1.11 km

MD

Proximity between seekers
A
A and
B
B is computed using the Great-Circle Haversine equation:

a
=

sin
⁡
2
(
Δ
ϕ
2
)
+
cos
⁡
(
ϕ
A
)
⋅
cos
⁡
(
ϕ
B
)
⋅
sin
⁡
2
(
Δ
λ
2
)
a=sin
2
 (
2
Δϕ
​
 )+cos(ϕ
A
​
 )⋅cos(ϕ
B
​
 )⋅sin
2
 (
2
Δλ
​
 )
d
=

2
⋅
R
⋅
arcsin
⁡
(
a
)
d=2⋅R⋅arcsin(
a

​
 )
Where
R
=

6371.0
 km
R=6371.0 km.
The displayed distance to users is clamped:

d
display
=

max
⁡
(
0.5
,
d
)
 km
d
display
​
 =max(0.5,d) km

MD

3.2 Discovery Self-Exclusion Perimeter Logic
Implemented in backend/app/services/feed_service.py to prevent duplicate encounters or awkward interactions:
MD

Python

# backend/app/services/feed_service.py

from uuid import UUID
from sqlalchemy import select, and_, not_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain.user import User
from app.models.domain.match_and_chat import Match
from app.models.domain.feed import Swipe
from app.models.domain.legal import BlockedUser

async def build_discovery_feed_query(seeker: User, session: AsyncSession):
    """
    Constructs discovery query with self-exclusion perimeter:
    1. Excludes seeker's own user_id, auth_id, and email.
    2. Excludes previously swiped profiles (likes and passes within 30 days).
    3. Excludes active matches and direct letter recipients.
    4. Excludes bilaterally blocked seekers.
    5. Excludes seekers with is_incognito = TRUE.
    6. Enforces reciprocal orientation filters.
    """
    # 1. Past Swiped IDs (within 30-day replay window)
    swiped_stmt = select(Swipe.target_id).where(
        Swipe.actor_id == seeker.id,
        Swipe.created_at >= func.now() - func.cast("30 days", func.INTERVAL)
    )
    swiped_ids = (await session.execute(swiped_stmt)).scalars().all()

    # 2. Blocked IDs (both incoming and outgoing)
    blocked_stmt = select(BlockedUser.blocked_id).where(BlockedUser.blocker_id == seeker.id)
    blocker_stmt = select(BlockedUser.blocker_id).where(BlockedUser.blocked_id == seeker.id)
    b1 = (await session.execute(blocked_stmt)).scalars().all()
    b2 = (await session.execute(blocker_stmt)).scalars().all()
    excluded_ids = set(swiped_ids + b1 + b2 + [seeker.id])

    # 3. Orientation Filter
    gender_filter = []
    if seeker.interested_in == "Men":
        gender_filter.append(User.gender == "Man")
    elif seeker.interested_in == "Women":
        gender_filter.append(User.gender == "Woman")
    elif seeker.interested_in == "Everyone":
        gender_filter.append(User.gender.in_(["Woman", "Man", "Non-Binary", "Other"]))

    reciprocal_filter = or_(
        User.interested_in == "Everyone",
        and_(seeker.gender == "Man", User.interested_in == "Men"),
        and_(seeker.gender == "Woman", User.interested_in == "Women")
    )

    query = select(User).where(
        User.deleted_at.is_(None),
        User.is_profile_completed.is_(True),
        User.is_incognito.is_(False),
        not_(User.id.in_(excluded_ids)),
        not_(User.auth_id == seeker.auth_id),
        and_(*gender_filter),
        reciprocal_filter
    ).order_by(
        User.boost_points.desc(),
        User.streak_count.desc(),
        User.created_at.desc()
    ).limit(20)

    return query

MD

1. The 3-Stage Progressive Revelation Ritual
Superficial photo swiping is eliminated through a progressive 3-stage revelation model.
MD

  STAGE 1: SANCTUARY DISCOVERY
  • Bio prose, values, lifestyle choices, education, profession
  • 7-second Voice Spark audio snippet
  • 35px Gaussian Blur Veil over photos (No superficial swiping)
               │
               ▼ Mutual Like / Direct Letter
  STAGE 2: ENCRYPTED KINSHIP DIALOGUE
  • 1:1 E2EE encrypted chat chamber (public.messages)
  • Text & emojis only (No image attachments permitted)
  • NLP sanitizers monitor off-platform financial solicitations
               │
               ▼ Bilateral Consent (3 Mindful Ads OR ₹99 Instant Key)
  STAGE 3: SACRED REVEAL & CONTACT BRIDGE
  • Unseals WhatsApp, Instagram, Telegram, Signal handle
  • Mutual cryptographic unsealing across public.whatsapp_reveal_tokens

MD

Stage 3: Sacred Contact Bridge Bilateral State Machine
Handles off-platform handle reveals via mindful ad rituals or Instant Bridge Keys (₹99):
MD

BridgeUnlocked
⟺
(
C
1
∧
C
2
)
∨
K
1
∨
K
2
BridgeUnlocked⟺(C
1
​
 ∧C
2
​
 )∨K
1
​
 ∨K
2
​

Where:

C
i
C
i
​
 : User
i
i watched 3 rewarded mindfulness ads (
A
i
≥
3
A
i
​
 ≥3).
MD

K
i
K
i
​
 : User
i
i redeemed an Instant Contact Key (₹99 micro-perk).
MD

Python

# backend/app/services/contact_bridge_service.py

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain.revelation import ContactRevealToken
from app.core.exceptions import BilateralConsentPendingException

async def process_bridge_ad_increment(match_id: UUID, user_id: UUID, session: AsyncSession) -> dict:
    token = await session.get(ContactRevealToken, match_id)
    if not token:
        token = ContactRevealToken(match_id=match_id)
        session.add(token)

    # Determine user slot in match
    if user_id == token.user1_id:
        token.user1_ads_count = min(3, token.user1_ads_count + 1)
        if token.user1_ads_count == 3:
            token.user1_consent = True
    else:
        token.user2_ads_count = min(3, token.user2_ads_count + 1)
        if token.user2_ads_count == 3:
            token.user2_consent = True

    if token.user1_consent and token.user2_consent:
        token.is_unlocked = True

    await session.commit()
    return {
        "user1_ads": token.user1_ads_count,
        "user2_ads": token.user2_ads_count,
        "is_unlocked": token.is_unlocked
    }

MD

1. Mindful Streak & Night Slumber Engine
Encourages daily intentional reflection over addictive doomscrolling.
MD

                             [ DAILY USER ENGAGEMENT ]
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         Log in within 24 Hours                   Miss 24-Hour Renewal
         OR Watch 1 Reflection Ad                             │
                    │                                         ▼
                    ▼                               Streak Resets to 0
         Streak Count Increments (+1)               Boost Points Cleared
         Extends streak_expires_at +24h

MD

5.1 Accelerometer Night Slumber Rest Multiplier
Night slumber detection runs on the mobile client using device accelerometer stillness between 10:00 PM and 6:00 AM local time. Restful sleep scales morning ad rewards:
MD

+ 1

M
rest
(
t
)
=

{
2.0
if
t
slumber
≥
8.0
 hours
1.5
if
6.0
≤
t
slumber
<
8.0
 hours
1.0
if
t
slumber
<
6.0
 hours
M
rest
​
 (t)=
⎩

⎨

⎧
​
  
2.0
1.5
1.0
​
  
if t
slumber
​
 ≥8.0 hours
if 6.0≤t
slumber
​
 <8.0 hours
if t
slumber
​
 <6.0 hours
​

MD

Morning Reward Multiplier Matrix
Sleep Duration (
t
t) Rest Multiplier (
M
rest
M
rest
​
 ) Morning Harvest Reward Yield
<
6.0
 hours
<6.0 hours 
1.0
×
1.0× (Standard) 
+
10
 Swipes
,
+
10
 Boost Points
+10 Swipes,+10 Boost Points

MD

6.0
≤
t
<
8.0
 hours
6.0≤t<8.0 hours 
1.5
×
1.5× (Mindful Rest) 
+
15
 Swipes
,
+
15
 Boost Points
+15 Swipes,+15 Boost Points

MD

≥
8.0
 hours
≥8.0 hours 
2.0
×
2.0× (Deep Slumber) 
+
20
 Swipes
,
+
2
 Direct Letters
,
+
25
 Points
+20 Swipes,+2 Direct Letters,+25 Points

MD

MD

Python

# backend/app/services/streak_engine.py

from datetime import datetime, timezone, timedelta
from app.models.domain.user import User

def calculate_morning_reward(user: User, sleep_hours: float) -> dict:
    multiplier = 1.0
    if sleep_hours >= 8.0:
        multiplier = 2.0
    elif sleep_hours >= 6.0:
        multiplier = 1.5

    base_swipes = 10
    awarded_swipes = int(base_swipes * multiplier)
    awarded_letters = 2 if multiplier == 2.0 else 0
    awarded_boost_points = int(25 * multiplier)

    return {
        "multiplier": multiplier,
        "swipes_awarded": awarded_swipes,
        "direct_letters_awarded": awarded_letters,
        "boost_points_awarded": awarded_boost_points
    }

MD

1. Mindful Closure Protocol ("Pass with Grace")
To prevent abrupt unmatching and ghosting shocks, conversations conclude using structured closure templates.
MD

  Participant A Initiates "Pass with Grace"
                    │
                    ▼ Selects Closure Template
  ┌─────────────────────────────────────────────────────────────┐
  │ • grace_paths_diverge: "Our paths diverge, honoring our... "│
  │ • grace_not_aligned:   "Our core rhythms differ, wishing... "│
  │ • grace_holding_space: "Taking time for quiet solitude... " │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  Match record status transitions to 'closed_with_grace'
  Dialogue chamber archived with dignity; no abrasive unmatch shock

MD

Curated Closure Templates (backend/app/services/closure_service.py)
Python

# backend/app/services/closure_service.py

CLOSURE_TEMPLATES = {
    "grace_paths_diverge": {
        "title": "Paths Diverge",
        "message": "Our paths diverge, but I honor the moments and thoughts we shared here."
    },
    "grace_not_aligned": {
        "title": "Different Rhythms",
        "message": "I felt our core rhythms and life outlook differ. I wish you profound clarity ahead."
    },
    "grace_holding_space": {
        "title": "Quiet Solitude",
        "message": "I am stepping back to hold space for quiet solitude. Bowing out with gratitude."
    }
}

MD

1. Automated Test Suites & State Verification
To verify the Condition C1–C4 state engines, self-exclusion algorithms, and streak timers:
MD

Bash

# 1. Verify feed self-exclusion and reciprocal orientation filters

pytest backend/tests/test_feed_self_exclusion.py

# 2. Verify mindful streak timers and 24h decay countdown

pytest backend/tests/test_mindful_streak_system.py

# 3. Verify dynamic slumber auction and morning multiplier

pytest backend/tests/test_ads_dynamic_auction_and_antiban.py
