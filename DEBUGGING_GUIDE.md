# Debugging Guide - Frontend State Issues

## 🎯 **IMMEDIATE FIX**

The **Reset Demo button now forces a full page reload** to clear all React state.

### Try This Right Now:
1. **Close ALL browser tabs** showing `localhost:3000`
2. Open **ONE fresh tab**: `http://localhost:3000`
3. Click **"Reset Demo"** button (top right)
4. Page will reload automatically
5. Go to **Agent View** tab
6. Claim details should load correctly

---

## ✅ Backend is Working Perfectly

I've verified the backend:

```bash
# Latest conversation: conv_3601k9n1k3cffcfak4wcz9tkzfj2
# Claim ID: bf010f9a-c838-4089-82ff-73095cd5c549
# Status: ALL ENDPOINTS RETURNING 200 OK ✅
```

**Claim Data:**
- Name: **John Smith**
- Car: **Toyota Prius 2020**
- Location: **London, Regent Street near Piccadilly Circus**
- Coverage: **COVERED** (100% confidence)
- Action: **Tow to Downtown Auto Repair** (30-45 min)

---

## ❌ Frontend Issue

**Problem:** React state showing old claim IDs even after localStorage cleared
**Solution:** Force full page reload (implemented)

---

## What Changed

### `/frontend/app/page.tsx` - Updated Reset Demo

```typescript
const handleResetDemo = () => {
  console.log('🔄 Resetting demo...');
  
  // Clear ALL localStorage
  localStorage.clear();
  localStorage.setItem('demoReset', 'true');
  
  // Notify components
  window.dispatchEvent(new StorageEvent('storage', {
    key: 'clearConversation',
    newValue: Date.now().toString(),
  }));
  
  // FORCE PAGE RELOAD (new!)
  setTimeout(() => {
    window.location.reload();
  }, 500);
};
```

---

## Testing Steps

### 1. Complete Reset
```bash
1. Close ALL browser tabs with localhost:3000
2. Open ONE new tab: http://localhost:3000
3. Click "Reset Demo" - wait for reload
4. Go to Agent View
```

### 2. Check localStorage is Clean
```javascript
// In browser console (F12)
console.log(localStorage);
// Should show: { demoReset: "true" } or empty
```

### 3. Verify Current Claim
```bash
# Get latest conversation
curl http://localhost:8000/conversation/latest | jq '.conversation_id'

# Get claim for that conversation (replace CONV_ID)
curl http://localhost:8000/conversation/CONV_ID/claim | jq '.claim_id'

# Get claim data (replace CLAIM_ID)
curl http://localhost:8000/claim/coverage/CLAIM_ID | jq '.'
```

All should return 200 OK with data.

---

## Expected UI After Fix

### Agent View Should Show:
```
📞 Conversation: conv_3601... | 📋 Claim: bf010... | 📝 Logs: 14 | Transcriptions: 15

┌─────────────────────────┐  ┌──────────────────────────┐
│   CLAIM DETAILS         │  │  CALL TRANSCRIPTION      │
│                         │  │                          │
│ Personal Information    │  │  Agent: Hello...         │
│ • Name: John Smith      │  │  User: Hi...             │
│ • Safety: Safe          │  │  Agent: ...              │
│                         │  ├──────────────────────────┤
│ Vehicle Information     │  │  AGENT EXECUTION LOGS    │
│ • Make: Toyota          │  │                          │
│ • Model: Prius          │  │  ✅ Policy found         │
│ • Year: 2020            │  │  ✅ Agent completed      │
│                         │  └──────────────────────────┘
│ Location                │
│ • Regent Street         │
│ • London                │
│                         │
│ Coverage Decision       │
│ • Status: COVERED ✅    │
│ • Confidence: 100%      │
│                         │
│ Recommended Action      │
│ • Type: Tow             │
│ • Garage: Downtown...   │
│                         │
│ [Approve] [Reject]      │
└─────────────────────────┘
```

---

## Common Issues & Fixes

### Issue 1: Still Seeing 404 Errors

**Symptom:**
```
GET /claim/coverage/7de4048e-6cc5-4412-8e12-b7b321e32453 404
```

**Fix:**
```javascript
// In browser console
localStorage.clear();
localStorage.setItem('demoReset', 'true');
location.reload();
```

### Issue 2: "Loading claim details..." Forever

**Causes:**
1. Frontend using wrong claim ID
2. Browser cache
3. Multiple tabs open

**Fix:**
```bash
1. Close ALL tabs
2. Clear browser cache (Cmd+Shift+Delete)
3. Open ONE new tab
4. Click "Reset Demo"
```

### Issue 3: Two Different Claim IDs in Console

**Symptom:**
```
ClaimInterface: Fetching bf010f9a...
ClaimInterface: Fetching 7de4048e...
```

**Cause:** React Strict Mode (development) or state confusion

**Fix:** Page reload (now automatic with Reset Demo)

---

## Backend Endpoints Quick Reference

```bash
# Health check
GET http://localhost:8000/docs

# Latest conversation
GET /conversation/latest

# Conversation → Claim mapping
GET /conversation/{conversation_id}/claim

# Claim data (200 OK immediately after agent processing)
GET /claim/coverage/{claim_id}    # ✅ Works now
GET /claim/action/{claim_id}      # ✅ Works now
GET /claim/message/{claim_id}     # ❌ 404 until approved/rejected

# Claim actions
POST /claim/{claim_id}/approve
POST /claim/{claim_id}/reject

# Real-time logs
GET /claim/stream/{claim_id}  # SSE stream
```

---

## Verification Commands

Run these to verify backend is working:

```bash
# 1. Check latest conversation
curl -s http://localhost:8000/conversation/latest | jq '.conversation_id'
# Expected: "conv_3601k9n1k3cffcfak4wcz9tkzfj2"

# 2. Get claim for this conversation
curl -s http://localhost:8000/conversation/conv_3601k9n1k3cffcfak4wcz9tkzfj2/claim | jq '.claim_id'
# Expected: "bf010f9a-c838-4089-82ff-73095cd5c549"

# 3. Get claim coverage (should return 200 OK with data)
curl -s http://localhost:8000/claim/coverage/bf010f9a-c838-4089-82ff-73095cd5c549 | jq '.'
# Expected: Full claim data with John Smith, Toyota Prius, etc.

# 4. Get claim action (should return 200 OK)
curl -s http://localhost:8000/claim/action/bf010f9a-c838-4089-82ff-73095cd5c549 | jq '.'
# Expected: Tow action with garage details
```

All commands should return 200 OK with data (no 404s).

---

## Summary

### ✅ Fixed
- Backend enum issue (`REJECTED` → `DENIED`)
- On-demand claim creation now triggers agent processing
- Reset Demo now forces page reload

### ✅ Verified Working
- Backend endpoints returning 200 OK
- Claim data is complete and correct
- Agent processing successful

### ⚠️ To Test
- Close all tabs
- Click "Reset Demo"
- Verify claim details load correctly

**The issue is frontend state confusion - the page reload should fix it!** 🎉

