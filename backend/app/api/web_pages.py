"""
Sanctuary Web Portals Router
Serves production-grade, responsive HTML5 portals for UR-Heart Sanctuary:
- /store: Sovereign Web Store with +20% web perks bonus, seeker identity binding, and Razorpay checkout
- /emergency-takedown: Public 24-hr NCII Emergency Takedown Portal under IT Rules 2021 Rule 3(2)(b)
- /grievance: Resident Grievance Officer Portal (Anubhav Singh, Ayodhya District Court, asiverticals@gmail.com)
- /refund: Strict No-Refund & Digital Consumable Finality Policy under Consumer Protection Rules 2020
- /delete-account: Out-of-app Data Incineration & Account Deletion Portal (DPDP § 12, Apple 5.1.1(v) & Google Play)
- /contact: Official Corporate Operations & Support Hub
"""

from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

web_router = APIRouter(tags=["WebPortals"])

# Common CSS Stylesheet for Sanctuary Dark-Gold Glass Aesthetics
SANCTUARY_STYLE = """
:root {
  --bg-deep: #07080B;
  --bg-card: rgba(18, 22, 29, 0.88);
  --bg-card-hover: rgba(26, 32, 42, 0.95);
  --border-gold: rgba(212, 175, 55, 0.28);
  --border-gold-glow: rgba(212, 175, 55, 0.65);
  --text-main: #F3F4F6;
  --text-muted: #9CA3AF;
  --gold-primary: #D4AF37;
  --gold-light: #F3E5AB;
  --gold-dark: #997D29;
  --danger-crimson: #EF4444;
  --danger-bg: rgba(239, 68, 68, 0.12);
  --danger-border: rgba(239, 68, 68, 0.35);
  --success-emerald: #10B981;
  --success-bg: rgba(16, 185, 129, 0.12);
  --success-border: rgba(16, 185, 129, 0.35);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: var(--bg-deep);
  background-image: 
    radial-gradient(ellipse 90% 40% at 50% -10%, rgba(212, 175, 55, 0.18) 0%, rgba(7, 8, 11, 0) 70%),
    radial-gradient(circle 800px at 85% 90%, rgba(212, 175, 55, 0.05) 0%, rgba(7, 8, 11, 0) 60%);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  border-bottom: 1px solid var(--border-gold);
  background: rgba(10, 12, 16, 0.85);
  backdrop-filter: blur(14px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1140px;
  margin: 0 auto;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-main);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #D4AF37 0%, #997D29 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 14px rgba(212, 175, 55, 0.4);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 20px;
  list-style: none;
}

.nav-links a {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}

.nav-links a:hover, .nav-links a.active {
  color: var(--gold-light);
}

.badge-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(16, 185, 129, 0.15);
  color: #34D399;
  border: 1px solid rgba(16, 185, 129, 0.35);
}

.badge-status::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34D399;
  box-shadow: 0 0 8px #34D399;
}

main {
  flex: 1;
  max-width: 1140px;
  width: 100%;
  margin: 0 auto;
  padding: 40px 20px 60px;
}

.hero-banner {
  text-align: center;
  margin-bottom: 40px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 24px;
  background: rgba(212, 175, 55, 0.12);
  border: 1px solid var(--border-gold);
  color: var(--gold-light);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 14px;
}

.hero-title {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #FFFFFF 30%, #E5E7EB 70%, #D4AF37 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  color: var(--text-muted);
  font-size: 16px;
  max-width: 680px;
  margin: 0 auto;
}

.glass-card {
  background: var(--bg-card);
  border: 1px solid var(--border-gold);
  border-radius: 16px;
  padding: 30px;
  backdrop-filter: blur(12px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  margin-bottom: 24px;
  transition: border-color 0.25s, transform 0.25s;
}

.glass-card:hover {
  border-color: var(--border-gold-glow);
}

.glass-card-danger {
  background: rgba(24, 12, 16, 0.9);
  border-color: var(--danger-border);
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
  gap: 24px;
}

.product-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.product-tag {
  position: absolute;
  top: 14px;
  right: 14px;
  background: rgba(212, 175, 55, 0.16);
  border: 1px solid var(--border-gold);
  color: var(--gold-light);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}

.product-price {
  font-size: 32px;
  font-weight: 800;
  color: #FFFFFF;
  margin: 16px 0 8px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.product-price .currency {
  font-size: 20px;
  color: var(--gold-primary);
}

.product-price .alt-price {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 400;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 22px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
  width: 100%;
}

.btn-gold {
  background: linear-gradient(135deg, #D4AF37 0%, #B8972E 100%);
  color: #08090C;
  box-shadow: 0 4px 16px rgba(212, 175, 55, 0.3);
}

.btn-gold:hover {
  background: linear-gradient(135deg, #E6C252 0%, #C4A235 100%);
  box-shadow: 0 6px 22px rgba(212, 175, 55, 0.45);
  transform: translateY(-1px);
}

.btn-danger {
  background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
  color: #FFFFFF;
  box-shadow: 0 4px 16px rgba(220, 38, 38, 0.3);
}

.btn-danger:hover {
  background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
  transform: translateY(-1px);
}

.btn-outline {
  background: transparent;
  color: var(--gold-light);
  border: 1px solid var(--border-gold);
}

.btn-outline:hover {
  background: rgba(212, 175, 55, 0.1);
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--gold-light);
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  background: rgba(11, 13, 17, 0.85);
  border: 1px solid var(--border-gold);
  border-radius: 8px;
  padding: 12px 14px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.form-control:focus {
  border-color: var(--gold-primary);
  box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2);
}

textarea.form-control {
  resize: vertical;
  min-height: 110px;
}

.checkbox-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin: 18px 0;
  cursor: pointer;
  text-align: left;
}

.checkbox-group input[type="checkbox"] {
  accent-color: var(--gold-primary);
  width: 18px;
  height: 18px;
  margin-top: 3px;
}

.checkbox-label {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.alert {
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 24px;
  font-size: 14px;
}

.alert-gold {
  background: rgba(212, 175, 55, 0.08);
  border: 1px solid var(--border-gold);
  color: var(--gold-light);
}

.alert-danger {
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
  color: #FCA5A5;
}

.alert-success {
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  color: #6EE7B7;
}

.trust-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20px;
  margin-top: 36px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.trust-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

footer {
  border-top: 1px solid rgba(212, 175, 55, 0.18);
  background: rgba(7, 8, 11, 0.95);
  padding: 36px 20px;
  font-size: 13px;
  color: var(--text-muted);
  margin-top: auto;
}

.footer-content {
  max-width: 1140px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 24px;
}

.footer-col {
  flex: 1;
  min-width: 220px;
}

.footer-col h4 {
  color: var(--gold-light);
  font-size: 14px;
  margin-bottom: 12px;
}

.footer-col ul {
  list-style: none;
}

.footer-col ul li {
  margin-bottom: 8px;
}

.footer-col ul li a {
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-col ul li a:hover {
  color: var(--gold-primary);
}

.footer-bottom {
  max-width: 1140px;
  margin: 24px auto 0;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
}

@media (max-width: 768px) {
  .nav-container {
    flex-direction: column;
    gap: 12px;
  }
  .nav-links {
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
  }
  .hero-title {
    font-size: 28px;
  }
  .grid-2, .grid-3 {
    grid-template-columns: 1fr;
  }
}
"""

