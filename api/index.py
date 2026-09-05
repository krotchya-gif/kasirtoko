"""
KasirToko — Vercel serverless entrypoint (P3-3).

Seluruh logika ada di app.py (single source of truth). File ini hanya
me-re-export objek `app` agar fix di app.py otomatis berlaku di production
(tidak ada lagi drift copy-paste).

P3-6: di Vercel WAJIB ada POSTGRES_URL/DATABASE_URL karena filesystem
ephemeral (SQLite akan hilang tiap cold start) → fail-fast dengan pesan jelas.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if os.environ.get('VERCEL') and not (
    os.environ.get('POSTGRES_URL')
    or os.environ.get('DATABASE_URL')
    or os.environ.get('POSTGRES_PRISMA_URL')
):
    raise RuntimeError(
        'KasirToko di Vercel membutuhkan POSTGRES_URL/DATABASE_URL. '
        'SQLite tidak persisten di serverless (data hilang tiap cold start).'
    )

from app import app  # noqa: E402  (single source of truth)

# Vercel Python runtime memakai variabel `app` ini sebagai handler.
