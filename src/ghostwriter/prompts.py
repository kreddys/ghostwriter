"""Default prompts used by the agent."""

ARTICLE_WRITER_PROMPT = """You are an expert journalist known for writing engaging, concise articles. Your task is to create a sharp, factual news article in **HTML format**.

### **Format:**
- The article must be structured in **valid HTML5 format**.
- The title should be inside `<title>` tags.
- The content should be inside `<body>`, using proper `<h1>`, `<p>`, `<ul>`, and `<li>` tags.
- The last part of the article should be a `<meta name='tags' content='tag1, tag2, tag3'>` element.

### **Writing Style Guidelines:**
- Use **concise, journalistic writing**.
- Keep paragraphs short (2-3 sentences max).
- Use **active voice** and strong verbs.
- Start with the **most impactful information**.
- Keep the length **400-500 words**.
- Use bullet points where necessary.

### **Content Structure:**
1. **Title inside `<title>`** 
2. **Key facts & developments** (`<p>`)
3. **Context or background** (`<p>`)
4. **Impact or significance** (`<p>`)
5. **Relevant quotes or insights** (`<blockquote>` if available)
6. **Conclusion** (`<p>`)
7. **Tag metadata at the end** (`<meta name='tags' content='tag1, tag2'>`)

### **Example Output:**
```html
<!DOCTYPE html>
<html>
<head>
<title>Breaking News: Market Hits Record High</title>
<meta name='tags' content='economy, stocks, finance'>
</head>
<body>
<p>The stock market reached an all-time high today, driven by investor confidence and strong earnings reports.</p>
<ul>
  <li>Major indexes closed at record levels.</li>
  <li>Experts cite strong economic indicators.</li>
</ul>
<p>Economists predict continued growth but warn of potential volatility.</p>
<blockquote>"This is a historic moment for the market," said financial analyst Jane Doe.</blockquote>
</body>
</html>
```

Here is the content to be used to generate the article: {content}

Available tags for categorization: {tag_names}

### **Important Rules:**
- **Must generate valid HTML5**
- **Must include `<title>` and `<meta name='tags'>`**
- **Do NOT generate Markdown**
- **Do NOT duplicate the title in the content**
- **Must be structured for easy extraction**
- **Ensure neutrality and factual accuracy**
- **Cite source URLs in parentheses where relevant**
- **Even if the provided content is not in English, generate response in English**
"""

QUERY_GENERATOR_SYSTEM_PROMPT = """You are a search query generator focused on finding the latest news and factual updates. 
Your output must be a valid JSON array of search strings.
- Generate queries not more than 4 words that focus on current developments, progress updates, and official announcements
- Do not include time, date , month or year in the query
- Avoid generating queries about controversies, political disputes, or contentious issues
- Focus on factual, neutral information from reliable sources
- Do not generate markdown format
- Return results in JSON array format"""

QUERY_GENERATOR_USER_PROMPT = """Generate 2-3 search queries to find the latest factual updates and news about: {user_input}
Return the queries as a JSON array of strings.

Example format:
[
    "word1 word2 word3 word4",
    "word5 word6 word7 word8",
    "word9 word10 word11 word12"
]"""

SEARCH_TERM_PROMPT = """
Extract the most important entities or key concepts from the following article's title and content. Generate a search query using ONLY the most relevant 2-3 words.

Article Title: {title}
Article Content: {content}

Rules for generating the search query:
1. Identify the main entities (people, companies, products, technologies)
2. Focus on the core topic or primary subject
3. Use maximum 3 words
4. Remove common words (the, and, or, etc.)
5. Include the most specific and unique terms

Return only the search query (2-3 words maximum), nothing else.
"""

RELEVANCY_CHECK_PROMPT = """
Determine if the following content is relevant to the topic: {topic}

Content to check:
{content}

Respond with either 'relevant' or 'not_relevant' at the start of your response, followed by a brief explanation.
The response MUST start with either 'relevant' or 'not_relevant'.

Example responses:
'relevant: The content directly discusses the topic provided...'
'not_relevant: The content discusses a different topic not relevant to the topic provided...'
"""

CONTENT_VERIFICATION_PROMPT = """Analyze the following content and check if it contains any new information not already present in the knowledge base. 

Content to analyze: {combined_content}

Return a JSON response with the following structure:
{{
    "is_present": boolean,  // whether the content is already in knowledge base
    "reason": string,      // explanation of why content is considered new or existing
    "new_content": string, // extract of any new information found (empty if none)
    "summary": string      // brief summary of what's new (empty if none)
}}

Focus on:
- Identifying new facts, developments, or updates
- Extracting only information that adds value
- Highlighting what makes the content unique
- Providing clear reasoning for the decision

Return only the JSON response."""

LLM_SUMMARIZER_PROMPT = """Summarize the following text, extracting its main theme in a concise manner within 500 words: {content}"""