def render_html_page(title: str, content: str, active_tab: str = "") -> str:
    """Renders complete HTML5 page shell with Sanctuary Dark Gold aesthetic."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{SANCTUARY_STYLE}</style>
</head>
<body>
  <header>
    <div class="nav-container">
      <a href="/store" class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#08090C" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </div>
        <span>UR-Heart Sanctuary</span>
      </a>
      <ul class="nav-links">
        <li><a href="/store" class="{'active' if active_tab == 'store' else ''}">Web Store</a></li>
        <li><a href="/emergency-takedown" class="{'active' if active_tab == 'takedown' else ''}">Emergency Takedown</a></li>
        <li><a href="/grievance" class="{'active' if active_tab == 'grievance' else ''}">Grievance Officer</a></li>
        <li><a href="/refund" class="{'active' if active_tab == 'refund' else ''}">Refund Policy</a></li>
        <li><a href="/delete-account" class="{'active' if active_tab == 'deletion' else ''}">Data Deletion</a></li>
        <li><span class="badge-status">Sanctum Online</span></li>
      </ul>
    </div>
  </header>

  <main>
    {content}
  </main>

  <footer>
    <div class="footer-content">
      <div class="footer-col">
        <h4>UR-Heart Sanctuary</h4>
        <p>A sacred, mindful space for authentic connection, protected by cryptographic privacy and bilateral consent.</p>
        <p style="margin-top: 10px; font-size: 12px; color: var(--gold-light);">Operated by ASI Verticals Private Limited</p>
      </div>
      <div class="footer-col">
        <h4>Statutory Portals</h4>
        <ul>
          <li><a href="/emergency-takedown">24-Hour NCII Emergency Desk</a></li>
          <li><a href="/grievance">Resident Grievance Officer</a></li>
          <li><a href="/refund">Strict No-Refund Policy</a></li>
          <li><a href="/delete-account">Out-of-App Data Incineration</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Legal Compliance</h4>
        <ul>
          <li><a href="/api/v1/legal/terms">Terms of Service</a></li>
          <li><a href="/api/v1/legal/privacy">Privacy Policy & DPDP Notice</a></li>
          <li><a href="https://gac.gov.in" target="_blank" rel="noopener">Grievance Appellate Committee (GAC)</a></li>
          <li><a href="/contact">Corporate Office & Support</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Resident Grievance Officer</h4>
        <p><strong style="color: #FFF;">Anubhav Singh</strong><br>
        Resident Grievance Officer & Legal Counsel<br>
        Chambers of Resident Legal Counsel,<br>
        Ayodhya District Court, Ayodhya,<br>
        Uttar Pradesh 224001, India<br>
        Email: <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary);">asiverticals@gmail.com</a>
        </p>
      </div>
    </div>
    <div class="footer-bottom">
      <div>&copy; 2026 ASI Verticals Private Limited. All rights reserved.</div>
      <div>Ayodhya District Court, Uttar Pradesh, Republic of India</div>
    </div>
  </footer>
</body>
</html>
"""


