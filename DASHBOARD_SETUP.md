# 🚀 Quick Start: Tesla Dashboard Setup

This guide will get your Next.js dashboard running in 5 minutes.

## ✅ Prerequisites Check

Before starting, verify:

```bash
# 1. Check Docker containers are running
docker ps

# You should see these containers:
# - postgres
# - kafka
# - zookeeper
# - airflow-webserver
# - airflow-scheduler

# 2. Check PostgreSQL has data
docker exec -it postgres psql -U reddit_user -d reddit_pipeline -c "SELECT COUNT(*) FROM posts_raw;"

# Should return a count > 0 (you have 701 posts)

# 3. Check Node.js version
node --version
# Should be v18 or higher
```

## 🏗️ Setup Steps

### Step 1: Navigate to Dashboard

```bash
cd /Users/shivanshsingh/Desktop/reddit_etl_project/dashboard
```

### Step 2: Create Environment File

```bash
cat > .env.local << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=reddit_pipeline
DB_USER=reddit_user
DB_PASSWORD=reddit_pass
NEXT_PUBLIC_APP_NAME=Tesla Energy Sentiment Dashboard
NEXT_PUBLIC_REFRESH_INTERVAL=30000
EOF
```

### Step 3: Install Dependencies (if needed)

```bash
# Check if node_modules exists
ls node_modules

# If not, install dependencies
npm install
```

### Step 4: Start Development Server

```bash
npm run dev
```

You should see:

```
▲ Next.js 16.0.3
- Local:        http://localhost:3000
- Environments: .env.local

✓ Starting...
✓ Ready in 2.3s
```

### Step 5: Open Dashboard

Open your browser and navigate to:

**http://localhost:3000**

You should see:

- Total Posts: 701
- Entity Extraction Rate: 61.6%
- Critical Alerts count
- Sentiment timeline chart

## 🎯 Test Each Page

1. **Dashboard (/)**: Check stats load correctly
2. **Alerts (/alerts)**: Verify 5 CRITICAL, 3 HIGH, 5 MEDIUM alerts show
3. **Products (/products)**: Confirm Model Y (152 posts) appears
4. **Insights (/insights)**: See 15 topics and 7 clusters
5. **Subreddits (/subreddits)**: View 14 subreddit stats

## 🐛 Common Issues & Fixes

### Issue 1: "Failed to fetch data"

**Cause**: PostgreSQL not accessible

**Fix**:

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# If not running, start containers
cd /Users/shivanshsingh/Desktop/reddit_etl_project
docker-compose up -d postgres
```

### Issue 2: "Database connection failed"

**Cause**: Wrong credentials in .env.local

**Fix**:

```bash
# Verify credentials match docker-compose.yaml
cat docker-compose.yaml | grep POSTGRES_

# Update .env.local if needed
nano .env.local
```

### Issue 3: Port 3000 already in use

**Fix**:

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm run dev
```

### Issue 4: npm install fails

**Fix**:

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and package-lock
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

### Issue 5: Build errors

**Fix**:

```bash
# Delete .next folder
rm -rf .next

# Rebuild
npm run build
```

## 🔍 Verify Data Pipeline

If dashboard shows no data, check the pipeline:

```bash
# 1. Check Airflow UI
open http://localhost:8080
# Login: admin / admin

# 2. Verify DAGs have run
# Look for green checkmarks on:
# - reddit_ingestion_dag
# - sentiment_analysis_dag
# - topic_extraction_dag
# - anomaly_detection_dag

# 3. Query database directly
docker exec -it postgres psql -U reddit_user -d reddit_pipeline

# Run these queries:
SELECT COUNT(*) FROM posts_raw;           -- Should be 701
SELECT COUNT(*) FROM sentiment_timeseries; -- Should be 697
SELECT COUNT(*) FROM alerts;               -- Should be 13
SELECT COUNT(*) FROM topics;               -- Should be 15
SELECT COUNT(*) FROM issue_clusters;       -- Should be 7
```

## 🎨 Customize Dashboard

### Change Refresh Interval

Edit `.env.local`:

```bash
NEXT_PUBLIC_REFRESH_INTERVAL=60000  # 60 seconds instead of 30
```

### Disable Auto-Refresh

In each page component (`src/app/*/page.tsx`), comment out:

```typescript
// const interval = setInterval(fetchData, 30000);
// return () => clearInterval(interval);
```

### Change Theme Colors

Edit `src/app/globals.css`:

```css
:root {
  --primary: /* your color */
  --background: /* your color */
}
```

## 📊 Demo Preparation

Before your interview:

### 1. Start Everything

```bash
# Start backend
cd /Users/shivanshsingh/Desktop/reddit_etl_project
docker-compose up -d

# Wait 30 seconds for services to start

# Start dashboard
cd dashboard
npm run dev
```

### 2. Test All Features

- [ ] Homepage loads with stats
- [ ] Sentiment chart displays
- [ ] Alerts page shows 13 alerts
- [ ] Can mark alert as resolved
- [ ] Products page shows categories
- [ ] Insights shows topics and clusters
- [ ] Subreddits table displays

### 3. Prepare Talking Points

- **Architecture**: Next.js → API Routes → PostgreSQL
- **Real-Time**: Auto-refresh every 30s
- **Data Source**: 701 posts from 14 subreddits
- **Entity Extraction**: 61.6% success rate
- **Anomaly Detection**: 5 CRITICAL alerts detected
- **ML Insights**: TF-IDF + K-Means clustering

### 4. Demo Flow (3 minutes)

1. **Homepage** (30s): Show stats, explain auto-refresh
2. **Alerts** (45s): Demonstrate alert management, Reddit links
3. **Products** (45s): Show Model Y sentiment, product breakdown
4. **Insights** (30s): Explain TF-IDF keywords, K-Means clusters
5. **Architecture** (30s): Frontend → Backend → Database flow

## 🚀 Production Deployment (Optional)

### Vercel (Easiest)

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
cd /Users/shivanshsingh/Desktop/reddit_etl_project/dashboard
vercel

# Add environment variables in Vercel dashboard:
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
```

**Note**: For production, you'd need:

- Cloud-hosted PostgreSQL (not localhost)
- SSL/TLS for database connections
- Authentication for dashboard access

## 📞 Get Help

If you encounter issues:

1. Check browser console (F12) for errors
2. Check terminal output for build errors
3. Verify Docker containers are running
4. Test database connection manually
5. Review logs: `docker logs airflow-scheduler --tail 50`

## ✅ Success Checklist

Before your interview, confirm:

- [ ] Dashboard loads on http://localhost:3000
- [ ] All 5 pages work (Dashboard, Alerts, Products, Insights, Subreddits)
- [ ] Data displays correctly (701 posts, etc.)
- [ ] No console errors in browser
- [ ] Auto-refresh works (check timestamp updates)
- [ ] Can mark alerts as resolved
- [ ] Charts render properly
- [ ] Mobile responsive (test by resizing window)

## 🎉 You're Ready!

Your dashboard is now fully functional and ready to demo. Good luck with your interview! 🚀

---

**Interview Date**: Monday, November 25, 2024  
**Dashboard Port**: http://localhost:3000  
**Airflow UI**: http://localhost:8080 (admin/admin)
