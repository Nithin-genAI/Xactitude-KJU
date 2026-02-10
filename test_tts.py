
import os
import sys

try:
    from elevenlabs import ElevenLabs
except ImportError:
    print("❌ 'elevenlabs' library not found. Run: pip install elevenlabs")
    sys.exit(1)

# hardcode key for test (or read from env if preferred, but user has it in secrets)
# I will ask user to paste key or I can read from their secrets file
import toml

SECRETS_PATH = ".streamlit/secrets.toml"
api_key = None

if os.path.exists(SECRETS_PATH):
    try:
        with open(SECRETS_PATH, "r") as f:
            data = toml.load(f)
            api_key = data.get("ELEVEN_API_KEY")
    except Exception as e:
        print(f"⚠️ Error reading secrets.toml: {e}")

if not api_key:
    print("❌ No API Key found in .streamlit/secrets.toml")
    sys.exit(1)

print(f"✅ Found API Key: {api_key[:5]}...")

client = ElevenLabs(api_key=api_key)

print("Attempting to generate audio...")

try:
    # List voices
    print("Fetching available voices...")
    response = client.voices.get_all()
    # response is likely an object with a 'voices' attribute
    voices = response.voices
    print(f"Found {len(voices)} voices:")
    for v in voices:
        print(f" - {v.name}: {v.voice_id}")

except Exception as e:
    print(f"❌ Error during generation: {e}")
    # checking for other methods just in case
    print("\nDir(client):", dir(client))