# ==========================================
# 1. WEB STORE ROUTE (/store)
# ==========================================
@web_router.get("/store", response_class=HTMLResponse)
@web_router.get("/shop", response_class=HTMLResponse)
@web_router.get("/sanctuary-store", response_class=HTMLResponse)
async def serve_web_store(request: Request) -> HTMLResponse:
    """Renders high-conversion, production-grade Sovereign Web Store."""
    content = """
    <div class="hero-banner">
      <div class="hero-badge">Web Store Exclusive &bull; +20% Bonus Perks Credited</div>
      <h1 class="hero-title">Sovereign Vault & Sacred Store</h1>
      <p class="hero-subtitle">Acquire Intentional Passes, Direct Letters, and Sacred Micro-Perks. Purchases receive an exclusive +20% Web Bonus credited directly to your Seeker Vault.</p>
    </div>

    <!-- Seeker Binding Card -->
    <div class="glass-card" style="max-width: 680px; margin: 0 auto 36px; text-align: center;">
      <h3 style="color: var(--gold-light); font-size: 18px; margin-bottom: 8px;">Bind Purchase to Seeker Account</h3>
      <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">Enter your registered account email or Seeker UUID so entitlements are credited immediately upon payment.</p>
      <div style="display: flex; gap: 10px; max-width: 500px; margin: 0 auto;">
        <input type="text" id="seeker-ident" class="form-control" placeholder="seeker@urheart.app or Seeker UUID" value="">
        <button type="button" class="btn btn-outline" style="width: auto; white-space: nowrap;" onclick="saveSeekerIdent()">Save Identity</button>
      </div>
      <div id="ident-status" style="font-size: 12px; color: var(--success-emerald); margin-top: 8px; display: none;">&check; Seeker account active for checkout</div>
    </div>

    <!-- Strict No-Refund Statutory Disclosure -->
    <div class="alert alert-gold" style="max-width: 900px; margin: 0 auto 36px; display: flex; align-items: center; gap: 16px;">
      <div style="font-size: 26px;">&bull;</div>
      <div style="text-align: left; font-size: 13px;">
        <strong style="color: #FFF;">Strict No-Refund Policy [Consumer Protection Rules 2020]:</strong>
        All purchases of digital consumables, passes, and micro-perks are provisioned immediately to your seeker vault. Because digital consumables are consumed in real-time interactions, all sales are final, immediate, and non-refundable once credited.
        <a href="/refund" style="color: var(--gold-light); text-decoration: underline; margin-left: 6px;">Read Full Policy &rarr;</a>
      </div>
    </div>

    <!-- Product Grid -->
    <div class="grid-3">
      <!-- Item 1: Weekly Pass -->
      <div class="glass-card product-card">
        <div>
          <span class="product-tag">+20% Bonus</span>
          <h3 style="color: #FFF; font-size: 20px;">Weekly Sovereign Pass</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">7 days of mindful discovery. Includes 120 Intentional Swipes (20 extra swipes web bonus).</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>49
            <span class="alt-price">/ $0.99 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; 120 Intentional Swipes</li>
            <li>&check; 7-Day Ad-Free Exploration</li>
            <li>&check; Instant Vault Crediting</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('pass_weekly', 49)">Acquire Weekly Pass</button>
      </div>

      <!-- Item 2: Monthly Pass (Popular) -->
      <div class="glass-card product-card" style="border-color: var(--gold-primary); box-shadow: 0 0 24px rgba(212, 175, 55, 0.25);">
        <div>
          <span class="product-tag" style="background: var(--gold-primary); color: #08090C;">⭐ Most Popular</span>
          <h3 style="color: #FFF; font-size: 20px;">Monthly Sovereign Pass</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">30 days of elevated resonance. Includes 600 Swipes + 6 Direct Letters (+20% web bonus).</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>149
            <span class="alt-price">/ $2.99 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; 600 Intentional Swipes</li>
            <li>&check; 6 Sovereign Direct Letters</li>
            <li>&check; Voice Verification Spark</li>
            <li>&check; 30-Day Ad-Free Sanctuary</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('pass_monthly', 149)">Acquire Monthly Pass</button>
      </div>

      <!-- Item 3: Infinity Pass (VIP) -->
      <div class="glass-card product-card">
        <div>
          <span class="product-tag">👑 Sovereign Tier</span>
          <h3 style="color: #FFF; font-size: 20px;">Infinity Sovereign Pass</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">Non-expiring lifetime entitlement. Unlimited swipes and 18 Direct Letters (+20% web bonus).</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>1,499
            <span class="alt-price">/ $29.99 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; Unlimited Intentional Swipes</li>
            <li>&check; 18 Sovereign Direct Letters</li>
            <li>&check; Permanent Ad-Free Sanctuary</li>
            <li>&check; Priority Match Queue</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('pass_infinity', 1499)">Acquire Infinity Pass</button>
      </div>

      <!-- Item 4: Instant Contact Key -->
      <div class="glass-card product-card">
        <div>
          <span class="product-tag">+20% Bonus</span>
          <h3 style="color: #FFF; font-size: 18px;">Instant Contact Key</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">Unseals bilateral contact bridge immediately upon mutual match + 20 bonus discovery swipes.</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>29
            <span class="alt-price">/ $0.49 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; 1 Instant Contact Key</li>
            <li>&check; 20 Bonus Swipes</li>
            <li>&check; Zero Waiting Period</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('contact_key_instant', 29)">Acquire Key</button>
      </div>

      <!-- Item 5: Direct Letters Pack -->
      <div class="glass-card product-card">
        <div>
          <span class="product-tag">4 Letters (+20%)</span>
          <h3 style="color: #FFF; font-size: 18px;">Direct Letters Pack</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">4 Intentional Direct Letters bypassing the discovery deck with sacred priority notification.</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>49
            <span class="alt-price">/ $0.99 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; 4 Direct Intentional Letters</li>
            <li>&check; Direct Inbox Delivery</li>
            <li>&check; Never Expires in Vault</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('direct_letters_pack_3', 49)">Acquire Letters</button>
      </div>

      <!-- Item 6: Global Passport -->
      <div class="glass-card product-card">
        <div>
          <span class="product-tag">29 Hours (+20%)</span>
          <h3 style="color: #FFF; font-size: 18px;">24h Global Passport</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-top: 6px;">Explore sanctuaries worldwide. Includes 29 hours of uninterrupted global discovery.</p>
          <div class="product-price">
            <span class="currency">&#8377;</span>99
            <span class="alt-price">/ $1.99 USD</span>
          </div>
          <ul style="list-style: none; font-size: 13px; color: var(--text-muted); margin: 16px 0; line-height: 1.8;">
            <li>&check; 29 Hours Global Teleport</li>
            <li>&check; Explore Any Metropolitan Sanctum</li>
            <li>&check; Instant Activation</li>
          </ul>
        </div>
        <button class="btn btn-gold" onclick="initiateCheckout('passport_24h', 99)">Acquire Passport</button>
      </div>
    </div>

    <!-- Trust Badges -->
    <div class="trust-badges">
      <div class="trust-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
        <span>256-Bit TLS Encryption</span>
      </div>
      <div class="trust-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        <span>Instant Vault Crediting</span>
      </div>
      <div class="trust-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>
        <span>RBI & NPCI Compliant Gateways</span>
      </div>
      <div class="trust-item">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>
        <span>Strict Finality &bull; No Hidden Fees</span>
      </div>
    </div>

    <!-- Client-Side Checkout Script -->
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
      function getSeekerIdent() {
        return localStorage.getItem('urheart_seeker_ident') || document.getElementById('seeker-ident').value.trim();
      }

      function saveSeekerIdent() {
        const val = document.getElementById('seeker-ident').value.trim();
        if (!val) {
          alert('Please enter your seeker email or account UUID.');
          return;
        }
        localStorage.setItem('urheart_seeker_ident', val);
        const status = document.getElementById('ident-status');
        status.style.display = 'block';
        setTimeout(() => { status.style.display = 'none'; }, 3000);
      }

      window.addEventListener('DOMContentLoaded', () => {
        const saved = localStorage.getItem('urheart_seeker_ident');
        if (saved) {
          document.getElementById('seeker-ident').value = saved;
          document.getElementById('ident-status').style.display = 'block';
        }
      });

      async function initiateCheckout(productId, amountInr) {
        const ident = getSeekerIdent();
        if (!ident) {
          alert('Please provide your registered account email or Seeker UUID so your purchase can be credited.');
          document.getElementById('seeker-ident').focus();
          return;
        }

        const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(ident);
        const payload = {
          product_identifier: productId,
          email: isUuid ? 'seeker@urheart.app' : ident,
          seeker_uuid: isUuid ? ident : null,
          currency: 'INR'
        };

        try {
          const resp = await fetch('/api/v1/payments/web-create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const resJson = await resp.json();

          if (!resp.ok || !resJson.success) {
            alert('Unable to initialize payment: ' + (resJson.message || 'Please try again.'));
            return;
          }

          const order = resJson.data;
          if (window.Razorpay) {
            const options = {
              key: order.key_id,
              amount: order.amount_paise,
              currency: order.currency,
              name: 'UR-Heart Sanctuary',
              description: productId + ' (+20% Web Bonus)',
              order_id: order.order_id,
              prefill: {
                email: isUuid ? '' : ident,
              },
              theme: { color: '#D4AF37' },
              handler: function (response) {
                alert('Payment Confirmed! Your order reference: ' + response.razorpay_payment_id + '\\nEntitlements are provisioned to your vault.');
                window.location.reload();
              }
            };
            const rzp = new window.Razorpay(options);
            rzp.open();
          } else {
            alert('Order Created: ' + order.order_id + '\\nAmount: &#8377;' + order.amount + '\\nPlease complete in sanctuary client or verify via webhook.');
          }
        } catch (err) {
          alert('Network communication error: ' + err.message);
        }
      }
    </script>
    """
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Sovereign Web Store", content, active_tab="store"))


