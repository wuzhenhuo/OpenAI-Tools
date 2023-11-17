import os
import io
import base64
import asyncio
import argparse
import streamlit as st
from pathlib import Path
from openai import OpenAI
from datetime import datetime
import streamlit.components.v1 as components

UTC_TIMESTAMP = int(datetime.utcnow().timestamp())

FILE_ROOT = Path(__file__).resolve().parent

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()

DEBUG = args.debug

tts_lookup = {
    "tts-1": "tts-1: low latency, lower quality, more static",
    "tts-1-hd": "tts-1-hd: slower, higher quality",
}
def tts_format_func(option):
    return tts_lookup[option]

@st.cache_data(show_spinner=False)
def get_js() -> str:
    # Read javascript web trackers code from script.js file
    with open(FILE_ROOT / "script.js", "r") as f:
        return f"""
            <audio id="voicePlayer" autoplay #voicePlayer></audio>
            <script type='text/javascript'>{f.read()}</script>
        """

@st.cache_data(show_spinner=False)
def get_css() -> str:
    # Read CSS code from style.css file
    with open(FILE_ROOT / "style.css", "r") as f:
        return f"<style>{f.read()}</style>"

### MAIN APP STARTS HERE ###

async def main():

    # Define overall layout
    st.set_page_config(
        page_title="OpenAI Tools",
        page_icon="https://openaiapi-site.azureedge.net/public-assets/d/e90ac348d3/favicon.png",
        initial_sidebar_state=st.session_state.get('sidebar_state', 'expanded'),
        layout="wide"
    )

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if len(openai_api_key) > 0:
        st.session_state["openai_api_key"] = openai_api_key

    # Load CSS code
    st.markdown(get_css(), unsafe_allow_html=True)

    # Define sidebar layout
    with st.sidebar:
        st.subheader("OpenAI Credentials")
        st.text_input(label="openai_api_key", key="openai_api_key", placeholder="Your OpenAI API Key", type="password", label_visibility="collapsed")
        # st.text_input(label="openai_org_id", key="openai_org_id", placeholder="Your OpenAI Organization ID", type="password", label_visibility="collapsed")
        st.caption("_**Author's Note:** While I can only claim that your credentials are not stored anywhere, for maximum security, you should generate a new app-specific API key on your OpenAI account page and use it here. This way, you can deactivate the key after you don't plan to use the app anymore, and it won't affect any of your other keys/apps. You can check out the GitHub source for this app using below button:_")
        st.markdown('<a href="https://github.com/tipani86/OpenAI-Tools"><img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/tipani86/OpenAI-Tools?style=social"></a>', unsafe_allow_html=True)
        st.markdown('<a href="https://www.producthunt.com/posts/openai-tools?utm_source=badge-featured&utm_medium=badge&utm_souce=badge-openai&#0045;tools" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=414885&theme=neutral" alt="OpenAI&#0032;Tools - Super&#0032;App&#0032;For&#0032;Fine&#0045;tuning&#0032;Datasets&#0044;&#0032;Jobs&#0044;&#0032;Metrics&#0032;&#0038;&#0032;Models | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>', unsafe_allow_html=True)
        st.markdown('<small>Page views: <img src="https://www.cutercounter.com/hits.php?id=hxncoqd&nd=4&style=2" border="0" alt="visitor counter"></small>', unsafe_allow_html=True)
        if DEBUG:
            if st.button("Reload page"):
                st.session_state["NEED_REFRESH"] is True
                st.rerun()

    # Gate the loading of the rest of the page if the user hasn't entered their credentials
    openai_api_key = st.session_state.get("openai_api_key", "")
    # openai_org_id = st.session_state.get("openai_org_id", "")

    if len(openai_api_key) == 0: # or len(openai_org_id) == 0:
        st.info("Please enter your OpenAI credentials in the sidebar to continue.")
        st.stop()

    # Set up OpenAI API client
    client = OpenAI(api_key=openai_api_key)

    ### Main content ###

    with st.expander("**Whisper (Speech-To-Text) Playground**", expanded=True):
        # The audio file object (not file name) to transcribe, in one of these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
        whisper_file = st.file_uploader("Upload an audio file _(Note: There's a 25MB limit by OpenAI)_", type=["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"])
        # Check that the file size doesn't exceed 25MB which is OpenAI's limit
        if whisper_file is not None:
            file_size = len(whisper_file.getvalue())
            if file_size > 25 * 1024 * 1024:
                st.error(f"File size exceeds 25MB limit. Please upload a smaller file.")
            else:
                whisper_submitted = st.button("Transcribe")
                if whisper_submitted:
                    with st.spinner("Transcribing..."):
                        # Call the OpenAI API
                        transcript = await client.audio.transcriptions.acreate(
                            model="whisper-1",  # Only this one available for now
                            file=whisper_file,
                            timeout=TIMEOUT,
                        )
                    st.caption("Transcription complete.")
                    st.text_area("Transcript", transcript["text"] if "text" in transcript else transcript, height=200)

    with st.expander("**Speech (TTS) Playground", expanded=True):
        with st.form(key="tts_form", clear_on_submit=False):
            options_cols = st.columns(2)
            with options_cols[0]:
                model = st.radio("Model", options=tts_lookup.keys(), format_func=tts_format_func)
            with options_cols[1]:
                voice = st.selectbox("Voice", options=[
                    "alloy", 
                    "echo", 
                    "fable", 
                    "onyx", 
                    "nova", 
                    "shimmer"
                ])
            input_text = st.text_area("Input text", height=300, max_chars=4096)
            tts_submitted = st.form_submit_button("Generate")
        if tts_submitted:
            with st.spinner("Generating..."):
                # Call the OpenAI API
                response = await client.audio.speech.acreate(
                    model=model,
                    voice=voice,
                    input=input_text,
                    timeout=TIMEOUT,
                )
            buffer = io.BytesIO()
            for chunk in response.iter_bytes(chunk_size=4096):
                buffer.write(chunk)
                # Convert bytes to base64 string
                b64 = base64.b64encode(buffer.getvalue()).decode()
                if len(b64) > 0:
                    components.html(f"""<script>
                        window.parent.document.voicePlayer.src = "data:audio/mp3;base64,{b64}";
                        window.parent.document.voicePlayer.pause();
                        window.parent.document.voicePlayer.currentTime = 0;
                        window.parent.document.voicePlayer.play();
                    </script>""", height=0, width=0)
            buffer.seek(0)

if __name__ == "__main__":
    asyncio.run(main())