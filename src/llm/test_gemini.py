import json
import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)

# Load the transcript chunks
with open("outputs/transcript_chunks.json", "r", encoding="utf-8") as file:
    chunks = json.load(file)

# For now, test only Chunk 1
chunk = chunks[0]

transcript_text = "\n".join(
    f"{record['source_ref']} | {record['text']}"
    for record in chunk["records"]
)

prompt = f"""
You are analyzing a legal deposition transcript.

Your task is to identify the meaningful topic or topics discussed in this transcript chunk.

IMPORTANT:
1. Use only the supplied transcript.
2. Do not invent information.
3. Preserve the exact page:line references provided before each line.
4. A topic should represent a meaningful subject of discussion, not every individual question.
5. If the chunk contains more than one meaningful topic, return multiple topics.
6. Start and end references must be exact references from the supplied transcript.
7. Evidence references must also be exact references from the supplied transcript.

Return ONLY valid JSON in this format:

{{
  "topics": [
    {{
      "topic": "short meaningful topic label",
      "start_ref": "page:line",
      "end_ref": "page:line",
      "evidence_refs": ["page:line", "page:line"]
    }}
  ]
}}

Transcript chunk:

{transcript_text}
"""

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)

result = interaction.output_text

print("\n===== GEMINI BASELINE RESULT =====\n")
print(result)

# Remove Markdown code fences if Gemini returns them
clean_result = result.strip()

if clean_result.startswith("```json"):
    clean_result = clean_result[len("```json"):].strip()

if clean_result.endswith("```"):
    clean_result = clean_result[:-3].strip()

# Validate that the cleaned result is real JSON
parsed_result = json.loads(clean_result)

with open("outputs/baseline_chunk_01.json", "w", encoding="utf-8") as file:
    json.dump(parsed_result, file, indent=2, ensure_ascii=False)

print("\nSaved valid JSON to: outputs/baseline_chunk_01.json")