# ==========================================
# 2. EMERGENCY 24-HR NCII TAKEDOWN PORTAL (/emergency-takedown)
# ==========================================
@web_router.get("/emergency-takedown", response_class=HTMLResponse)
@web_router.get("/takedown", response_class=HTMLResponse)
async def serve_emergency_takedown(request: Request) -> HTMLResponse:
    """Renders public emergency 24-hour takedown portal under IT Rules 2021 Rule 3(2)(b)."""
    content = """
    <div class="hero-banner">
      <div class="hero-badge" style="background: rgba(239, 68, 68, 0.15); color: #FCA5A5; border-color: var(--danger-border);">
        🚨 IT Rules 2021 Rule 3(2)(b) &bull; 24-Hour Emergency Portal
      </div>
      <h1 class="hero-title">Emergency 24-Hour NCII Takedown Desk</h1>
      <p class="hero-subtitle">Statutory expedited grievance mechanism for victims of Non-Consensual Intimate Imagery (NCII), impersonation, voyeurism, or explicit content. Immediate response guaranteed within 24 hours.</p>
    </div>

    <div class="glass-card glass-card-danger" style="max-width: 760px; margin: 0 auto;">
      <div id="form-container">
        <div class="alert alert-danger" style="margin-bottom: 24px;">
          <strong>Statutory Notice:</strong> This emergency form is reserved for urgent reports under Rule 3(2)(b) of the Information Technology Rules, 2021. Knowingly filing a fraudulent complaint is punishable under Bharatiya Nyaya Sanhita (BNS) & Section 66D of the IT Act.
        </div>

        <form id="takedown-form" onsubmit="handleTakedownSubmit(event)">
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="comp-name">Complainant Full Name *</label>
              <input type="text" id="comp-name" class="form-control" required placeholder="Your full legal name">
            </div>
            <div class="form-group">
              <label class="form-label" for="comp-email">Complainant Official Email *</label>
              <input type="email" id="comp-email" class="form-control" required placeholder="you@domain.com">
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label" for="comp-phone">Contact Phone / Signal (Optional)</label>
              <input type="tel" id="comp-phone" class="form-control" placeholder="+91-XXXXXXXXXX">
            </div>
            <div class="form-group">
              <label class="form-label" for="reported-handle">Reported Profile / Handle / Seeker ID *</label>
              <input type="text" id="reported-handle" class="form-control" required placeholder="@username or Profile UUID">
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="violation-cat">Statutory Violation Category *</label>
            <select id="violation-cat" class="form-control" required>
              <option value="ncii" selected>Non-Consensual Intimate Imagery (NCII / Explicit Images) &mdash; 24h SLA</option>
              <option value="explicit_content">Explicit Content Without Consent &mdash; 24h SLA</option>
              <option value="impersonation">Identity Impersonation / Fake Profile &mdash; 24h SLA</option>
              <option value="underage">Child Sexual Abuse Material (CSAM) / Underage &mdash; ZERO TOLERANCE</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="evidence-text">Statement of Fact & Context * (min 10 characters)</label>
            <textarea id="evidence-text" class="form-control" minlength="10" maxlength="1000" required placeholder="Describe the violation, how the content was uploaded without consent, and where it appears..."></textarea>
          </div>

          <div class="form-group">
            <label class="form-label" for="evidence-url">Offending Media URL / Screenshot Asset (Optional)</label>
            <input type="url" id="evidence-url" class="form-control" placeholder="https://media.urheart.app/... or CDN link">
          </div>

          <div class="checkbox-group">
            <input type="checkbox" id="affirmation" required>
            <label for="affirmation" class="checkbox-label">
              I solemnly affirm under penalty of perjury under the laws of the Republic of India that the statements made herein are true and accurate, that I am the depicted individual or their legally authorized representative, and that the depicted material violates Rule 3(2)(b) of the Information Technology Rules, 2021.
            </label>
          </div>

          <button type="submit" id="submit-btn" class="btn btn-danger" style="margin-top: 10px;">
            Submit Emergency 24-Hour Statutory Takedown Dossier
          </button>
        </form>
      </div>

      <!-- Result Card -->
      <div id="result-container" style="display: none; text-align: center; padding: 20px 0;">
        <div style="font-size: 54px; margin-bottom: 12px;">🛡️</div>
        <h2 style="color: var(--success-emerald); font-size: 24px; margin-bottom: 8px;">Emergency Dossier Acknowledged</h2>
        <p style="color: var(--text-muted); font-size: 14px; max-width: 520px; margin: 0 auto 20px;">
          Your emergency complaint has been cryptographically registered and dispatched to the Resident Grievance Officer and Trust &amp; Safety Desk.
        </p>

        <div class="glass-card" style="background: rgba(10, 12, 16, 0.9); border-color: var(--success-border); max-width: 500px; margin: 0 auto 24px; text-align: left;">
          <div style="font-size: 12px; color: var(--gold-light); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Statutory Reference ID</div>
          <div id="res-ref" style="font-family: monospace; font-size: 18px; color: #FFF; font-weight: 700; margin-bottom: 14px;"></div>
          
          <div style="font-size: 12px; color: var(--gold-light); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Statutory Takedown Deadline</div>
          <div id="res-deadline" style="font-size: 14px; color: #FCA5A5; font-weight: 600; margin-bottom: 14px;"></div>

          <div style="font-size: 12px; color: var(--gold-light); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Action Clock Countdown</div>
          <div id="countdown-timer" style="font-family: monospace; font-size: 24px; color: var(--gold-light); font-weight: 800;">23:59:59</div>
        </div>

        <p style="font-size: 12px; color: var(--text-muted);">
          A statutory receipt has been dispatched to your email. For follow-up, quote your Reference ID to <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary);">asiverticals@gmail.com</a>.
        </p>
      </div>
    </div>

    <script>
      async function handleTakedownSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('submit-btn');
        btn.disabled = true;
        btn.innerText = 'Transmitting Statutory Dossier...';

        const payload = {
          complainant_name: document.getElementById('comp-name').value.trim(),
          complainant_email: document.getElementById('comp-email').value.trim(),
          complainant_phone: document.getElementById('comp-phone').value.trim() || null,
          reported_handle_or_name: document.getElementById('reported-handle').value.trim(),
          violation_category: document.getElementById('violation-cat').value,
          evidence_text: document.getElementById('evidence-text').value.trim(),
          evidence_media_url: document.getElementById('evidence-url').value.trim() || null,
          good_faith_affirmation: document.getElementById('affirmation').checked
        };

        try {
          const resp = await fetch('/api/v1/legal/emergency-takedown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const resJson = await resp.json();

          if (!resp.ok || !resJson.success) {
            alert('Submission failed: ' + (resJson.message || 'Please check your inputs and try again.'));
            btn.disabled = false;
            btn.innerText = 'Submit Emergency 24-Hour Statutory Takedown Dossier';
            return;
          }

          document.getElementById('form-container').style.display = 'none';
          document.getElementById('result-container').style.display = 'block';
          document.getElementById('res-ref').innerText = resJson.data.dossier_reference_id;
          document.getElementById('res-deadline').innerText = new Date(resJson.data.emergency_takedown_due_at).toLocaleString();

          // Start live 24-hour countdown
          const dueTime = new Date(resJson.data.emergency_takedown_due_at).getTime();
          setInterval(() => {
            const now = new Date().getTime();
            const diff = Math.max(0, dueTime - now);
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const secs = Math.floor((diff % (1000 * 60)) / 1000);
            document.getElementById('countdown-timer').innerText = 
              String(hours).padStart(2, '0') + ':' + 
              String(mins).padStart(2, '0') + ':' + 
              String(secs).padStart(2, '0');
          }, 1000);

        } catch (err) {
          alert('Network communication error: ' + err.message);
          btn.disabled = false;
          btn.innerText = 'Submit Emergency 24-Hour Statutory Takedown Dossier';
        }
      }
    </script>
    """
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Emergency 24-Hour NCII Takedown Desk", content, active_tab="takedown"))


