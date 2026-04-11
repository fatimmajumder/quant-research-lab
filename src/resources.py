from __future__ import annotations


PUBLIC_RESOURCES = [
    {
        "title": "Kenneth French Data Library",
        "category": "Data",
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "summary": "Canonical public factor datasets for market, size, value, profitability, and investment.",
    },
    {
        "title": "FRED Economic Data",
        "category": "Macro",
        "url": "https://fred.stlouisfed.org/",
        "summary": "Macro time series for policy rates, term structure, and unemployment overlays.",
    },
    {
        "title": "AQR Data Library",
        "category": "Research",
        "url": "https://www.aqr.com/Insights/Datasets",
        "summary": "Public factor and style premia series used for cross-checking research assumptions.",
    },
    {
        "title": "FRED S&P 500 / VIX Series",
        "category": "Market",
        "url": "https://fred.stlouisfed.org/series/SP500",
        "summary": "Open market and volatility proxy series for testing market-history ingestion without API keys.",
    },
    {
        "title": "SEC Company Facts API",
        "category": "Fundamentals",
        "url": "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "summary": "Public filing API for future point-in-time fundamental enrichment.",
    },
]


def list_public_resources() -> list[dict[str, str]]:
    return [resource.copy() for resource in PUBLIC_RESOURCES]
