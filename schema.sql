CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    aliases TEXT,
    period TEXT,
    era TEXT,
    location TEXT,
    case_type TEXT,
    silhouette INTEGER DEFAULT 0,
    summary TEXT,
    case_details TEXT,
    psychological_profile TEXT,
    sources TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