# ==========================================
# 3. RESIDENT GRIEVANCE OFFICER PORTAL (/grievance)
# ==========================================
@web_router.get("/grievance", response_class=HTMLResponse)
@web_router.get("/grievance-officer", response_class=HTMLResponse)
async def serve_grievance_portal(request: Request) -> HTMLResponse:
    """Renders Resident Grievance Officer Portal under IT Rules 2021 Rule 3(2)(a) & DPDP Act 2023 § 13."""
    content = """
    <div class="hero-banner">
      <div class="hero-badge">Statutory Grievance Redressal &bull; IT Rules 2021 Rule 3(2)(a)</div>
      <h1 class="hero-title">Resident Grievance Redressal Mechanism</h1>
      <p class="hero-subtitle">Designated resident grievance mechanism for UR-Heart Sanctuary pursuant to the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 and Section 13 of the Digital Personal Data Protection Act, 2023.</p>
    </div>

    <!-- Officer Profile Card -->
    <div class="glass-card" style="max-width: 820px; margin: 0 auto 36px;">
      <div style="display: flex; flex-wrap: wrap; gap: 24px; align-items: center; border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding-bottom: 24px; margin-bottom: 24px;">
        <div style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #D4AF37 0%, #997D29 100%); display: flex; align-items: center; justify-content: center; font-size: 28px; color: #08090C; font-weight: 800; box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);">
          AS
        </div>
        <div>
          <h2 style="color: #FFF; font-size: 24px; margin-bottom: 4px;">Anubhav Singh</h2>
          <div style="color: var(--gold-light); font-size: 14px; font-weight: 600;">Resident Grievance Officer &amp; Legal Counsel</div>
          <div style="color: var(--text-muted); font-size: 13px;">ASI Verticals Private Limited &bull; Republic of India</div>
        </div>
      </div>

      <div class="grid-2" style="margin-bottom: 24px;">
        <div>
          <div style="font-size: 12px; color: var(--gold-light); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Official Physical Office</div>
          <div style="color: #FFF; font-size: 14px; line-height: 1.6;">
            Chambers of Resident Legal Counsel,<br>
            Ayodhya District Court,<br>
            Ayodhya, Uttar Pradesh 224001, India
          </div>
        </div>
        <div>
          <div style="font-size: 12px; color: var(--gold-light); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Statutory Grievance Email</div>
          <div style="color: #FFF; font-size: 14px; line-height: 1.6;">
            <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary); text-decoration: none; font-weight: 600;">asiverticals@gmail.com</a><br>
            <span style="font-size: 12px; color: var(--text-muted);">Working Hours: Mon&ndash;Fri 10:00 AM &ndash; 6:00 PM IST</span>
          </div>
        </div>
      </div>

      <!-- Statutory Timelines -->
      <div style="background: rgba(10, 12, 16, 0.7); border: 1px solid var(--border-gold); border-radius: 12px; padding: 18px 22px; margin-bottom: 24px;">
        <h4 style="color: var(--gold-light); font-size: 14px; margin-bottom: 10px;">Statutory Redressal Timelines (Rule 3(2))</h4>
        <div class="grid-2">
          <div>
            <span style="color: var(--success-emerald); font-weight: 700;">&check; 24-Hour Acknowledgment:</span>
            <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Receipt and docket number assigned within 24 hours of complaint transmission.</p>
          </div>
          <div>
            <span style="color: var(--success-emerald); font-weight: 700;">&check; 15-Day Final Resolution:</span>
            <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Comprehensive investigation, remediation, and reasoned determination within 15 calendar days.</p>
          </div>
        </div>
      </div>

      <!-- Appellate Mechanism -->
      <div class="alert alert-gold" style="margin-bottom: 0;">
        <strong style="color: #FFF;">Grievance Appellate Committee (GAC) Recourse:</strong><br>
        Under Rule 3A of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 (as amended 2022), if you are dissatisfied with an order or resolution of the Resident Grievance Officer, you may prefer an appeal to the central Grievance Appellate Committee (GAC) within 30 days via their official portal:
        <div style="margin-top: 10px;">
          <a href="https://gac.gov.in" target="_blank" rel="noopener" class="btn btn-outline" style="display: inline-block; width: auto; font-size: 12px; padding: 6px 14px;">Visit Official GAC Portal (gac.gov.in) &rarr;</a>
        </div>
      </div>
    </div>

    <!-- How to File a Grievance Instructions -->
    <div class="glass-card" style="max-width: 820px; margin: 0 auto;">
      <h3 style="color: var(--gold-light); font-size: 18px; margin-bottom: 12px;">How to Submit a Formal Grievance</h3>
      <p style="color: var(--text-muted); font-size: 13px; line-height: 1.6; margin-bottom: 16px;">
        To file a formal grievance under Rule 3(2) of the IT Rules or Section 13 of the DPDP Act 2023, transmit an email to <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary);">asiverticals@gmail.com</a> containing:
      </p>
      <ol style="font-size: 13px; color: var(--text-muted); line-height: 1.8; margin-left: 20px; margin-bottom: 20px;">
        <li><strong>Subject Header:</strong> <code>[STATUTORY-GRIEVANCE] - &lt;Your Seeker UUID or Registered Email&gt;</code></li>
        <li><strong>Complainant Particulars:</strong> Your legal name, registered email address, and jurisdiction.</li>
        <li><strong>Target Profile / Content:</strong> Specific URL, UUID, or handle of the profile or interaction in question.</li>
        <li><strong>Grounds of Grievance:</strong> Detailed narrative referencing specific statutory violation (privacy, harassment, defamation, intellectual property, etc.).</li>
        <li><strong>Supporting Evidence:</strong> Attached screenshots, timestamps, or incident references.</li>
      </ol>
      <a href="mailto:asiverticals@gmail.com?subject=[STATUTORY-GRIEVANCE]" class="btn btn-gold" style="display: inline-flex; width: auto;">
        Compose Grievance Email to asiverticals@gmail.com
      </a>
    </div>
    """
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Resident Grievance Officer", content, active_tab="grievance"))


