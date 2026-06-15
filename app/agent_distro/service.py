import os
import json
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from app.agent_distro.models import DistributionRelease, ReleaseStatus

client = genai.Client()

def run_autonomous_agent_pipeline(release_id: str, db: Session):
    release = db.query(DistributionRelease).filter(DistributionRelease.id == release_id).first()
    if not release:
        return
        
    
    release.status = ReleaseStatus.AI_AUDITING
    db.commit()

    try:
        system_instruction = (
            "You are the senior Operations & Legal Compliance Agent for VibeGarage Distribution. "
            "Your job is to audit incoming track metadata to ensure it passes Spotify/Apple Music guidelines, "
            "and dynamically draft a split-sheet licensing agreement based on the provided parameters."
        )
        user_content = f"""
        Review the following distribution request:
        - Release ID: {release.id}
        - Allow Commercial Sync Licensing: {release.allow_sync_licensing}
        
        Tasks:
        1. Perform a compliance verification scan on the title and track settings. Flag any streaming platform policy violations.
        2. Generate a professional, legally structured multi-party Master & Sync-ready licensing contract summary text that binds the primary artist and the collaborators together.
        """

        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2, 
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "is_compliant": {"type": "BOOLEAN"},
                        "compliance_notes": {"type": "STRING"},
                        "generated_legal_contract": {"type": "STRING"},
                        "suggested_upc": {"type": "STRING"}
                    },
                    "required": ["is_compliant", "compliance_notes", "generated_legal_contract"]
                }
            )
        )

        
        agent_result = json.loads(response.text)
        
        if agent_result["is_compliant"]:
            
            release.status = ReleaseStatus.PROCESSING_DISTRIBUTION
            release.license_contract_url = agent_result["generated_legal_contract"] 
            
            
            if "suggested_upc" in agent_result:
                release.upc = agent_result["suggested_upc"]
        else:
            
            release.status = ReleaseStatus.AI_FAILED
            
        db.commit()

    except Exception as e:
        db.rollback()
        release.status = ReleaseStatus.AI_FAILED
        db.commit()
        print(f"Agent Exec Pipeline Error: {str(e)}")