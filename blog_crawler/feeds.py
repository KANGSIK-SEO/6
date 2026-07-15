"""Feed catalog for Silicon Valley and Chinese tech company blogs.

Each entry describes a single RSS/Atom feed:
    company : display name of the company / product
    region  : "usa" (Silicon Valley / US) or "china"
    category : rough topic bucket (engineering, ai, cloud, ...)
    url     : the RSS or Atom feed URL

Feeds are grouped so the catalog is easy to extend. If a feed URL changes,
update it here only -- the crawler treats this file as the single source of
truth.
"""

FEEDS = [
    # ------------------------------------------------------------------ #
    # Silicon Valley / US
    # ------------------------------------------------------------------ #
    # Google
    {"company": "Google (The Keyword)", "region": "usa", "category": "general",
     "url": "https://blog.google/rss/"},
    {"company": "Google Research", "region": "usa", "category": "ai",
     "url": "https://research.google/blog/rss/"},
    {"company": "Google Developers", "region": "usa", "category": "engineering",
     "url": "https://developers.googleblog.com/feeds/posts/default"},

    # Microsoft
    {"company": "Microsoft", "region": "usa", "category": "general",
     "url": "https://blogs.microsoft.com/feed/"},
    {"company": "Microsoft AI", "region": "usa", "category": "ai",
     "url": "https://blogs.microsoft.com/ai/feed/"},
    {"company": "Microsoft Research", "region": "usa", "category": "ai",
     "url": "https://www.microsoft.com/en-us/research/feed/"},

    # Amazon / AWS
    {"company": "AWS News", "region": "usa", "category": "cloud",
     "url": "https://aws.amazon.com/blogs/aws/feed/"},
    {"company": "AWS Machine Learning", "region": "usa", "category": "ai",
     "url": "https://aws.amazon.com/blogs/machine-learning/feed/"},
    {"company": "Amazon Science", "region": "usa", "category": "ai",
     "url": "https://www.amazon.science/index.rss"},

    # Meta
    {"company": "Meta Engineering", "region": "usa", "category": "engineering",
     "url": "https://engineering.fb.com/feed/"},
    {"company": "Meta AI", "region": "usa", "category": "ai",
     "url": "https://ai.meta.com/blog/rss/"},

    # Apple
    {"company": "Apple Machine Learning", "region": "usa", "category": "ai",
     "url": "https://machinelearning.apple.com/rss.xml"},

    # Netflix
    {"company": "Netflix Tech", "region": "usa", "category": "engineering",
     "url": "https://netflixtechblog.com/feed"},

    # Uber
    {"company": "Uber Engineering", "region": "usa", "category": "engineering",
     "url": "https://www.uber.com/blog/engineering/rss/"},

    # Cloudflare
    {"company": "Cloudflare", "region": "usa", "category": "engineering",
     "url": "https://blog.cloudflare.com/rss/"},

    # GitHub
    {"company": "GitHub", "region": "usa", "category": "engineering",
     "url": "https://github.blog/feed/"},

    # Stripe
    {"company": "Stripe", "region": "usa", "category": "engineering",
     "url": "https://stripe.com/blog/feed.rss"},

    # OpenAI
    {"company": "OpenAI", "region": "usa", "category": "ai",
     "url": "https://openai.com/news/rss.xml"},

    # NVIDIA
    {"company": "NVIDIA", "region": "usa", "category": "ai",
     "url": "https://blogs.nvidia.com/feed/"},

    # ------------------------------------------------------------------ #
    # China
    # ------------------------------------------------------------------ #
    # Meituan (well maintained engineering RSS)
    {"company": "Meituan Tech", "region": "china", "category": "engineering",
     "url": "https://tech.meituan.com/feed/"},

    # Alibaba Cloud (English)
    {"company": "Alibaba Cloud", "region": "china", "category": "cloud",
     "url": "https://www.alibabacloud.com/blog/rss"},

    # Baidu Research
    {"company": "Baidu Research", "region": "china", "category": "ai",
     "url": "http://research.baidu.com/Blog/rss"},

    # DiDi / others frequently expose RSS via Medium-style feeds; add here.
    # ByteDance / Tencent / Huawei mostly publish on WeChat and do not offer
    # stable public RSS -- see README for how to add scraper-backed sources.
]


def filter_feeds(region=None, company=None, category=None):
    """Return feeds matching the given filters (case-insensitive substring)."""
    result = []
    for f in FEEDS:
        if region and f["region"] != region.lower():
            continue
        if category and category.lower() not in f["category"].lower():
            continue
        if company and company.lower() not in f["company"].lower():
            continue
        result.append(f)
    return result