# ==========================================
# 4. STRICT NO-REFUND POLICY PORTAL (/refund)
# ==========================================
@web_router.get("/refund", response_class=HTMLResponse)
@web_router.get("/refund-policy", response_class=HTMLResponse)
async def serve_refund_policy(request: Request) -> HTMLResponse:
    """Renders Strict No-Refund & Digital Consumable Finality Policy under Consumer Protection Rules 2020."""
    content = """
    <div class="hero-banner">
      <div class="hero-badge">Consumer Protection (E-Commerce) Rules 2020 &bull; Section 5</div>
      <h1 class="hero-title">Strict No-Refund &amp; Digital Finality Policy</h1>
      <p class="hero-subtitle">Comprehensive disclosure regarding the irrevocable nature of digital consumable purchases, instant sanctuary vault provisioning, and payment reconciliation terms.</p>
    </div>

    <div class="glass-card" style="max-width: 860px; margin: 0 auto; text-align: left;">
      <div class="alert alert-gold" style="margin-bottom: 24px;">
        <strong style="color: #FFF; font-size: 15px;">Core Policy Summary:</strong><br>
        All purchases of digital consumables (Sparks, Roses, Revelation Passes, Slumber Streaks, and Sovereign Memberships) made on the UR-Heart Web Store or in-app are <strong>strictly final, non-refundable, and non-cancellable</strong> once provisioned into your seeker vault.
      </div>

      <h3 style="color: var(--gold-light); font-size: 18px; margin: 24px 0 10px;">1. Scope &amp; Nature of Digital Consumable Products</h3>
      <p style="color: var(--text-muted); font-size: 14px; line-height: 1.7; margin-bottom: 16px;">
        UR-Heart Sanctuary is an intentional social sanctum. Products available for acquisition include digital micro-perks, direct letters, and time-bound sovereign access passes. These assets are intangible digital goods that are credited instantaneously to the seeker&rsquo;s account vault upon authorization by the banking gateway.
      </p>

      <h3 style="color: var(--gold-light); font-size: 18px; margin: 24px 0 10px;">2. Statutory Exemption from Return / Refund Rights</h3>
      <p style="color: var(--text-muted); font-size: 14px; line-height: 1.7; margin-bottom: 16px;">
        Pursuant to Rule 5(3)(b) of the Consumer Protection (E-Commerce) Rules, 2020 and global digital commerce standards, return and cancellation rights do not apply to services or digital content that have commenced execution or have been delivered into the consumer&rsquo;s custody with prior affirmative consent. Because sanctuary perks are consumed in real-time interactions, cooling-off periods and cash refunds are strictly not supported.
      </p>

      <h3 style="color: var(--gold-light); font-size: 18px; margin: 24px 0 10px;">3. Platform Billing Distinctions</h3>
      <ul style="color: var(--text-muted); font-size: 14px; line-height: 1.8; margin-left: 20px; margin-bottom: 16px;">
        <li><strong>Web Store Purchases (Razorpay / Stripe):</strong> Direct billing by ASI Verticals Private Limited. All transactions are final upon ledger confirmation.</li>
        <li><strong>Apple StoreKit Purchases:</strong> Governed strictly by Apple App Store Terms and Conditions. Apple retains exclusive discretion over StoreKit transactions.</li>
        <li><strong>Google Play Billing Purchases:</strong> Governed strictly by Google Play Developer Terms and billing policies.</li>
      </ul>

      <h3 style="color: var(--gold-light); font-size: 18px; margin: 24px 0 10px;">4. Banking Timeouts &amp; Uncredited Deductions</h3>
      <p style="color: var(--text-muted); font-size: 14px; line-height: 1.7; margin-bottom: 16px;">
        In rare circumstances where your bank or UPI app deducts funds but an intermediary network timeout prevents instantaneous crediting of your sanctuary vault:
      </p>
      <ol style="color: var(--text-muted); font-size: 14px; line-height: 1.8; margin-left: 20px; margin-bottom: 16px;">
        <li><strong>Automated Ledger Reconciliation:</strong> Our banking webhook listener continuously reconciles pending transactions. Credits typically settle automatically within 24 to 48 hours.</li>
        <li><strong>Manual Vault Assist:</strong> If your perks do not reflect within 24 hours, transmit your Bank UTR / Payment ID and registered account email to <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary);">asiverticals@gmail.com</a>. Upon verification of receipt in our merchant account, your perks will be manually credited immediately.</li>
      </ol>

      <h3 style="color: var(--gold-light); font-size: 18px; margin: 24px 0 10px;">5. Anti-Fraud &amp; Chargeback Abuse</h3>
      <p style="color: var(--text-muted); font-size: 14px; line-height: 1.7; margin-bottom: 24px;">
        Initiating an unjustified or fraudulent chargeback through a banking institution after consuming digital perks constitutes a material breach of our Master Terms of Service. In such events, the associated seeker account will be subject to permanent incineration and blacklisting from all ASI Verticals properties.
      </p>

      <div style="border-top: 1px solid rgba(212, 175, 55, 0.2); padding-top: 18px; font-size: 12px; color: var(--text-muted);">
        Effective Date: October 15, 2026 &bull; Published by ASI Verticals Private Limited &bull; Legal Desk: Ayodhya District Court, Ayodhya, Uttar Pradesh, India
      </div>
    </div>
    """
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Strict No-Refund Policy", content, active_tab="refund"))


