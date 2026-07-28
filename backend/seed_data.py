"""Run with: python seed_data.py
Populates a handful of demo HCPs, materials and samples so the
search_and_add_catalog_item tool and HCP autocomplete have something to find.
"""
import asyncio

from app import models
from app.database import Base, SessionLocal, engine


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        hcps = [
            models.HCP(name="Dr. Sharma", specialty="Oncology", hospital="City Hospital"),
            models.HCP(name="Dr. Smith", specialty="Cardiology", hospital="St. Mary's Medical Center"),
            models.HCP(name="Dr. Rao", specialty="Oncology", hospital="City Hospital"),
        ]
        materials = [
            models.Material(name="OncoBoost Phase III Brochure", category="Clinical Data"),
            models.Material(name="OncoBoost MOA Leave-behind", category="Mechanism of Action"),
            models.Material(name="CardioSafe Efficacy Summary", category="Clinical Data"),
        ]
        samples = [
            models.Sample(name="OncoBoost 50mg Sample Pack", lot_number="OB50-2026-A"),
            models.Sample(name="CardioSafe 10mg Starter Pack", lot_number="CS10-2026-B"),
        ]

        for row in hcps + materials + samples:
            await db.merge(row)

        await db.commit()
    print("Seed data inserted.")


if __name__ == "__main__":
    asyncio.run(seed())
