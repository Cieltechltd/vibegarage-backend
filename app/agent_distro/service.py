import os
import json
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from app.agent_distro.models import DistributionRelease, ReleaseStatus

# Initialize the official Google GenAI client
# Make sure GEMINI_API_KEY is saved inside your environment variables (.env)
client = genai.Client()

def run_autonomous_agent_pipeline(release_id: str, db: Session):
    """
    The Core Agent Logic: Fetches the distribution record, triggers Gemini 
    to audit metadata for DSP rules, and drafts a structural licensing contract.
    """
    # 1. Fetch the target release record from our database
    release = db.query(DistributionRelease).filter(DistributionRelease.id == release_id).first()
    if not release:
        return
        
    # Advance state machine to tracking audit mode
    release.status = ReleaseStatus.AI_AUDITING
    db.commit()

    try:
        # 2. Structure our prompt instructions for the Gemini Agent
        # We enforce a Structured Output (JSON) so our backend can read the results predictably
        system_instruction = (
            "You are the senior Operations & Legal Compliance Agent for VibeGarage Distribution. "
            "Your job is to audit incoming track metadata to ensure it passes Spotify/Apple Music guidelines, "
            "and dynamically draft a split-sheet licensing agreement based on the provided parameters."
        )

        # Assemble the payload information for the agent to review
        # (In a production setup, you can append your core track/profile titles here)
        user_content = f"""
        Review the following distribution request:
        - Release ID: {release.id}
        - Allow Commercial Sync Licensing: {release.allow_sync_licensing}
        
        Tasks:
        1. Perform a compliance verification scan on the title and track settings. Flag any streaming platform policy violations.
        2. Generate a professional, legally structured multi-party Master & Sync-ready licensing contract summary text that binds the primary artist and the collaborators together.
        """

        # 3. Call the Gemini Model enforcing a strict Pydantic-like JSON Schema return
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2, # Low temperature ensures high predictability and compliance precision
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

        # 4. Parse the AI Agent's structural evaluation matrix
        agent_result = json.loads(response.text)
        
        if agent_result["is_compliant"]:
            # If the track metadata passes, approve it and move the state forward
            release.status = ReleaseStatus.PROCESSING_DISTRIBUTION
            
            # Save the text contract directly to the db column 
            # (In Step 8, we can render this text out into a downloadable PDF asset)
            release.license_contract_url = agent_result["generated_legal_contract"] 
            
            # Store a dummy mock UPC code if suggested by the agent
            if "suggested_upc" in agent_result:
                release.upc = agent_result["suggested_upc"]
        else:
            # If the metadata contains banned terms or formatting issues, trigger a failure state
            release.status = ReleaseStatus.AI_FAILED
            
        db.commit()

    except Exception as e:
        db.rollback()
        release.status = ReleaseStatus.AI_FAILED
        db.commit()
        print(f"Agent Exec Pipeline Error: {str(e)}")