# ==========================================
# 5. OUT-OF-APP DATA INCINERATION PORTAL (/delete-account)
# ==========================================
@web_router.get("/delete-account", response_class=HTMLResponse)
@web_router.get("/web-deletion", response_class=HTMLResponse)
async def serve_data_incineration(request: Request, token: Optional[str] = Query(None)) -> HTMLResponse:
    """Renders out-of-app account deletion portal under DPDP Act 2023 § 12 & Apple 5.1.1(v)."""
    has_token = bool(token and token.strip())
    req_display = "none" if has_token else "block"
    conf_display = "block" if has_token else "none"
    token_val = token.strip() if token else ""

    content = """
    <div class="hero-banner">
      <div class="hero-badge" style="background: rgba(239, 68, 68, 0.15); color: #FCA5A5; border-color: var(--danger-border);">
        DPDP Act 2023 &bull; Section 12 Right to Erasure
      </div>
      <h1 class="hero-title">Out-of-App Data Incineration Desk</h1>
      <p class="hero-subtitle">Pursuant to Section 12 of the DPDP Act 2023, Apple App Store Review Guideline 5.1.1(v), and Google Play policy, seekers may permanently incinerate their account and personal data directly from the web.</p>
    </div>

    <div class="glass-card glass-card-danger" style="max-width: 680px; margin: 0 auto; text-align: left;">
      <div class="alert alert-danger" style="margin-bottom: 24px;">
        <strong>Irrevocable Deletion Warning:</strong> Account incineration permanently deletes your seeker profile, moments, chat histories, bilateral photo reveals, and biometric KYC templates. Cloudflare R2 media assets are purged immediately and cannot be recovered.
      </div>

      <!-- Mode 1: Request Deletion Magic Link (when token is missing) -->
      <div id="request-flow" style="display: __REQ_DISPLAY__;">
        <h3 style="color: #FFF; font-size: 18px; margin-bottom: 10px;">Step 1: Request Incineration Verification Link</h3>
        <p style="color: var(--text-muted); font-size: 13px; line-height: 1.6; margin-bottom: 18px;">
          Enter your registered sanctuary account email. We will dispatch a secure 15-minute verification link to authorize permanent incineration.
        </p>

        <form id="req-form" onsubmit="handleRequestLink(event)">
          <div class="form-group">
            <label class="form-label" for="del-email">Registered Account Email *</label>
            <input type="email" id="del-email" class="form-control" required placeholder="seeker@urheart.app">
          </div>

          <div class="form-group">
            <label class="form-label" for="del-reason">Reason for Departure (Optional)</label>
            <select id="del-reason" class="form-control">
              <option value="found_connection">I found a genuine connection</option>
              <option value="privacy_preference">Privacy &amp; data sovereignty preference</option>
              <option value="taking_break">Taking a mindful break from dating</option>
              <option value="other">Other reason</option>
            </select>
          </div>

          <button type="submit" id="dispatch-btn" class="btn btn-danger" style="margin-top: 10px;">
            Dispatch Statutory Incineration Verification Link
          </button>
        </form>

        <div id="dispatch-success" style="display: none; text-align: center; padding: 20px 0;">
          <div style="font-size: 48px; margin-bottom: 10px;">✉️</div>
          <h4 style="color: var(--success-emerald); font-size: 18px; margin-bottom: 6px;">Statutory Verification Link Dispatched</h4>
          <p style="color: var(--text-muted); font-size: 13px;">Please check your inbox. Click the verification link within 15 minutes to confirm permanent account incineration.</p>
        </div>
      </div>

      <!-- Mode 2: Confirm Incineration with Token (when token query param is provided) -->
      <div id="confirm-flow" style="display: __CONF_DISPLAY__;">
        <h3 style="color: #FFF; font-size: 18px; margin-bottom: 10px;">Step 2: Confirm Irrevocable Account Incineration</h3>
        <p style="color: var(--text-muted); font-size: 13px; line-height: 1.6; margin-bottom: 18px;">
          You are authorizing permanent erasure of your identity under DPDP Act 2023 Section 12. To execute cryptographic Row &amp; CDN asset purge, type the exact confirmation phrase below:
        </p>

        <form id="conf-form" onsubmit="handleConfirmIncineration(event)">
          <input type="hidden" id="token-input" value="__TOKEN_VAL__">
          <div class="form-group">
            <label class="form-label" for="confirm-phrase">Type exact phrase: <strong style="color: #FFF;">PERMANENTLY INCINERATE</strong></label>
            <input type="text" id="confirm-phrase" class="form-control" required placeholder="PERMANENTLY INCINERATE">
          </div>


          <button type="submit" id="confirm-btn" class="btn btn-danger">
            Execute Cryptographic Account Incineration
          </button>
        </form>

        <div id="incinerate-success" style="display: none; text-align: center; padding: 20px 0;">
          <div style="font-size: 54px; margin-bottom: 10px;">🔥</div>
          <h3 style="color: var(--gold-light); font-size: 22px; margin-bottom: 8px;">Sacred Identity Incinerated</h3>
          <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">
            All relational rows, profile moments, bilateral revelations, and R2 media assets have been purged permanently from UR-Heart Sanctuary.
          </p>
          <div id="cert-box" class="glass-card" style="background: rgba(10, 12, 16, 0.9); font-family: monospace; font-size: 12px; color: var(--gold-light); text-align: left;"></div>
        </div>
      </div>
    </div>

    <script>
      async function handleRequestLink(e) {
        e.preventDefault();
        const btn = document.getElementById('dispatch-btn');
        btn.disabled = true;
        btn.innerText = 'Dispatching Statutory Link...';

        const email = document.getElementById('del-email').value.trim();
        const reason = document.getElementById('del-reason').value;

        try {
          const resp = await fetch('/api/v1/legal/web-account-deletion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, reason: reason })
          });
          const resJson = await resp.json();

          if (!resp.ok || !resJson.success) {
            alert('Request failed: ' + (resJson.message || 'Please check your email and try again.'));
            btn.disabled = false;
            btn.innerText = 'Dispatch Statutory Incineration Verification Link';
            return;
          }

          document.getElementById('req-form').style.display = 'none';
          document.getElementById('dispatch-success').style.display = 'block';
        } catch (err) {
          alert('Network communication error: ' + err.message);
          btn.disabled = false;
          btn.innerText = 'Dispatch Statutory Incineration Verification Link';
        }
      }

      async function handleConfirmIncineration(e) {
        e.preventDefault();
        const phrase = document.getElementById('confirm-phrase').value.trim();
        if (phrase !== 'PERMANENTLY INCINERATE') {
          alert('You must type PERMANENTLY INCINERATE exactly to proceed.');
          return;
        }

        const btn = document.getElementById('confirm-btn');
        btn.disabled = true;
        btn.innerText = 'Purging Data & Assets...';

        const token = document.getElementById('token-input').value.trim();

        try {
          const resp = await fetch('/api/v1/legal/web-account-deletion/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
          });
          const resJson = await resp.json();

          if (!resp.ok || !resJson.success) {
            alert('Incineration failed: ' + (resJson.message || 'Token may have expired or already been utilized.'));
            btn.disabled = false;
            btn.innerText = 'Execute Cryptographic Account Incineration';
            return;
          }

          document.getElementById('conf-form').style.display = 'none';
          document.getElementById('incinerate-success').style.display = 'block';
          document.getElementById('cert-box').innerText = 
            'CRYPTOGRAPHIC ERASURE CERTIFICATE\\n' +
            '----------------------------------------\\n' +
            'Certificate: ' + (resJson.data.certificate || 'N/A') + '\\n' +
            'Incinerated At: ' + (resJson.data.incinerated_at || new Date().toISOString()) + '\\n' +
            'Status: PERMANENTLY ERASED FROM SANCTUARY';
        } catch (err) {
          alert('Network communication error: ' + err.message);
          btn.disabled = false;
          btn.innerText = 'Execute Cryptographic Account Incineration';
        }
      }
    </script>
    </div>
    """
    content = (
        content
        .replace("__REQ_DISPLAY__", req_display)
        .replace("__CONF_DISPLAY__", conf_display)
        .replace("__TOKEN_VAL__", token_val)
    )
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Out-of-App Data Incineration Desk", content, active_tab="deletion"))



