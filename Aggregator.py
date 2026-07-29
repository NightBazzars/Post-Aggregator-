import os
import time
from datetime import datetime, timezone
import praw

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT", 
    "python:personal_aggregator:v1.0 (by /u/YOUR_REDDIT_USERNAME)"
)

# Subreddits to monitor (formatted for the Reddit API)
SUBREDDITS = [
    "news",
    "worldpolitics",
    "onlyfansadvice",
    "investing",
    "singularity",
    "wallstreetbets"
]

# Categorization rules tuned for these specific subreddits
CATEGORIES = {
    "Markets & Trading": [
        "stock", "options", "calls", "puts", "yolo", "earnings", "portfolio", 
        "fed", "shares", "bull", "bear", "nvda", "spy", "gme", "qqq", "market"
    ],
    "AI & Emerging Tech": [
        "ai", "agi", "llm", "gpt", "model", "robot", "openai", "anthropic", 
        "superintelligence", "neural", "claude", "transformer", "compute"
    ],
    "News & Global Events": [
        "breaking", "election", "court", "policy", "government", "war", 
        "president", "law", "economy", "global", "senate", "congress"
    ],
    "Creator Growth & Marketing": [
        "subscribers", "promo", "tiktok", "instagram", "content", "fansly", 
        "ppv", "pricing", "customs", "reddit", "tier", "chargeback", "bio"
    ]
}

# Array to store interesting posts
# Format: {"id": str, "title": str, "category": str, "url": str, "added_at": float}
tracked_posts = []


# -------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------
def classify_post(title: str, body: str) -> str | None:
    """Checks if a post matches any defined category keywords."""
    content = f"{title} {body}".lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword in content for keyword in keywords):
            return category
    return None


def fetch_new_posts(reddit: praw.Reddit):
    """Queries target subreddits for new posts and saves matching entries."""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{timestamp}] Polling subreddits for new submissions...")

    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for submission in subreddit.new(limit=10):
                # Skip if already in tracked array
                if any(p["id"] == submission.id for p in tracked_posts):
                    continue

                category = classify_post(submission.title, submission.selftext)
                if category:
                    post_data = {
                        "id": submission.id,
                        "title": submission.title,
                        "category": category,
                        "url": submission.url,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "added_at": time.time(),
                    }
                    tracked_posts.append(post_data)
                    print(f"  + Added [{category}] r/{sub_name}: '{submission.title[:65]}...'")

        except Exception as e:
            print(f"  ! Error fetching r/{sub_name}: {e}")


def query_tracked_comments(reddit: praw.Reddit):
    """Queries top comments for all posts currently stored in the tracked array."""
    if not tracked_posts:
        return

    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"\n[{timestamp}] Fetching comment updates for {len(tracked_posts)} tracked posts...")

    for post in tracked_posts:
        try:
            submission = reddit.submission(id=post["id"])
            submission.comments.replace_more(limit=0)  # Flatten top comment tree
            top_comments = submission.comments[:3]

            print(f"\n--- [{post['category']}] {post['title']} ---")
            print(f"URL: {post['url']} | Comments: {submission.num_comments}")
            
            if top_comments:
                print("Latest Top Comments:")
                for comment in top_comments:
                    author = comment.author.name if comment.author else "[deleted]"
                    snippet = comment.body.replace("\n", " ")[:120]
                    print(f"  - u/{author}: {snippet}...")
            else:
                print("  (No comments yet)")

        except Exception as e:
            print(f"  ! Error fetching comments for post {post['id']}: {e}")


# -------------------------------------------------------------------
# MAIN EVENT LOOP
# -------------------------------------------------------------------
def main():
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
    )

    POST_FETCH_INTERVAL = 15 * 60  # 15 minutes
    COMMENT_CHECK_INTERVAL = 45 * 60  # Check comments every 45 minutes

    last_comment_check = 0

    print("Personal Reddit Post Aggregator running...\n")

    while True:
        # Step 1: Query new posts every 15 minutes
        fetch_new_posts(reddit)

        # Step 2: Query tracked post comments every 45 minutes
        now = time.time()
        if now - last_comment_check >= COMMENT_CHECK_INTERVAL:
            query_tracked_comments(reddit)
            last_comment_check = now

        print(f"\nSleeping for 15 minutes...\n")
        time.sleep(POST_FETCH_INTERVAL)


if __name__ == "__main__":
    main()
