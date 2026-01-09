# Quick 2FA Testing Guide

## Setup (One-time)

1. **Install Authenticator App** (choose one):
   - Google Authenticator (iOS/Android)
   - Microsoft Authenticator
   - Authy
   - Any TOTP-compatible app

2. **Start Backend**:
   ```bash
   cd backend
   python app.py
   ```

3. **Import Insomnia Collection**:
   - Open Insomnia
   - Import `tests/TUNAX_Insomnia_Collection.json`
   - Set base_url: `http://localhost:5000`

## Test Flow in Insomnia

### Step 1: Login (No 2FA Initially)
**Request:** `Login (No 2FA)`
```json
{
  "email": "citizen.demo@tunax.tn",
  "password": "TunaxDemo123!"
}
```
**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "user": { ... }
}
```
💡 **Save the `access_token`** in environment variable

---

### Step 2: Enable 2FA
**Request:** `Enable 2FA`
- Method: POST
- URL: `/two-factor/enable`
- Headers: `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "2FA setup initiated",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "secret": "BJHGFZACCQXWBC5ZVRYCLEDKQND3O4BV",
  "otpauth_url": "otpauth://totp/TUNAX:citizen.demo@tunax.tn?secret=..."
}
```

💡 **Copy the `qr_code` data URL** and paste into browser to see QR code
   OR use the `secret` key manually

---

### Step 3: Scan QR Code
1. Open your authenticator app
2. Click "+" or "Add account"
3. **Option A:** Scan the QR code from browser
4. **Option B:** Enter secret key manually
   - Account: TUNAX
   - Key: `BJHGFZACCQXWBC5ZVRYCLEDKQND3O4BV`
   - Type: Time-based

Your app will now show a 6-digit code that changes every 30 seconds

---

### Step 4: Verify Setup
**Request:** `Verify 2FA Setup`
```json
{
  "code": "123456"  // ← Enter current 6-digit code from app
}
```

**Response:**
```json
{
  "message": "2FA enabled successfully",
  "backup_codes": [
    "51F25BBF",
    "929451FA",
    "71A0E2ED",
    "656A7FF9",
    "F5D9A117",
    "3CE83972",
    "1862F109",
    "753DD2C1",
    "6FE6BD0D",
    "FC2FAEC2"
  ]
}
```

⚠️ **SAVE BACKUP CODES!** They're shown only once and can be used if you lose access to your authenticator app.

---

### Step 5: Test Login with 2FA
**Request:** `Login (With 2FA)`
```json
{
  "email": "citizen.demo@tunax.tn",
  "password": "TunaxDemo123!"
}
```

**Response:**
```json
{
  "requires_2fa": true,
  "temp_token": "eyJ0eXAi...",
  "message": "Please provide 2FA code"
}
```

💡 **Save the `temp_token`** - you'll need it for verification

---

### Step 6: Verify 2FA Login
**Request:** `Verify 2FA Login`
- Headers: `Authorization: Bearer <temp_token>`
```json
{
  "code": "789012"  // ← Current code from authenticator app
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "user": { ... }
}
```

✅ **Success!** You now have the final `access_token` to use for API requests

---

### Step 7: Disable 2FA (Optional)
**Request:** `Disable 2FA`
```json
{
  "password": "TunaxDemo123!"
}
```

**Response:**
```json
{
  "message": "2FA disabled successfully"
}
```

---

## Testing via Dashboard UI

1. **Login to Dashboard**:
   - Open `frontend/dashboards/citizen/index.html`
   - Login with `citizen.demo@tunax.tn` / `TunaxDemo123!`

2. **Enable 2FA**:
   - Click **🔓 2FA: OFF** button (next to Logout)
   - Click "Enable 2FA"
   - QR code will appear
   - Scan with authenticator app
   - Enter 6-digit code
   - Save backup codes
   - Button changes to **🔒 2FA: ON**

3. **Test 2FA Login**:
   - Logout
   - Login again
   - After password, you'll be prompted for 2FA code
   - Enter current code from authenticator app
   - Access granted

4. **Disable 2FA**:
   - Click **🔒 2FA: ON** button
   - Confirm you want to disable
   - Enter password
   - Button changes to **🔓 2FA: OFF**

---

## Troubleshooting

### "Invalid 2FA code"
- ✅ Check time synchronization on your device
- ✅ Codes change every 30 seconds - use current code
- ✅ Enter code quickly before it expires
- ✅ Try using a backup code instead

### "2FA already enabled"
- ✅ Must disable first, then re-enable
- ✅ Or use a different user account

### QR Code not showing
- ✅ Copy `qr_code` value from response
- ✅ Paste in browser: `data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...`
- ✅ Or use manual entry with `secret` key

### Authenticator app not working
- ✅ Verify device time is accurate (TOTP requires time sync)
- ✅ Try different authenticator app
- ✅ Use backup codes to login, then disable and re-enable 2FA

---

## Testing with Different Roles

All users can enable 2FA:
- **Citizen:** `citizen.demo@tunax.tn`
- **Business:** `business.demo@tunax.tn`
- **Agent:** `agent.demo@tunax.tn`
- **Finance:** `finance.demo@tunax.tn`
- **Admin:** `demo_admin@tunax.tn`
- **Ministry:** `ministry@tunax.tn`

Password for all: `TunaxDemo123!`

---

## API Endpoint Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/two-factor/enable` | POST | JWT | Generate QR code & secret |
| `/two-factor/verify-setup` | POST | JWT | Confirm 6-digit code |
| `/two-factor/disable` | POST | JWT | Disable 2FA (requires password) |
| `/two-factor/verify-login` | POST | temp_token | Verify code during login |

---

## Example: Complete Flow with curl

```bash
# 1. Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"citizen.demo@tunax.tn","password":"TunaxDemo123!"}'

# Save access_token from response

# 2. Enable 2FA
curl -X POST http://localhost:5000/api/two-factor/enable \
  -H "Authorization: Bearer <access_token>"

# Copy secret from response and add to authenticator app

# 3. Verify setup
curl -X POST http://localhost:5000/api/two-factor/verify-setup \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"123456"}'

# 4. Login again (now with 2FA)
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"citizen.demo@tunax.tn","password":"TunaxDemo123!"}'

# Save temp_token from response

# 5. Verify 2FA
curl -X POST http://localhost:5000/api/two-factor/verify-login \
  -H "Authorization: Bearer <temp_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"789012"}'

# Get final access_token
```

---

**Happy Testing!** 🔒
