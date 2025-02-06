from openai import OpenAI
from bs4 import BeautifulSoup
import os

# OpenAI-compatible API details
API_URL = "http://localhost:11434/v1/chat/completions"  # Example: Ollama, LM Studio
MODEL_NAME = "mistral"  # Adjust based on the available models (e.g., "mistral", "llama2", "gemma")

# Example HTML input
html_content = """
<p>The High Court of Andhra Pradesh has launched a new dynamic official website, marking a significant step towards digital transformation. The beta version of the website is now live, offering improved accessibility and user experience for citizens, legal professionals, and stakeholders. The initiative is part of the court's efforts to modernize its services and enhance transparency.</p>
<p>The Hon'ble Chief Justice, Sri Justice Dhiraj Singh Thakur, emphasized the importance of leveraging technology to streamline judicial processes. The new website is expected to provide real-time updates on case statuses, judgments, and court schedules, making it easier for users to access critical information.</p>
"""

# Step 1: Extract text from HTML
def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)  # Extract and clean text

extracted_text = extract_text_from_html(html_content)
print("Extracted Text:", extracted_text)

# # Step 2: Call OpenAI-compatible API for summarization
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))

response = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL"),
    messages=[
        {"role": "system", "content": "You are an expert summarizer. Summarize the given text into 450 words."},
        {"role": "user", "content": extracted_text},
    ],
    stream=False
)

print("Summarized Text:", response.choices[0].message.content)