# ==========================================
# 6. CORPORATE OPERATIONS & CONTACT HUB (/contact)
# ==========================================
@web_router.get("/contact", response_class=HTMLResponse)
@web_router.get("/support", response_class=HTMLResponse)
async def serve_contact_hub(request: Request) -> HTMLResponse:
    """Renders Official Corporate Operations and Support Hub."""
    content = """
    <div class="hero-banner">
      <div class="hero-badge">Official Operations &bull; ASI Verticals Private Limited</div>
      <h1 class="hero-title">Sanctuary Operations &amp; Support Hub</h1>
      <p class="hero-subtitle">Official communication desk for seekers, statutory bodies, law enforcement, and technical assistance.</p>
    </div>

    <div class="glass-card" style="max-width: 820px; margin: 0 auto; text-align: left;">
      <div class="grid-2" style="margin-bottom: 28px;">
        <div>
          <h4 style="color: var(--gold-light); font-size: 16px; margin-bottom: 8px;">Corporate Identity &amp; Jurisdiction</h4>
          <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6;">
            <strong style="color: #FFF;">ASI Verticals Private Limited</strong><br>
            Incorporated under the Companies Act, 2013<br>
            Republic of India
          </p>
        </div>
        <div>
          <h4 style="color: var(--gold-light); font-size: 16px; margin-bottom: 8px;">Physical Legal Address</h4>
          <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6;">
            Chambers of Resident Legal Counsel,<br>
            Ayodhya District Court,<br>
            Ayodhya, Uttar Pradesh 224001, India
          </p>
        </div>
      </div>

      <div class="grid-2" style="border-top: 1px solid rgba(212, 175, 55, 0.2); padding-top: 24px; margin-bottom: 24px;">
        <div>
          <h4 style="color: var(--gold-light); font-size: 16px; margin-bottom: 8px;">Official Support &amp; Grievance Email</h4>
          <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6;">
            <a href="mailto:asiverticals@gmail.com" style="color: var(--gold-primary); font-weight: 700; text-decoration: none;">asiverticals@gmail.com</a><br>
            Hours: Monday &ndash; Friday, 10:00 AM &ndash; 6:00 PM IST
          </p>
        </div>
        <div>
          <h4 style="color: var(--gold-light); font-size: 16px; margin-bottom: 8px;">Emergency 24-Hour NCII Portal</h4>
          <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6;">
            For non-consensual imagery or urgent safety concerns:<br>
            <a href="/emergency-takedown" style="color: var(--danger-crimson); font-weight: 700; text-decoration: underline;">Launch Emergency Takedown Desk &rarr;</a>
          </p>
        </div>
      </div>

      <div style="border-top: 1px solid rgba(212, 175, 55, 0.2); padding-top: 24px; display: flex; flex-wrap: wrap; gap: 12px;">
        <a href="/store" class="btn btn-gold" style="width: auto;">Visit Web Store</a>
        <a href="/grievance" class="btn btn-outline" style="width: auto;">Resident Grievance Officer</a>
        <a href="/refund" class="btn btn-outline" style="width: auto;">Refund Policy</a>
        <a href="/delete-account" class="btn btn-outline" style="width: auto;">Out-of-App Data Deletion</a>
      </div>
    </div>
    """
    return HTMLResponse(render_html_page("UR-Heart Sanctuary | Operations & Contact Desk", content, active_tab="contact"))
